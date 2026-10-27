"""Geohash e località normalizzate, identici alla webapp (web/src/lib/geo.ts, event.ts).

Il geohash usa lo stesso algoritmo e la stessa precisione (10) di geofire-common: le query per raggio
della webapp lavorano sugli intervalli di geohash, quindi i due lati devono produrre stringhe identiche.
"""

from __future__ import annotations

import re
import unicodedata

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
PRECISION = 10


def geohash(lat: float, lng: float, precision: int = PRECISION) -> str:
    lat_rng, lng_rng = [-90.0, 90.0], [-180.0, 180.0]
    out, bits, ch, even = [], 0, 0, True
    while len(out) < precision:
        rng, val = (lng_rng, lng) if even else (lat_rng, lat)
        mid = (rng[0] + rng[1]) / 2
        if val > mid:
            ch = (ch << 1) | 1
            rng[0] = mid
        else:
            ch <<= 1
            rng[1] = mid
        even = not even
        bits += 1
        if bits == 5:
            out.append(_BASE32[ch])
            bits, ch = 0, 0
    return "".join(out)


def slugify(s: str) -> str:
    """Come slugify() in TypeScript: niente accenti, minuscolo, trattini, massimo 70 caratteri."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70].rstrip("-")


def place_from_nominatim(address: dict | None) -> dict | None:
    """addressdetails di Nominatim → {city, citySlug, province (sigla), region}."""
    if not address:
        return None
    city = next((address[k] for k in ("city", "town", "village", "municipality", "hamlet") if address.get(k)), "")
    if not city:
        return None
    iso = address.get("ISO3166-2-lvl6", "")
    return {
        "city": city,
        "citySlug": slugify(city),
        "province": iso[3:] if iso.startswith("IT-") else "",
        "region": address.get("state", ""),
    }


def enrich(ev: dict, place: dict | None, fallback: dict) -> dict:
    """Aggiunge geohash e località a un evento con lat/lng. fallback: località nota della fonte."""
    ev["geohash"] = geohash(ev["lat"], ev["lng"])
    loc = place or fallback
    ev["city"] = loc["city"]
    ev["citySlug"] = loc.get("citySlug") or slugify(loc["city"])
    ev["province"] = loc.get("province", "")
    ev["region"] = loc.get("region", "")
    return ev
