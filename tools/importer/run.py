"""Importer degli eventi pubblici dai siti dei Comuni (fonti in adapters/).

Uso:  python run.py --dry-run            # stampa senza scrivere
      python run.py                      # upsert su Firestore + pulizia scaduti
      python run.py --source modena      # una sola fonte
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from adapters import SOURCES, Adapter, fallback_place
from geo import enrich
from geocode import Geocoder
from mapping import ROME, dedupe_key
from registry import USER_AGENT

HERE = Path(__file__).parent
EXPIRED_AFTER = timedelta(days=7)
log = logging.getLogger("importer")


def collect(client: httpx.Client, geocoder: Geocoder, names: list[str], now: datetime,
            horizon_days: int) -> list[dict]:
    events: dict[tuple, dict] = {}
    for name in names:
        source: Adapter = SOURCES[name]
        kept = skipped = 0
        try:
            for ev in source.events(client, now, horizon_days):
                for q in ev.pop("_geocode"):
                    if ev["lat"] is not None:
                        break
                    hit = geocoder.lookup(q, source.viewbox)
                    if hit:
                        ev["lat"], ev["lng"] = hit
                if ev["lat"] is None:
                    skipped += 1
                    log.warning("  senza coordinate, scartato: %s", ev["sourceUrl"])
                    continue
                enrich(ev, place_of(geocoder, ev), fallback_place(source))
                events.setdefault(dedupe_key(ev), ev)
                kept += 1
        except httpx.HTTPError as e:
            log.error("%s: fonte non raggiungibile (%s), la salto", name, e)
        log.info("%s: %d eventi, %d senza coordinate", name, kept, skipped)
    return list(events.values())


def place_of(geocoder: Geocoder, ev: dict) -> dict | None:
    """Comune, provincia e regione dalle coordinate; se Nominatim non risponde vale quello della fonte."""
    try:
        return geocoder.reverse(ev["lat"], ev["lng"])
    except httpx.HTTPError as e:
        log.warning("  reverse geocoding non riuscito (%s), uso il comune della fonte", e)
        return None


def write(events: list[dict], now: datetime) -> None:
    from db import client as firestore_client  # solo qui: il dry-run non richiede credenziali

    db = firestore_client()
    coll = db.collection("events")
    now_ms = int(now.timestamp() * 1000)
    # Legge solo i documenti che sta per scrivere, non l'intera collezione.
    refs = [coll.document(ev["id"]) for ev in events]
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

    cutoff = int((now - EXPIRED_AFTER).timestamp() * 1000)
    # Filtro su source in Python: evita un indice composito endTime+source.
    expired = [d.reference for d in coll.where("endTime", "<", cutoff).select(["source"]).stream()
               if (d.to_dict() or {}).get("source") == "scraper"]
    for i in range(0, len(expired), 400):
        b = db.batch()
        for ref in expired[i:i + 400]:
            b.delete(ref)
        b.commit()
    log.info("Scritti %d eventi, %d lasciati al manuale, %d scaduti eliminati",
             written, kept_manual, len(expired))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="stampa gli eventi senza scrivere")
    p.add_argument("--source", action="append", choices=sorted(SOURCES), help="fonte (ripetibile)")
    p.add_argument("--horizon-days", type=int, default=60, help="importa eventi che iniziano entro N giorni")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    now = datetime.now(timezone.utc)
    names = args.source or list(SOURCES)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        geocoder = Geocoder(client, HERE / "geocache.json")
        try:
            events = collect(client, geocoder, names, now, args.horizon_days)
        finally:
            geocoder.save()
    log.info("Totale dopo deduplica: %d (richieste Nominatim: %d)", len(events), geocoder.requests)
    if not events:
        log.error("Nessun evento raccolto: controlla le fonti")
        return 1

    if args.dry_run:
        for ev in sorted(events, key=lambda e: e["startTime"]):
            start = datetime.fromtimestamp(ev["startTime"] / 1000, ROME)
            print(f"{start:%d/%m %H:%M}  {ev['category']:<8} {ev['priceType']:<7} "
                  f"{ev['title'][:55]:<55}  {ev['city'][:18]:<18} {ev['province']:<2} {ev['geohash']}")
        return 0
    write(events, now)
    return 0


if __name__ == "__main__":
    sys.exit(main())
