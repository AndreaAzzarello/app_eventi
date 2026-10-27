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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from concurrent.futures import ThreadPoolExecutor

from adapters import SOURCES, Adapter, fallback_place
from geo import PROVINCES, enrich, in_viewbox, slugify
from geocode import Geocoder
from mapping import ROME, content_hash, dedupe_key, html_to_text, is_long_running, one_line
from registry import USER_AGENT

HERE = Path(__file__).parent
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
    # Geocoding (Nominatim, 1 richiesta/s in tutto) in sequenza, dagli eventi più vicini nel tempo: se il budget
    # di richieste del giro finisce, i più lontani restano senza geocoding e lo prendono nei giorni dopo.
    pending = []
    for name, (found, error) in zip(names, fetched):
        stats[name] = {"events": 0, "skipped": 0, "error": error}
        if error:
            log.error("%s: fonte non raggiungibile (%s), la salto", name, error)
        pending += [(name, ev) for ev in found]
    pending.sort(key=lambda p: (p[1]["startTime"], p[1]["sourceUrl"]))
    for name, ev in pending:
        source: Adapter = SOURCES[name]
        locate(ev, source, geocoder)
        if ev["lat"] is None:
            stats[name]["skipped"] += 1
            log.warning("  senza coordinate, scartato: %s", ev["sourceUrl"])
            continue
        enrich(ev, place_of(geocoder, ev, source), fallback_place(source))
        clean_texts(ev)
        if is_long_running(ev):
            ev["longRunning"] = True
        ev["importRegion"] = slugify(source.region)  # regione del registro, non quella di Nominatim
        ev["contentHash"] = content_hash(ev)
        if events.setdefault(dedupe_key(ev), ev) is ev:
            stats[name]["events"] += 1
    for name in names:
        log.info("%s: %d eventi, %d senza coordinate", name, stats[name]["events"], stats[name]["skipped"])
    return list(events.values())


def clean_texts(ev: dict) -> None:
    """Ultimo controllo su tutti gli adapter: niente tag né entità HTML nei testi (la descrizione tiene gli a capo)."""
    ev["shortDescription"] = html_to_text(ev["shortDescription"])
    for k in ("title", "venueName", "address"):
        ev[k] = one_line(ev[k])


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
        # il centro del comune vale anche a budget finito (essential): meglio un punto approssimato che perdere l'evento
        hit = (geocoder.lookup(f"{city}, {prov}", source.viewbox, essential=True)
               or geocoder.lookup(f"{source.city}, {prov}", source.viewbox, essential=True))
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
BATCH = 400  # limite Firestore 500 operazioni per batch
GET_ALL_CHUNK = 300  # documenti per chiamata get_all (primo import di una regione grande)
MAX_WRITES = 15_000  # quota Spark 20.000 scritture al giorno, con margine
MAX_GEOCODE = 3_000  # richieste nuove a Nominatim per giro
MAX_READS = 40_000  # quota Spark 50.000 letture al giorno, con margine
#: campi letti in una sola query di proiezione: bastano a decidere cosa scrivere
PROJECTION = ["source", "contentHash", "removedAt", "missingRuns", "sourceUrl", "startTime", "endTime", "createdAt"]


class QuotaExceeded(Exception):
    pass


def stale_updates(docs: dict[str, dict], seen_ids: set[str], ok_hosts: set[str], now_ms: int,
                  horizon_ms: int) -> dict[str, dict]:
    """Aggiornamenti per gli eventi scraper non ancora finiti che la loro fonte non pubblica più.

    docs: id → campi (source, sourceUrl, startTime, endTime, missingRuns, removedAt). Solo le fonti che in
    questo giro hanno risposto (ok_hosts) contano, e solo gli eventi che iniziano entro l'orizzonte (gli altri
    non erano nella lista letta). Al 2° import consecutivo senza l'evento: removedAt (nascosto, non cancellato).
    """
    out: dict[str, dict] = {}
    for doc_id, d in docs.items():
        if doc_id in seen_ids or d.get("source") != "scraper" or d.get("removedAt") or (d.get("endTime") or 0) < now_ms:
            continue
        if urlsplit(d.get("sourceUrl") or "").netloc not in ok_hosts or (d.get("startTime") or 0) > now_ms + horizon_ms:
            continue
        missing = (d.get("missingRuns") or 0) + 1
        out[doc_id] = {"missingRuns": missing} | ({"removedAt": now_ms} if missing >= MISSING_RUNS_TO_REMOVE else {})
    return out


