"""Carica (o rimuove con --delete) 10 eventi demo su Firestore dal PC.

Id fissi demo-01…demo-10: rilanciarlo aggiorna gli stessi documenti, non li duplica.
Credenziali: come run.py (FIREBASE_SERVICE_ACCOUNT o GOOGLE_APPLICATION_CREDENTIALS).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from db import client

# (titolo, descrizione, categoria, prezzo, inizio da ora, durata, luogo, indirizzo, lat, lng, tag)
SAMPLES = [
    ("Concerto in piazza", "Live gratuito", "music", "free", timedelta(hours=6), timedelta(hours=2),
     "Piazza Roma", "Piazza Roma, Modena", 44.646, 10.925, ["outdoor", "live", "kids"]),
    ("Sagra del quartiere", "Street food e musica", "food", "low", timedelta(days=1, hours=2), timedelta(hours=4),
     "Parco Ducale", "Parco Ducale, Modena", 44.650, 10.930, ["outdoor", "family"]),
    ("Mostra d'arte contemporanea", "Ingresso gratuito fino alle 18", "culture", "free", timedelta(days=2),
     timedelta(hours=3), "Galleria Civica", "Via Emilia, Modena", 44.645, 10.922, ["indoor"]),
    ("Mercatino dell'antiquariato", "Bancarelle e artigianato", "market", "free", timedelta(days=3, hours=1),
     timedelta(hours=4), "Piazza Grande", "Piazza Grande, Modena", 44.6455, 10.9255, ["outdoor", "kids"]),
    ("Allenamento aperto corsa", "5km nel parco", "sport", "free", timedelta(days=1, hours=20), timedelta(hours=2),
     "Parco Ferrari", "Parco Ferrari, Modena", 44.640, 10.926, ["outdoor"]),
    ("Laboratorio bambini", "Giochi creativi 6-10 anni", "kids", "free", timedelta(days=4, hours=10),
     timedelta(hours=2), "Biblioteca comunale", "Via dei Mille, Modena", 44.643, 10.920, ["kids", "indoor"]),
    ("Degustazione prodotti tipici", "Aceto balsamico & more", "food", "premium", timedelta(days=5, hours=18),
     timedelta(hours=2), "Cortile Estense", "Largo Porta Sant'Agostino, Modena", 44.6468, 10.9212, ["outdoor"]),
    ("Cinema all'aperto", "Classico restaurato", "culture", "low", timedelta(days=2, hours=21),
     timedelta(hours=2, minutes=30), "Arena estiva", "Via del Cinema, Modena", 44.6473, 10.9281, ["outdoor"]),
    ("Concerto acustico", "Ingresso libero con prenotazione", "music", "free", timedelta(days=6, hours=19),
     timedelta(hours=2), "Chiostro San Pietro", "Via San Pietro, Modena", 44.6422, 10.9197, ["outdoor", "live"]),
    ("Corso gratuito fotografia", "Base per principianti", "culture", "free", timedelta(days=7, hours=17),
     timedelta(hours=2), "Centro Civico", "Via Emilia Ovest, Modena", 44.6389, 10.9184, ["indoor"]),
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--delete", action="store_true", help="rimuove gli eventi demo")
    args = p.parse_args()

    db = client()
    coll = db.collection("events")
    batch = db.batch()
    now = datetime.now(timezone.utc)
    ms = lambda d: int(d.timestamp() * 1000)  # noqa: E731
    for i, (title, desc, cat, price, offset, dur, venue, addr, lat, lng, tags) in enumerate(SAMPLES, 1):
        ref = coll.document(f"demo-{i:02d}")
        if args.delete:
            batch.delete(ref)
            continue
        batch.set(ref, {
            "title": title, "shortDescription": desc, "category": cat, "priceType": price,
            "startTime": ms(now + offset), "endTime": ms(now + offset + dur),
            "venueName": venue, "address": addr, "lat": lat, "lng": lng,
            "imageUrl": "", "ticketUrl": "", "tags": tags,
            "source": "manual", "sourceUrl": "", "createdAt": ms(now), "updatedAt": ms(now),
        })
    batch.commit()
    print(f"{len(SAMPLES)} eventi demo {'rimossi' if args.delete else 'caricati'}")


if __name__ == "__main__":
    main()
