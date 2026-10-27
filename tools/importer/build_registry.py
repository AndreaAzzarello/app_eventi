"""Genera/aggiorna sources/comuni.csv dagli open data ISTAT (comuni) e IndicePA (siti istituzionali).

Uso:  python build_registry.py                        # Emilia-Romagna
      python build_registry.py --regione Lombardia    # ripetibile
Le righe già nel CSV con stato attivo/manuale non vengono toccate; le altre aggiornano solo
regione, provincia, comune e sito. I comuni nuovi entrano come da_verificare.
Dati: ISTAT "Elenco dei comuni italiani" (CC-BY 3.0 IT) · IndicePA "Amministrazioni" (CC-BY 4.0).
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys

import httpx

from geo import slugify
from registry import COLUMNS, PROTECTED, USER_AGENT, base_url, read_rows, write_rows

ISTAT_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
IPA_URL = ("https://indicepa.gov.it/ipa-dati/dataset/502ff370-1b2c-4310-94c7-f39ceb7500e3/resource/"
           "3ed63523-ff9c-41f6-a6fe-980f3d9e501f/download/amministrazioni.txt")
COMUNI_TYPE = "Comuni e loro Consorzi e Associazioni"


def parse_istat(text: str, regions: set[str]) -> list[dict]:
    """Colonne cercate per intestazione (l'ISTAT le sposta di anno in anno)."""
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    head = [re.sub(r"\s+", " ", h).strip().lower() for h in rows[0]]
    col = lambda start: next(i for i, h in enumerate(head) if h.startswith(start))  # noqa: E731
    i_cod, i_name = col("codice comune formato alfanumerico"), col("denominazione in italiano")
    i_reg, i_sig = col("denominazione regione"), col("sigla automobilistica")
    want = {r.lower() for r in regions}
    return [
        {"regione": r[i_reg], "provincia": r[i_sig], "comune": r[i_name], "codice_istat": r[i_cod]}
        for r in rows[1:] if len(r) > i_sig and r[i_reg].lower() in want
    ]


def _key(name: str, provincia: str) -> tuple[str, str]:
    return slugify(name), provincia.upper()


def parse_ipa(text: str) -> dict[tuple[str, str], str]:
    """(slug comune, sigla provincia) → sito istituzionale, solo per gli enti 'Comune di …'."""
    sites: dict[tuple[str, str], str] = {}
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿")), delimiter="\t"):
        if r["tipologia_istat"] != COMUNI_TYPE or not r["des_amm"].lower().startswith("comune "):
            continue
        sito = base_url("" if r["sito_istituzionale"] in ("", "null") else r["sito_istituzionale"])
        if not sito:
            continue
        # Chiave dal campo Comune e dal nome ente ("Comune di X"): copre le differenze di grafia.
        stripped = re.sub(r"^comune (dello|della|dell'|delle|degli|dei|del|di|d')\s*", "", r["des_amm"], flags=re.I)
        for name in (r["Comune"], stripped):
            sites.setdefault(_key(name, r["Provincia"]), sito)
    return sites


def merge(existing: list[dict], comuni: list[dict], sites: dict[tuple[str, str], str]) -> list[dict]:
    by_code = {r["codice_istat"]: r for r in existing}
    for c in comuni:
        sito = sites.get(_key(c["comune"], c["provincia"]), "")
        row = by_code.get(c["codice_istat"])
        if row is None:
            by_code[c["codice_istat"]] = {k: "" for k in COLUMNS} | c | {
                "sito": sito, "stato": "da_verificare", "note": "" if sito else "auto: sito non in IndicePA"}
        elif row["stato"] not in PROTECTED:
            row.update(c)
            if sito and sito != row["sito"]:
                row["sito"] = sito  # il sito è cambiato: il rilevamento precedente non vale più
                row.update(cms="", url_eventi="", licenza="", robots_ok="")
    return list(by_code.values())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--regione", action="append", help="regione (ripetibile); default Emilia-Romagna")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=120, follow_redirects=True) as client:
        istat = client.get(ISTAT_URL).raise_for_status().content.decode("cp1252")
        ipa = client.get(IPA_URL).raise_for_status().content.decode("utf-8-sig")
    comuni = parse_istat(istat, set(args.regione or ["Emilia-Romagna"]))
    sites = parse_ipa(ipa)
    rows = merge(read_rows(), comuni, sites)
    write_rows(rows)
    with_site = sum(1 for c in comuni if sites.get(_key(c["comune"], c["provincia"])))
    print(f"Comuni: {len(comuni)}, con sito in IndicePA: {with_site}, senza: {len(comuni) - with_site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