def plan_writes(events: list[dict], existing: dict[str, dict], ok_hosts: set[str], now_ms: int,
                horizon_ms: int) -> dict:
    """Cosa scrivere: solo gli eventi nuovi o con hash diverso (o da ripristinare), più gli spariti dalla fonte.

    existing: id → campi del documento già nel database (PROJECTION). Gli eventi con `source == manual`
    (modificati dall'admin) non si toccano.
    """
    write, unchanged, kept_manual = [], 0, 0
    for ev in events:
        old = existing.get(ev["id"])
        if old is None:
            write.append(ev)
        elif old.get("source") == "manual":
            kept_manual += 1
        elif old.get("contentHash") == ev["contentHash"] and not old.get("removedAt") and not old.get("missingRuns"):
            unchanged += 1
        else:
            write.append(ev)
    stale = stale_updates(existing, {ev["id"] for ev in events}, ok_hosts, now_ms, horizon_ms)
    return {"write": write, "unchanged": unchanged, "kept_manual": kept_manual, "stale": stale}


def commit_in_batches(db, ops: list) -> None:
    """ops: funzioni (batch) → None, committate a gruppi di BATCH."""
    for i in range(0, len(ops), BATCH):
        b = db.batch()
        for op in ops[i:i + BATCH]:
            op(b)
        b.commit()


