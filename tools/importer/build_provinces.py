"""Genera provinces.json: per ogni sigla di provincia il nome (ISTAT) e il riquadro (OpenStreetMap).

Uso:  python build_provinces.py
Dati: ISTAT "Elenco dei comuni italiani" (CC BY 4.0, nomi e sigle) · OpenStreetMap via Overpass (ODbL, riquadri).
Il riquadro è quello dei confini amministrativi (admin_level 6) più un margine di MARGIN gradi: serve a scartare
le omonimie lontane, non a tracciare i confini. La Valle d'Aosta non ha province: vale il riquadro della regione.
Una sigla ISTAT senza confine in OSM viene segnalata e lasciata fuori (niente riquadri inventati a mano).
Le province sarde della riforma 2025 (OT, OG, VS) non sono ancora nell'elenco ISTAT, che usa SS/NU/OR/SU/CA: nome e riquadro vengono da OSM.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

import httpx

from registry import USER_AGENT

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY = ('[out:json][timeout:120];(relation["boundary"="administrative"]["admin_level"="6"]["ISO3166-2"~"^IT-"];'
         'relation["boundary"="administrative"]["ISO3166-2"="IT-23"];);out tags bb;')
ISTAT_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
OUT = Path(__file__).parent / "provinces.json"
MARGIN = 0.05
#: nome già usato nelle query a Nominatim e nelle chiavi di geocache.json: cambiarlo farebbe rifare le richieste
NAME_KEEP = {"RE": "Reggio Emilia"}
AOSTA = "AO"
NEW_SARDINIA = ("OT", "OG", "VS")


def parse_overpass(data: dict, margin: float = MARGIN) -> dict[str, str]:
    """sigla → "lon_min,lat_max,lon_max,lat_min" con margine. IT-23 (Valle d'Aosta) diventa AO."""
    out = {}
    for el in data["elements"]:
        code = el.get("tags", {}).get("ISO3166-2", "")[3:]
        b = el.get("bounds")
        if not b or not code:
            continue
        code = AOSTA if code == "23" else code
        out[code] = f"{b['minlon'] - margin:.3f},{b['maxlat'] + margin:.3f},{b['maxlon'] + margin:.3f},{b['minlat'] - margin:.3f}"
    return out


def parse_overpass_names(data: dict, codes: tuple[str, ...] = NEW_SARDINIA) -> dict[str, str]:
    """sigla → nome (la parte italiana di "Tèttari/Sassari") per le province che l'ISTAT non ha ancora."""
    return {c: el["tags"]["name"].split("/")[-1].strip() for el in data["elements"]
            if (c := el.get("tags", {}).get("ISO3166-2", "")[3:]) in codes and el["tags"].get("name")}


def parse_istat_names(text: str) -> dict[str, str]:
    """sigla → nome dell'unità territoriale sovracomunale (colonne cercate per intestazione)."""
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    head = [re.sub(r"\s+", " ", h).strip().lower() for h in rows[0]]
    i_sig = next(i for i, h in enumerate(head) if h.startswith("sigla automobilistica"))
    i_name = next(i for i, h in enumerate(head) if h.startswith("denominazione dell'unità territoriale sovracomunale")
                  or h.startswith("denominazione unità territoriale sovracomunale"))
    i_reg = next(i for i, h in enumerate(head) if h.startswith("denominazione regione"))
    names = {}
    for r in rows[1:]:
        if len(r) > i_sig and r[i_sig]:
            names.setdefault(r[i_sig], r[i_name].split("/")[0].strip())
    names.setdefault(AOSTA, next((r[i_reg].split("/")[0] for r in rows[1:] if len(r) > i_reg and r[i_reg].startswith("Valle")), "Aosta"))
    return names


def build(boxes: dict[str, str], names: dict[str, str]) -> tuple[dict[str, list[str]], list[str]]:
    """→ ({sigla: [nome, riquadro]}, sigle ISTAT senza confine in OSM)."""
    provinces = {c: [NAME_KEEP.get(c, names[c]), boxes[c]] for c in sorted(names) if c in boxes}
    return provinces, sorted(set(names) - set(boxes))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=180, follow_redirects=True) as client:
        osm = client.post(OVERPASS, data={"data": QUERY}).raise_for_status().json()
        istat = client.get(ISTAT_URL).raise_for_status().content.decode("cp1252")
    provinces, missing = build(parse_overpass(osm), {**parse_overpass_names(osm), **parse_istat_names(istat)})
    OUT.write_text(json.dumps(provinces, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(provinces)} province scritte in {OUT.name}")
    if missing:
        print(f"ATTENZIONE: sigle ISTAT senza confine in OSM, escluse: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
