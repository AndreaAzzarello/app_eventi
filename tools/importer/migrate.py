"""Migrazione una tantum: aggiunge geohash, city, citySlug, province e region agli eventi che non li hanno.

Uso:  python migrate.py --texts --dry-run   # tag/entità HTML nei testi degli eventi già in Firestore
      python migrate.py --texts             # li ripulisce (anche gli eventi manual)
      python migrate.py --dry-run     # mostra cosa cambierebbe, non scrive
      python migrate.py               # scrive
Credenziali: come run.py (FIREBASE_SERVICE_ACCOUNT o GOOGLE_APPLICATION_CREDENTIALS).
Letture: una per evento (l'intera collezione, una volta sola). Nominatim: 1 richiesta/s, con cache.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

from geo import enrich
from geocode import Geocoder
from mapping import html_to_text, one_line
from run import USER_AGENT

HERE = Path(__file__).parent
FIELDS = ["geohash", "city", "citySlug", "province", "region"]
log = logging.getLogger("migrate")


def plan(docs: list[tuple[str, dict]], geocoder: Geocoder) -> tuple[list[tuple[str, dict]], list[str]]:
    """(id, campi da aggiornare) per gli eventi incompleti; elenco degli id senza coordinate valide."""
    updates, broken = [], []
    for doc_id, d in docs:
        if all(d.get(k) for k in FIELDS if k != "province"):
            continue
        lat, lng = d.get("lat"), d.get("lng")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)) or (lat == 0 and lng == 0):
            broken.append(doc_id)
            continue
        try:
            place = geocoder.reverse(lat, lng)
        except httpx.HTTPError as e:
            log.warning("%s: reverse geocoding non riuscito (%s)", doc_id, e)
            place = None
        if place is None and not d.get("city"):
            broken.append(doc_id)
            continue
        fallback = {"city": d.get("city", ""), "province": d.get("province", ""), "region": d.get("region", "")}
        ev = enrich({"lat": lat, "lng": lng}, place, fallback)
        updates.append((doc_id, {k: ev[k] for k in FIELDS}))
    return updates, broken


TEXT_FIELDS = ["title", "venueName", "address", "shortDescription"]


def text_updates(docs: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    """(id, campi) per gli eventi con tag o entità HTML nei testi: gli stessi che l'importer ora ripulisce."""
    out = []
    for doc_id, d in docs:
        new = {k: (html_to_text if k == "shortDescription" else one_line)(d.get(k)) for k in TEXT_FIELDS if d.get(k)}
        changed = {k: v for k, v in new.items() if v != d[k]}
        if changed:
            out.append((doc_id, changed))
    return out


def fix_texts(dry_run: bool) -> int:
    """Una tantum: ripulisce i testi di TUTTI gli eventi già in Firestore (anche manual); una lettura per evento."""
    from db import client as firestore_client

    db = firestore_client()
    coll = db.collection("events")
    docs = [(d.id, d.to_dict() or {}) for d in coll.select(TEXT_FIELDS).stream()]
    updates = text_updates(docs)
    log.info("Eventi: %d, con HTML nei testi: %d", len(docs), len(updates))
    for doc_id, fields in updates[:20]:
        print(f"{doc_id:<22} " + " | ".join(f"{k}: {v[:60]!r}" for k, v in fields.items()))
    if dry_run:
        return 0
    for i in range(0, len(updates), 400):
        batch = db.batch()
        for doc_id, fields in updates[i:i + 400]:
            batch.update(coll.document(doc_id), fields)
        batch.commit()
    log.info("Ripuliti %d eventi", len(updates))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="mostra le modifiche senza scrivere")
    p.add_argument("--texts", action="store_true", help="solo: toglie tag ed entità HTML dai testi degli eventi")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.texts:
        return fix_texts(args.dry_run)
    from db import client as firestore_client

    db = firestore_client()
    coll = db.collection("events")
    docs = [(d.id, d.to_dict() or {}) for d in coll.select(["lat", "lng", *FIELDS]).stream()]
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
        geocoder = Geocoder(client, HERE / "geocache.json")
        try:
            updates, broken = plan(docs, geocoder)
        finally:
            geocoder.save()

    log.info("Eventi: %d, da aggiornare: %d, senza coordinate valide: %d (richieste Nominatim: %d)",
             len(docs), len(updates), len(broken), geocoder.requests)
    for doc_id in broken:
        log.warning("  da sistemare a mano in /admin: %s", doc_id)
    if args.dry_run:
        for doc_id, fields in updates:
            print(f"{doc_id:<22} {fields['city'][:24]:<24} {fields['province']:<2} {fields['region'][:20]:<20} {fields['geohash']}")
        return 0
    for i in range(0, len(updates), 400):
        batch = db.batch()
        for doc_id, fields in updates[i:i + 400]:
            batch.update(coll.document(doc_id), fields)
        batch.commit()
    log.info("Aggiornati %d eventi", len(updates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