def write(events: list[dict], now: datetime, ok_hosts: set[str] | None = None, horizon_days: int = 60,
          regions: set[str] | None = None, db=None, max_writes: int = MAX_WRITES, max_reads: int = MAX_READS) -> dict:
    """Upsert incrementale. Una sola lettura di proiezione degli eventi scraper delle regioni in elaborazione
    (id + contentHash + …), poi si scrive solo ciò che è cambiato. Si ferma prima di scrivere se le quote
    stimate superano max_writes/max_reads. Restituisce le statistiche (letti, scritti, invariati, nascosti)."""
    from google.cloud.firestore_v1.base_query import FieldFilter

    if db is None:
        from db import client as firestore_client  # solo qui: il dry-run non richiede credenziali

        db = firestore_client()
    coll = db.collection("events")
    now_ms = int(now.timestamp() * 1000)
    regions = regions or {ev["importRegion"] for ev in events}
    query = coll.where(filter=FieldFilter("importRegion", "in", sorted(regions)))
    indexed = query.count().get()[0][0].value  # 1 lettura ogni 1000 voci
    reads = max(1, -(-indexed // 1000))
    if reads + indexed > max_reads:
        raise QuotaExceeded(f"letture stimate {reads + indexed} > {max_reads}: non scrivo")
    existing = {d.id: d.to_dict() or {} for d in query.select(PROJECTION).stream()}
    reads += len(existing)
    # Id non trovati (nuovi, o vecchi documenti senza importRegion): un get_all per createdAt e source manual.
    missing = [ev["id"] for ev in events if ev["id"] not in existing]
    if reads + len(missing) > max_reads:
        raise QuotaExceeded(f"letture stimate {reads + len(missing)} > {max_reads}: non scrivo")
    elsewhere = {d.id: d.to_dict() or {} for i in range(0, len(missing), GET_ALL_CHUNK)
                 for d in db.get_all([coll.document(x) for x in missing[i:i + GET_ALL_CHUNK]], field_paths=PROJECTION)
                 if d.exists}
    reads += len(missing)
    plan = plan_writes(events, existing | elsewhere, ok_hosts or set(), now_ms, horizon_days * 86_400_000)
    n_writes = len(plan["write"]) + len(plan["stale"])
    if n_writes > max_writes:
        raise QuotaExceeded(f"scritture stimate {n_writes} > {max_writes}: non scrivo")

    ops = []
    for ev in plan["write"]:
        doc = {k: v for k, v in ev.items() if k != "id"}
        doc["createdAt"] = (existing | elsewhere).get(ev["id"], {}).get("createdAt") or now_ms
        doc["updatedAt"] = now_ms
        ops.append(lambda b, ref=coll.document(ev["id"]), doc=doc: b.set(ref, doc))
    for doc_id, fields in plan["stale"].items():
        ops.append(lambda b, ref=coll.document(doc_id), fields=fields: b.update(ref, fields))
    commit_in_batches(db, ops)
    hidden = sum(1 for f in plan["stale"].values() if "removedAt" in f)
    stats = {"reads": reads, "written": len(plan["write"]), "unchanged": plan["unchanged"],
             "kept_manual": plan["kept_manual"], "stale": len(plan["stale"]), "hidden": hidden,
             "writes": n_writes, "deleted": 0}
    log.info("Letture %d · scritti %d · invariati %d · lasciati al manuale %d · spariti dalla fonte %d "
             "(%d nascosti con removedAt)", reads, stats["written"], stats["unchanged"], stats["kept_manual"],
             stats["stale"], hidden)
    return stats


def coverage_doc(region: str, sources: list, events: list[dict], centers: dict[tuple[str, str], tuple[float, float]],
                 now_ms: int) -> dict:
    """Documento coverage/{regione}: i comuni coperti (fonti attive) con centro e numero di eventi di oggi.

    Lo legge la webapp per la scelta regione → comune e per le pagine /regione/[slug]; un comune senza centro
    geocodificato non si può scegliere e resta fuori.
    """
    counts = Counter(ev["citySlug"] for ev in events if ev["importRegion"] == slugify(region))
    comuni = []
    for s in sorted(sources, key=lambda s: s.city):
        slug = slugify(s.city)
        if (region, slug) in centers:
            lat, lng = centers[(region, slug)]
            comuni.append({"name": s.city, "slug": slug, "province": s.province, "lat": round(lat, 4),
                           "lng": round(lng, 4), "events": counts.get(slug, 0)})
    return {"name": region, "updatedAt": now_ms, "comuni": comuni}


def find_centers(names: list[str], geocoder: Geocoder) -> dict[tuple[str, str], tuple[float, float]]:
    """Centro di ogni comune coperto, (regione, slug) → (lat, lng): dalla cache del geocoder, 1 richiesta la prima volta."""
    centers = {}
    for n in names:
        s = SOURCES[n]
        try:
            hit = geocoder.lookup(f"{s.city}, {PROVINCES.get(s.province, (s.province,))[0]}", s.viewbox, essential=True)
        except httpx.HTTPError as e:
            log.warning("  centro di %s non trovato (%s)", s.city, e)
            hit = None
        if hit:
            centers[(s.region, slugify(s.city))] = hit
    return centers


def write_coverage(db, events: list[dict], names: list[str], centers: dict, now_ms: int) -> int:
    """Una scrittura al giorno per regione (coverage/{slug})."""
    by_region: dict[str, list] = {}
    for n in names:
        by_region.setdefault(SOURCES[n].region, []).append(SOURCES[n])
    for region, sources in by_region.items():
        db.collection("coverage").document(slugify(region)).set(coverage_doc(region, sources, events, centers, now_ms))
    return len(by_region)


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
    print(text)  # il riepilogo unico del workflow lo scrive ci_report.py
    return text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="stampa gli eventi senza scrivere")
    p.add_argument("--source", action="append", choices=sorted(SOURCES), help="fonte (ripetibile)")
    p.add_argument("--dump", type=Path, help="con --dry-run: scrive gli eventi in questo file JSON (per i controlli)")
    p.add_argument("--regione", action="append", help="regione del registro (ripetibile), per esempio lombardia")
    p.add_argument("--max-writes", type=int, default=MAX_WRITES, help="si ferma prima di scrivere oltre N documenti")
    p.add_argument("--max-reads", type=int, default=MAX_READS, help="si ferma prima di leggere oltre N documenti")
    p.add_argument("--stats-out", type=Path, help="scrive qui le statistiche dell'import (JSON)")
    p.add_argument("--max-geocode", type=int, default=MAX_GEOCODE,
                   help="richieste nuove a Nominatim per giro (le altre, dagli eventi più lontani, nei giorni dopo)")
    p.add_argument("--horizon-days", type=int, default=60, help="importa eventi che iniziano entro N giorni")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    now = datetime.now(timezone.utc)
    names = args.source or [n for n, a in SOURCES.items() if not args.regione or slugify(a.region) in args.regione]
    if not names:
        log.error("Nessuna fonte attiva per questa selezione")
        return 1
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        geocoder = Geocoder(client, HERE / "geocache.json", args.max_geocode,
                            float(os.environ.get("NOMINATIM_INTERVAL", "1")))
        stats: dict[str, dict] = {}
        try:
            events = collect(client, geocoder, names, now, args.horizon_days, stats)
            centers = {} if args.dry_run or args.source else find_centers(names, geocoder)
        finally:
            geocoder.save()
    summary(stats, SOURCES)
    log.info("Totale dopo deduplica: %d (richieste Nominatim: %d)", len(events), geocoder.requests)
    if geocoder.deferred:
        log.warning("Geocoding: %d richieste rimandate oltre il budget di %d, servono circa %d giorni "
                    "(gli eventi più vicini nel tempo hanno la precedenza)", len(geocoder.deferred), args.max_geocode,
                    -(-len(geocoder.deferred) // max(1, args.max_geocode)))
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
    try:
        stats = write(events, now, ok_hosts, args.horizon_days, {slugify(SOURCES[n].region) for n in names},
                      max_writes=args.max_writes, max_reads=args.max_reads)
    except QuotaExceeded as e:
        log.error("%s", e)
        return 2
    if not args.source:  # con --source il conteggio per comune sarebbe parziale
        from db import client as firestore_client

        stats["writes"] += write_coverage(firestore_client(), events, names, centers, int(now.timestamp() * 1000))
    if args.stats_out:
        args.stats_out.write_text(json.dumps(stats | {
            "region": "+".join(sorted({slugify(SOURCES[n].region) for n in names})), "events": len(events),
            "sources": len(names), "geocode": geocoder.requests, "deferred": len(geocoder.deferred)}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
