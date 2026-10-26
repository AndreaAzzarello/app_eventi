"""Importer degli eventi pubblici dei comuni della provincia di Modena.

Uso:  python run.py --dry-run            # stampa senza scrivere
      python run.py                      # upsert su Firestore + pulizia scaduti
      python run.py --source modena      # una sola fonte
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from geocode import Geocoder
from mapping import ROME, dedupe_key, to_event

USER_AGENT = "EventiVicini-importer/1.0 (+https://github.com/AndreaAzzarello/app_eventi)"
HERE = Path(__file__).parent
EXPIRED_AFTER = timedelta(days=7)
PAGE_SIZE = 25

# Siti design-comuni-plone: API REST pubblica (++api++), robots.txt senza Disallow.
# Termini: riuso consentito citando la fonte (l'app mostra il link "Fonte").
SOURCES = {
    "modena": {"base": "https://www.comune.modena.it", "city": "Modena"},
    "formigine": {"base": "https://www.comune.formigine.mo.it", "city": "Formigine"},
    "sassuolo": {"base": "https://www.comune.sassuolo.mo.it", "city": "Sassuolo"},
    "mirandola": {"base": "https://www.comune.mirandola.mo.it", "city": "Mirandola"},
}

log = logging.getLogger("importer")


def fetch(client: httpx.Client, source: dict, now: datetime):
    """Eventi Plone non ancora finiti, pagina per pagina, 1 richiesta al secondo."""
    url = f"{source['base']}/++api++/@search"
    params = {
        "portal_type": "Event", "end.query": now.strftime("%Y-%m-%d"), "end.range": "min",
        "sort_on": "start", "b_size": PAGE_SIZE, "fullobjects": 1,
    }
    while url:
        res = client.get(url, params=params, headers={"Accept": "application/json"})
        res.raise_for_status()
        data = res.json()
        yield from data.get("items", [])
        url, params = (data.get("batching") or {}).get("next"), None
        if url:
            time.sleep(1)


def collect(client: httpx.Client, geocoder: Geocoder, names: list[str], now: datetime,
            horizon_days: int) -> list[dict]:
    events: dict[tuple, dict] = {}
    for name in names:
        source = SOURCES[name]
        kept = skipped = 0
        try:
            for item in fetch(client, source, now):
                ev = to_event(item, source, now, horizon_days)
                if ev is None:
                    continue
                for q in ev.pop("_geocode"):
                    if ev["lat"] is not None:
                        break
                    hit = geocoder.lookup(q)
                    if hit:
                        ev["lat"], ev["lng"] = hit
                if ev["lat"] is None:
                    skipped += 1
                    log.warning("  senza coordinate, scartato: %s", ev["sourceUrl"])
                    continue
                events.setdefault(dedupe_key(ev), ev)
                kept += 1
        except httpx.HTTPError as e:
            log.error("%s: fonte non raggiungibile (%s), la salto", name, e)
        log.info("%s: %d eventi, %d senza coordinate", name, kept, skipped)
    return list(events.values())


def write(events: list[dict], now: datetime) -> None:
    from db import client as firestore_client  # solo qui: il dry-run non richiede credenziali

    db = firestore_client()
    coll = db.collection("events")
    now_ms = int(now.timestamp() * 1000)
    existing = {d.id: d.to_dict() or {} for d in coll.select(["source", "createdAt"]).stream()}

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
                  f"{ev['title'][:60]:<60}  {ev['venueName'][:30]} ({ev['lat']:.4f},{ev['lng']:.4f})")
        return 0
    write(events, now)
    return 0


if __name__ == "__main__":
    sys.exit(main())
