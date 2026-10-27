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


# Emilia-Romagna: nome per le query a Nominatim e riquadro (lon_min, lat_max, lon_max, lat_min) della provincia.
# Riquadri approssimati e un po' larghi: servono a scartare le omonimie lontane, non a tracciare i confini.
PROVINCES = {
    "PC": ("Piacenza", "9.15,45.20,10.10,44.45"),
    "PR": ("Parma", "9.55,45.05,10.55,44.30"),
    "RE": ("Reggio Emilia", "10.15,44.98,10.95,44.15"),
    "MO": ("Modena", "10.40,45.00,11.40,44.10"),
    "BO": ("Bologna", "10.85,44.90,12.05,43.85"),
    "FE": ("Ferrara", "11.20,45.05,12.45,44.50"),
    "RA": ("Ravenna", "11.50,44.65,12.50,44.00"),
    "FC": ("Forlì-Cesena", "11.60,44.40,12.50,43.70"),
    "RN": ("Rimini", "12.10,44.25,12.85,43.75"),
}


def in_viewbox(lat: float, lng: float, viewbox: str | None) -> bool:
    if not viewbox:
        return True
    lon_min, lat_max, lon_max, lat_min = (float(x) for x in viewbox.split(","))
    return lat_min <= lat <= lat_max and lon_min <= lng <= lon_max


def slugify(s: str) -> str:
    """Come slugify() in TypeScript: niente accenti, minuscolo, trattini, massimo 70 caratteri."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:70].rstrip("-")


#: enti sovra-comunali che Nominatim mette in "municipality" al posto del comune
UNION_RE = re.compile(r"^(unione|comunit[àa]|unione montana)\b", re.I)
#: dal più al meno probabile come frazione da mostrare accanto al comune
LOCALITY_KEYS = ("town", "village", "hamlet")


def place_from_nominatim(address: dict | None, city: str | None = None, province: str | None = None) -> dict | None:
    """addressdetails di Nominatim → {city, citySlug, province (sigla), region, locality}.

    city: comune della fonte. Nominatim chiama "village"/"town" anche le frazioni (e a volte il comune stesso:
    Rottofreno è village, San Nicolò a Trebbia è town), e "municipality" può essere un'Unione di comuni
    (Minerbio → "Unione Terre di Pianura"). Quindi: se uno dei nomi dell'indirizzo è il comune della fonte, è
    quello; altrimenti vale municipality/city/town; se c'è solo una frazione, il comune è quello della fonte.
    La frazione va in "locality". None (= usa la fonte) se l'indirizzo è vuoto o in un'altra provincia.
    """
    if not address:
        return None
    iso = address.get("ISO3166-2-lvl6", "")
    prov = iso[3:] if iso.startswith("IT-") else ""
    if province and prov and prov != province:
        return None
    names = {k: address[k] for k in ("municipality", "city", "town", "village", "hamlet")
             if address.get(k) and not UNION_RE.match(address[k])}
    if not names:
        return None
    own = bool(city) and any(slugify(v) == slugify(city) for v in names.values())
    name = city if own else (names.get("municipality") or names.get("city") or names.get("town")
                             or city or names.get("village") or names.get("hamlet"))
    locality = next((names[k] for k in LOCALITY_KEYS if k in names and slugify(names[k]) != slugify(name)), "")
    return {
        "city": name,
        "citySlug": slugify(name),
        "province": prov or province or "",
        "region": address.get("state", ""),
        "locality": locality,
    }


def enrich(ev: dict, place: dict | None, fallback: dict) -> dict:
    """Aggiunge geohash e località a un evento con lat/lng. fallback: località nota della fonte."""
    ev["geohash"] = geohash(ev["lat"], ev["lng"])
    loc = place or fallback
    ev["city"] = loc["city"]
    ev["citySlug"] = loc.get("citySlug") or slugify(loc["city"])
    ev["province"] = loc.get("province", "")
    ev["region"] = loc.get("region", "")
    if loc.get("locality"):
        ev["locality"] = loc["locality"]
    return ev
