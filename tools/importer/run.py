"""Importer degli eventi pubblici dai siti dei Comuni (fonti in adapters/).

Uso:  python run.py --dry-run            # stampa senza scrivere
      python run.py                      # upsert su Firestore + pulizia scaduti
      python run.py --source modena      # una sola fonte
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from concurrent.futures import ThreadPoolExecutor

from adapters import SOURCES, Adapter, fallback_place
from geo import PROVINCES, enrich, in_viewbox
from geocode import Geocoder
from mapping import ROME, dedupe_key
from registry import USER_AGENT

HERE = Path(__file__).parent
EXPIRED_AFTER = timedelta(days=7)
WORKERS = 4  # fonti scaricate in parallelo
log = logging.getLogger("importer")


def collect(client: httpx.Client, geocoder: Geocoder, names: list[str], now: datetime,
            horizon_days: int, stats: dict[str, dict] | None = None) -> list[dict]:
    """stats (opzionale): per fonte {"events", "skipped", "error"}; "error" None = la fonte ha risposto."""
    events: dict[tuple, dict] = {}
    stats = {} if stats is None else stats

    def fetch(name: str) -> tuple[list[dict], str | None]:
        """Solo rete (un host per fonte, 1 richiesta/s ciascuno): può girare in parallelo."""
        try:
            return list(SOURCES[name].events(client, now, horizon_days)), None
        except httpx.HTTPError as e:
            return [], str(e) or type(e).__name__

    with ThreadPoolExecutor(WORKERS) as pool:
        fetched = list(pool.map(fetch, names))
    # Geocoding (Nominatim, 1 richiesta/s in tutto) in sequenza.
    for name, (found, error) in zip(names, fetched):
        source: Adapter = SOURCES[name]
        kept = skipped = 0
        stats[name] = {"events": 0, "skipped": 0, "error": error}
        if error:
            log.error("%s: fonte non raggiungibile (%s), la salto", name, error)
        for ev in found:
            locate(ev, source, geocoder)
            if ev["lat"] is None:
                skipped += 1
                log.warning("  senza coordinate, scartato: %s", ev["sourceUrl"])
                continue
            enrich(ev, place_of(geocoder, ev, source), fallback_place(source))
            events.setdefault(dedupe_key(ev), ev)
            kept += 1
        stats[name] |= {"events": kept, "skipped": skipped}
        log.info("%s: %d eventi, %d senza coordinate", name, kept, skipped)
    return list(events.values())


def locate(ev: dict, source: Adapter, geocoder: Geocoder) -> None:
    """Coordinate dell'evento, sempre dentro la provincia della fonte.

    Quelle della fonte fuori provincia si scartano (capita: Umbria, Varsi…); si prova con gli indirizzi
    (comune e provincia nella query, risultato nel riquadro); in ultima istanza il centro del comune,
    con approxLocation=True.
    """
    queries = ev.pop("_geocode")
    if ev["lat"] is not None and not in_viewbox(ev["lat"], ev["lng"], source.viewbox):
        log.warning("  coordinate fuori provincia (%s, %s), le ignoro: %s", ev["lat"], ev["lng"], ev["sourceUrl"])
        ev["lat"] = ev["lng"] = None
    prov = PROVINCES.get(source.province, (source.province, None))[0]
    for q in queries:
        if ev["lat"] is not None:
            return
        hit = geocoder.lookup(f"{q}, {prov}", source.viewbox)
        if hit:
            ev["lat"], ev["lng"] = hit
    if ev["lat"] is None:
        city = queries[0].rsplit(",", 1)[-1].strip() if queries else source.city
        hit = geocoder.lookup(f"{city}, {prov}", source.viewbox) or geocoder.lookup(f"{source.city}, {prov}", source.viewbox)
        if hit:
            ev["lat"], ev["lng"] = hit
            ev["approxLocation"] = True
            log.warning("  luogo non trovato, uso il centro di %s: %s", city, ev["sourceUrl"])


def place_of(geocoder: Geocoder, ev: dict, source: Adapter) -> dict | None:
    """Comune, frazione, provincia e regione dalle coordinate; se Nominatim non risponde, non dà un comune
    o cade in un'altra provincia vale il comune della fonte."""
    try:
        return geocoder.reverse(ev["lat"], ev["lng"], source.city, source.province)
    except httpx.HTTPError as e:
        log.warning("  reverse geocoding non riuscito (%s), uso il comune della fonte", e)
        return None


MISSING_RUNS_TO_REMOVE = 2


def stale_updates(docs: dict[str, dict], seen_ids: set[str], ok_hosts: set[str], now_ms: int,
                  horizon_ms: int) -> dict[str, dict]:
    """Aggiornamenti per gli eventi scraper non ancora finiti che la loro fonte non pubblica più.

    docs: id → campi (source, sourceUrl, startTime, missingRuns, removedAt). Solo le fonti che in questo
    giro hanno risposto (ok_hosts) contano, e solo gli eventi che iniziano entro l'orizzonte (gli altri
    non erano nella lista letta). Al 2° import consecutivo senza l'evento: removedAt (nascosto, non cancellato).
    """
    out: dict[str, dict] = {}
    for doc_id, d in docs.items():
        if doc_id in seen_ids or d.get("source") != "scraper" or d.get("removedAt"):
            continue
        if urlsplit(d.get("sourceUrl") or "").netloc not in ok_hosts or (d.get("startTime") or 0) > now_ms + horizon_ms:
            continue
        missing = (d.get("missingRuns") or 0) + 1
        out[doc_id] = {"missingRuns": missing} | ({"removedAt": now_ms} if missing >= MISSING_RUNS_TO_REMOVE else {})
    return out


