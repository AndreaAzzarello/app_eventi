"""Geocoding con Nominatim e cache su file, nel rispetto della policy OSM:
User-Agent identificativo, massimo 1 richiesta al secondo, risultati solo in Italia."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

NOMINATIM = "https://nominatim.openstreetmap.org/search"
# Provincia di Modena (lon_min, lat_max, lon_max, lat_min): scarta omonimie in altre regioni.
VIEWBOX = "10.40,45.00,11.40,44.10"


class Geocoder:
    def __init__(self, client: httpx.Client, cache_path: Path):
        self._client = client
        self._path = cache_path
        self._cache: dict[str, list[float] | None] = (
            json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
        )
        self._last = 0.0
        self.requests = 0

    def lookup(self, query: str) -> tuple[float, float] | None:
        key = query.strip().lower()
        if key in self._cache:  # anche i "non trovato", per non richiederli ogni giorno
            hit = self._cache[key]
            return (hit[0], hit[1]) if hit else None
        wait = self._last + 1.0 - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        self.requests += 1
        res = self._client.get(NOMINATIM, params={
            "q": query, "format": "jsonv2", "limit": 1, "countrycodes": "it",
            "viewbox": VIEWBOX, "bounded": 1, "accept-language": "it",
        })
        res.raise_for_status()
        data = res.json()
        hit = [float(data[0]["lat"]), float(data[0]["lon"])] if data else None
        self._cache[key] = hit
        return (hit[0], hit[1]) if hit else None

    def save(self) -> None:
        self._path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1), encoding="utf-8")
