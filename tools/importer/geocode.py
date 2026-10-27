"""Geocoding con Nominatim e cache su file, nel rispetto della policy OSM:
User-Agent identificativo, massimo 1 richiesta al secondo, risultati solo in Italia."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from geo import place_from_nominatim

NOMINATIM = "https://nominatim.openstreetmap.org"


class Geocoder:
    def __init__(self, client: httpx.Client, cache_path: Path):
        self._client = client
        self._path = cache_path
        self._cache: dict[str, object] = (
            json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
        )
        self._last = 0.0
        self.requests = 0

    def _get(self, endpoint: str, params: dict):
        wait = self._last + 1.0 - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        self.requests += 1
        res = self._client.get(f"{NOMINATIM}/{endpoint}", params={
            "format": "jsonv2", "accept-language": "it", **params})
        res.raise_for_status()
        return res.json()

    def lookup(self, query: str, viewbox: str | None = None) -> tuple[float, float] | None:
        """Indirizzo → (lat, lng). viewbox "lon_min,lat_max,lon_max,lat_min" scarta le omonimie lontane."""
        key = query.strip().lower()  # le query contengono già il comune: la cache esistente resta valida
        if key in self._cache:  # anche i "non trovato", per non richiederli ogni giorno
            hit = self._cache[key]
            return (hit[0], hit[1]) if hit else None
        params = {"q": query, "limit": 1, "countrycodes": "it"}
        if viewbox:
            params |= {"viewbox": viewbox, "bounded": 1}
        data = self._get("search", params)
        hit = [float(data[0]["lat"]), float(data[0]["lon"])] if data else None
        self._cache[key] = hit
        return (hit[0], hit[1]) if hit else None

    def reverse(self, lat: float, lng: float) -> dict | None:
        """Coordinate → {city, citySlug, province, region}. Cache a ~100 m (3 decimali)."""
        key = f"rev:{lat:.3f},{lng:.3f}"
        if key not in self._cache:
            data = self._get("reverse", {"lat": f"{lat:.3f}", "lon": f"{lng:.3f}", "zoom": 14, "addressdetails": 1})
            self._cache[key] = place_from_nominatim(data.get("address")) if isinstance(data, dict) else None
        return self._cache[key]

    def save(self) -> None:
        self._path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=1), encoding="utf-8")