def write(events: list[dict], now: datetime, ok_hosts: set[str] | None = None, horizon_days: int = 60) -> None:
    from google.cloud.firestore_v1.base_query import FieldFilter

    from db import client as firestore_client  # solo qui: il dry-run non richiede credenziali

    db = firestore_client()
    coll = db.collection("events")
    now_ms = int(now.timestamp() * 1000)
    # Legge solo i documenti che sta per scrivere, non l'intera collezione.
    seen_ids = {ev["id"] for ev in events}
    refs = [coll.document(i) for i in seen_ids]
    existing = {d.id: d.to_dict() or {} for d in db.get_all(refs, field_paths=["source", "createdAt"]) if d.exists}

    batch, n, written, kept_manual = db.batch(), 0, 0, 0
    for ev in events:
        doc_id = ev.pop("id")
        old = existing.get(doc_id)
        if old and old.get("source") == "manual":  # modificato a mano dall'admin
            kept_manual += 1
            continue
        ev["createdAt"] = (old or {}).get("createdAt") or now_ms
        ev["updatedAt"] = now_ms
        batch.set(coll.document(doc_id), ev)
        n += 1
        written += 1
        if n == 400:  # limite Firestore 500 operazioni per batch
            batch.commit()
            batch, n = db.batch(), 0
    if n:
        batch.commit()

    live = {d.id: d.to_dict() or {} for d in coll.where(filter=FieldFilter("endTime", ">=", now_ms)).select(
        ["source", "sourceUrl", "startTime", "missingRuns", "removedAt"]).stream()}
    stale = stale_updates(live, seen_ids, ok_hosts or set(), now_ms, horizon_days * 86_400_000)
    for i, (doc_id, fields) in enumerate(stale.items()):
        if i % 400 == 0:
            if i:
                b.commit()
            b = db.batch()
        b.update(coll.document(doc_id), fields)
    if stale:
        b.commit()
    removed = sum(1 for f in stale.values() if "removedAt" in f)

    cutoff = int((now - EXPIRED_AFTER).timestamp() * 1000)
    # Filtro su source in Python: evita un indice composito endTime+source.
    expired = [d.reference for d in coll.where(filter=FieldFilter("endTime", "<", cutoff)).select(["source"]).stream()
               if (d.to_dict() or {}).get("source") == "scraper"]
    for i in range(0, len(expired), 400):
        b = db.batch()
        for ref in expired[i:i + 400]:
            b.delete(ref)
        b.commit()
    log.info("Scritti %d eventi, %d lasciati al manuale, %d scaduti eliminati, %d spariti dalla fonte "
             "(%d nascosti con removedAt)", written, kept_manual, len(expired), len(stale), removed)


def summary(stats: dict[str, dict], sources: dict) -> str:
    """Tabella eventi per comune, errori e comuni a zero; va anche nel riepilogo del job GitHub."""
    lines = ["| comune | eventi | senza coordinate | errore |", "|---|---|---|---|"]
    for name, st in sorted(stats.items()):
        lines.append(f"| {sources[name].city} | {st['events']} | {st['skipped']} | {st['error'] or ''} |")
    zero = [sources[n].city for n, st in sorted(stats.items()) if st["events"] == 0]
    errors = [sources[n].city for n, st in sorted(stats.items()) if st["error"]]
    lines += ["", f"Totale: {sum(st['events'] for st in stats.values())} eventi da {len(stats)} comuni",
              f"Comuni a zero ({len(zero)}): {', '.join(zero) or '-'}",
              f"Comuni con errori ({len(errors)}): {', '.join(errors) or '-'}"]
    text = "\n".join(lines)
    print(text)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    return text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="stampa gli eventi senza scrivere")
    p.add_argument("--source", action="append", choices=sorted(SOURCES), help="fonte (ripetibile)")
    p.add_argument("--dump", type=Path, help="con --dry-run: scrive gli eventi in questo file JSON (per i controlli)")
    p.add_argument("--horizon-days", type=int, default=60, help="importa eventi che iniziano entro N giorni")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    now = datetime.now(timezone.utc)
    names = args.source or list(SOURCES)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        geocoder = Geocoder(client, HERE / "geocache.json")
        stats: dict[str, dict] = {}
        try:
            events = collect(client, geocoder, names, now, args.horizon_days, stats)
        finally:
            geocoder.save()
    summary(stats, SOURCES)
    log.info("Totale dopo deduplica: %d (richieste Nominatim: %d)", len(events), geocoder.requests)
    if not events:
        log.error("Nessun evento raccolto: controlla le fonti")
        return 1

    if args.dry_run:
        if args.dump:
            args.dump.write_text(json.dumps(events, ensure_ascii=False, indent=1), encoding="utf-8")
        for ev in sorted(events, key=lambda e: e["startTime"]):
            start = datetime.fromtimestamp(ev["startTime"] / 1000, ROME)
            print(f"{start:%d/%m %H:%M}  {ev['category']:<8} {ev['priceType']:<7} "
                  f"{ev['title'][:55]:<55}  {ev['city'][:18]:<18} {ev['province']:<2} {ev['geohash']}")
        return 0
    ok_hosts = {urlsplit(SOURCES[n].base).netloc for n, st in stats.items() if st["error"] is None}
    write(events, now, ok_hosts, args.horizon_days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
