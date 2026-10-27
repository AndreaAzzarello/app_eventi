"""Registro delle fonti: sources/comuni.csv (UTF-8 con BOM, separatore ";", si apre in Excel).

Stati: da_verificare (appena creata o dubbia) · candidato (CMS supportato, robots e licenza ok: serve la tua
conferma) · escluso (robots lo vieta o licenza restrittiva) · attivo (l'importer la legge) · manuale (a mano:
gli script automatici non la toccano mai).
"""

from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "EventiVicini-importer/1.0 (+https://github.com/AndreaAzzarello/app_eventi)"
PATH = Path(__file__).parent / "sources" / "comuni.csv"
COLUMNS = ["regione", "provincia", "comune", "codice_istat", "sito", "url_eventi", "cms", "fornitore", "stato",
           "licenza", "robots_ok", "note"]
PROTECTED = {"manuale", "attivo"}  # righe che gli script automatici non modificano


def read_rows(path: Path = PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{c: (r.get(c) or "").strip() for c in COLUMNS} for r in csv.DictReader(f, delimiter=";")]


def write_rows(rows: list[dict], path: Path = PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["regione"], r["provincia"], r["comune"]))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, delimiter=";", lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)


def base_url(sito: str) -> str:
    """'www.comune.x.it/it' → 'https://www.comune.x.it' (solo origine)."""
    sito = sito.strip()
    if not sito:
        return ""
    if "://" not in sito:
        sito = "https://" + sito
    p = urlsplit(sito)
    return f"{p.scheme}://{p.netloc.lower()}"
