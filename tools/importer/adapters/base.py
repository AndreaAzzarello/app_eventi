"""Interfaccia comune delle fonti. Per aggiungerne una: una classe con questi attributi e metodi,
registrata in adapters/__init__.py. run.py pensa a geocoding, località, geohash, deduplica e scrittura."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol

import httpx


class Adapter(Protocol):
    name: str
    #: origine del sito (https://host), per sapere quali eventi in archivio appartengono alla fonte
    base: str
    #: comune/provincia/regione della fonte, usati se il reverse geocoding non risponde
    city: str
    province: str
    region: str
    #: "lon_min,lat_max,lon_max,lat_min" per il geocoding degli indirizzi (o None)
    viewbox: str | None

    def events(self, client: httpx.Client, now: datetime, horizon_days: int) -> Iterable[dict]:
        """Eventi nel modello dell'app, con "id" (event_id(url)) ma senza geohash né località normalizzate.

        Campi: title, shortDescription, category, priceType, startTime, endTime (ms), venueName, address,
        lat, lng (None se da geocodificare), imageUrl, ticketUrl, tags, source="scraper", sourceUrl e
        "_geocode": indirizzi da provare con Nominatim, in ordine.
        """
        ...


def fallback_place(adapter: Adapter) -> dict:
    return {"city": adapter.city, "province": adapter.province, "region": adapter.region}
