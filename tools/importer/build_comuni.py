"""Genera web/src/lib/data/comuni.json: tutti i comuni italiani per la ricerca del sito (nome, sigla, centro, popolazione).

Uso:  python build_comuni.py            # usa la cache in .httpcache se c'è
      python build_comuni.py --refresh  # riscarica ISTAT e Wikidata
Dati: ISTAT "Elenco dei comuni italiani" (CC BY 4.0: codici, nomi, nomi bilingui, sigle) ·
      Wikidata (CC0: coordinate del centro, popolazione più recente, nome francese per la Valle d'Aosta).
I due elenchi si uniscono per codice ISTAT. Un comune senza coordinate in Wikidata resta fuori dal file e viene
segnalato (niente coordinate inventate a mano); test_build_comuni.py ne fissa il numero massimo.
Formato (compatto, lo legge web/src/lib/comuni.ts):
  {"v": 1, "regioni": [nome…], "c": [[nome, nome altra lingua|"", sigla, indice regione, lat, lng, popolazione, slug|""]…]}
Lo slug è slugify(nome); per gli omonimi, tutti quelli del gruppo hanno anche la sigla (samone-to, samone-tn).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import httpx

from build_registry import ISTAT_URL, SARDINIA
from geo import PROVINCES, in_viewbox, slugify
from registry import USER_AGENT

HERE = Path(__file__).parent
CACHE = HERE / ".httpcache"
OUT = HERE.parent.parent / "web" / "src" / "lib" / "data" / "comuni.json"
SPARQL = "https://query.wikidata.org/sparql"
# Comuni italiani attivi (Q747074 e sottoclassi: i comuni valdostani ne usano una) con codice ISTAT (P635) e coordinate (P625); popolazione (P1082) con la sua data (P585).
QUERY = """SELECT ?code ?coord ?pop ?d ?fr ?it WHERE {
  ?c wdt:P31/wdt:P279* wd:Q747074; wdt:P635 ?code; wdt:P625 ?coord.
  FILTER NOT EXISTS { ?c wdt:P576 ?end }
  OPTIONAL { ?c rdfs:label ?fr FILTER(LANG(?fr) = "fr") }
  OPTIONAL { ?c rdfs:label ?it FILTER(LANG(?it) = "it") }
  OPTIONAL { ?c p:P1082 ?s. ?s ps:P1082 ?pop. OPTIONAL { ?s pq:P585 ?d } }
}"""
AOSTA = "Valle d'Aosta"
SARDINIA_BOX = "8.1,41.4,9.9,38.8"  # lon_min,lat_max,lon_max,lat_min, come in provinces.json


def parse_istat(text: str) -> list[dict]:
    """Un dict per comune: codice, nome (italiano), alt (altra lingua, se c'è), sigla, regione. Colonne cercate per intestazione."""
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    head = [re.sub(r"\s+", " ", h).strip().lower() for h in rows[0]]
    col = lambda start: next(i for i, h in enumerate(head) if h.startswith(start))  # noqa: E731
    i_cod, i_name, i_alt = col("codice comune formato alfanumerico"), col("denominazione in italiano"), col("denominazione altra lingua")
    i_reg, i_sig = col("denominazione regione"), col("sigla automobilistica")
    out = []
    for r in rows[1:]:
        if len(r) <= i_sig or not r[i_cod].strip():
            continue
        out.append({"codice": r[i_cod].strip(), "nome": r[i_name].strip(), "alt": r[i_alt].strip(), "sigla": r[i_sig].strip(),
                    "regione": r[i_reg].split("/")[0].strip()})
    return out


def parse_wikidata(data: dict) -> dict[str, dict]:
    """codice ISTAT → {lat, lng, pop, fr}; la popolazione è quella con la data più recente (senza data, l'ultima letta)."""
    out: dict[str, dict] = {}
    best: dict[str, str] = {}
    for b in data["results"]["bindings"]:
        code = b["code"]["value"]
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", b["coord"]["value"])
        if not m:
            continue
        e = out.setdefault(code, {"lat": float(m[2]), "lng": float(m[1]), "pop": 0, "fr": "", "it": ""})
        e["fr"] = b.get("fr", {}).get("value", e["fr"])
        e["it"] = b.get("it", {}).get("value", e["it"])
        if "pop" in b:
            day = b.get("d", {}).get("value", "")
            if code not in best or day >= best[code]:
                best[code] = day
                e["pop"] = int(float(b["pop"]["value"]))
    return out


def build(istat: list[dict], wiki: dict[str, dict]) -> tuple[dict, list[dict]]:
    """→ (dataset nel formato del file, comuni ISTAT senza coordinate)."""
    regions = sorted({r["regione"] for r in istat})
    # Dove i codici non coincidono (Sardegna: Wikidata ha quelli precedenti alla riforma) si ripiega sul nome,
    # solo con le voci Wikidata non già usate e solo se il nome è univoco tra queste.
    spare = Counter(slugify(w["it"]) for c, w in wiki.items() if c not in {r["codice"] for r in istat})
    by_name = {slugify(w["it"]): w for c, w in wiki.items() if c not in {r["codice"] for r in istat} and spare[slugify(w["it"])] == 1}
    match = lambda r: wiki.get(r["codice"]) or by_name.get(slugify(r["nome"]))  # noqa: E731
    missing = [r for r in istat if not match(r)]
    rows = []
    for r in istat:
        w = match(r)
        if not w:
            continue
        alt = r["alt"]
        # La Valle d'Aosta è bilingue ma l'ISTAT non riporta il nome francese: viene da Wikidata, solo se diverso.
        if not alt and r["regione"] == AOSTA and slugify(w["fr"]) not in ("", slugify(r["nome"])):
            alt = w["fr"]
        rows.append({**r, "alt": alt, "lat": round(w["lat"], 3), "lng": round(w["lng"], 3), "pop": w["pop"]})
    rows.sort(key=lambda r: (slugify(r["nome"]), r["sigla"]))
    dup = {s for s, n in Counter(slugify(r["nome"]) for r in rows).items() if n > 1}
    index = {n: i for i, n in enumerate(regions)}
    c = [[r["nome"], r["alt"], r["sigla"], index[r["regione"]], r["lat"], r["lng"], r["pop"],
          f'{slugify(r["nome"])}-{r["sigla"].lower()}' if slugify(r["nome"]) in dup else ""] for r in rows]
    return {"v": 1, "regioni": regions, "c": c}, missing


def outside_province(data: dict) -> list[str]:
    """Comuni il cui centro cade fuori dal riquadro della propria provincia (sigle senza riquadro: non controllate)."""
    # Le province sarde sono cambiate con la riforma (OT, OG, VS, CI tornano e se ne vanno): per la Sardegna vale il riquadro dell'isola.
    box = lambda sig: SARDINIA_BOX if sig in SARDINIA else PROVINCES[sig][1] if sig in PROVINCES else None  # noqa: E731
    return [f"{n} ({sig})" for n, _a, sig, _r, lat, lng, *_ in data["c"] if not in_viewbox(lat, lng, box(sig))]


def cached(name: str, refresh: bool, fetch):
    path = CACHE / name
    if refresh or not path.exists():
        CACHE.mkdir(exist_ok=True)
        path.write_bytes(fetch())
    return path.read_bytes()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="riscarica ISTAT e Wikidata")
    args = ap.parse_args()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=180, follow_redirects=True) as client:
        istat = cached("comuni-istat.csv", args.refresh, lambda: client.get(ISTAT_URL).raise_for_status().content).decode("cp1252")
        wiki = json.loads(cached("comuni-wikidata.json", args.refresh, lambda: client.get(
            SPARQL, params={"query": QUERY, "format": "json"}, headers={"Accept": "application/sparql-results+json"}).raise_for_status().content))
    data, missing = build(parse_istat(istat), parse_wikidata(wiki))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(data['c'])} comuni scritti in {OUT} ({OUT.stat().st_size // 1024} KB)")
    if missing:
        print(f"ATTENZIONE: {len(missing)} comuni ISTAT senza coordinate in Wikidata, esclusi: " + ", ".join(f"{r['nome']} ({r['sigla']})" for r in missing))
    if bad := outside_province(data):
        print(f"ATTENZIONE: {len(bad)} comuni fuori dal riquadro della provincia: " + ", ".join(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
