"""Genera/aggiorna sources/<regione>.csv dagli open data ISTAT (comuni) e IndicePA (siti istituzionali).

Uso:  python build_registry.py --regione Lombardia    # ripetibile
      python build_registry.py --tutte                # tutte le regioni italiane
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


def parse_istat(text: str, regions: set[str] | None) -> list[dict]:
    """Colonne cercate per intestazione (l'ISTAT le sposta di anno in anno)."""
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    head = [re.sub(r"\s+", " ", h).strip().lower() for h in rows[0]]
    col = lambda start: next(i for i, h in enumerate(head) if h.startswith(start))  # noqa: E731
    i_cod, i_name = col("codice comune formato alfanumerico"), col("denominazione in italiano")
    i_reg, i_sig = col("denominazione regione"), col("sigla automobilistica")
    i_alt = next((i for i, h in enumerate(head) if h.startswith("denominazione altra lingua")), None)
    want = {slugify(r) for r in regions} if regions is not None else None  # None = tutte
    out = []
    for r in rows[1:]:
        # "Trentino-Alto Adige/Südtirol", "Valle d'Aosta/Vallée d'Aoste": la regione è il nome italiano
        region = r[i_reg].split("/")[0].strip() if len(r) > i_sig else ""
        if region and (want is None or slugify(region) in want):
            alt = r[i_alt].strip() if i_alt is not None and len(r) > i_alt else ""
            out.append({"regione": region, "provincia": r[i_sig], "comune": r[i_name], "codice_istat": r[i_cod],
                        "comune_alt": alt})
    return out


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
        names = [r["Comune"], stripped] + [x for x in re.split(r"\s*/\s*|\s+-\s+", r["Comune"]) if x]  # "Bolzano - Bozen"
        for name in names:
            sites.setdefault(_key(name, r["Provincia"]), sito)
    return sites


def merge(existing: list[dict], comuni: list[dict], sites: dict[tuple[str, str], str]) -> list[dict]:
    by_code = {r["codice_istat"]: r for r in existing}
    for c in comuni:
        sito = next((sites[k] for n in (c["comune"], c.get("comune_alt")) if n and (k := _key(n, c["provincia"])) in sites), "")
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
    p.add_argument("--regione", action="append", help="regione (ripetibile)")
    p.add_argument("--tutte", action="store_true", help="tutte le regioni")
    args = p.parse_args(argv)
    if not args.regione and not args.tutte:
        p.error("indica --regione <nome> (ripetibile) oppure --tutte")
    sys.stdout.reconfigure(encoding="utf-8")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=120, follow_redirects=True) as client:
        istat = client.get(ISTAT_URL).raise_for_status().content.decode("cp1252")
        ipa = client.get(IPA_URL).raise_for_status().content.decode("utf-8-sig")
    comuni = parse_istat(istat, None if args.tutte else set(args.regione))
    sites = parse_ipa(ipa)
    rows = merge(read_rows(), comuni, sites)
    write_rows(rows)
    with_site = sum(1 for r in rows if r["sito"] and r["codice_istat"] in {c["codice_istat"] for c in comuni})
    print(f"Comuni: {len(comuni)}, con sito in IndicePA: {with_site}, senza: {len(comuni) - with_site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
