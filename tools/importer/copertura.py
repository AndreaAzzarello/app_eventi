"""Report di copertura: reports/copertura_er.md. Non attiva nessun comune e non scrive su Firestore.

Uso:  python copertura.py                 # stima gli eventi dei comuni design_comuni_html e scrive il report
      python copertura.py --no-estimate   # solo i conteggi del registro
La stima è un dry-run limitato per comune: 1 pagina di lista + sitemap + al massimo 10 pagine di dettaglio, senza
geocoding. Conta gli eventi futuri (entro 60 giorni) tra quelle pagine: è un minimo, non il totale.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

from adapters import CMS_ADAPTERS
from adapters.design_comuni_html import DesignComuniHtmlAdapter
from detect_cms import is_open
from geo import PROVINCES
from registry import USER_AGENT, base_url, read_rows

REPORT = Path(__file__).parent / "reports" / "copertura_er.md"
SAMPLE_PAGES = 10


def estimate(client: httpx.Client, r: dict, now: datetime) -> tuple[int | None, str]:
    """(eventi futuri trovati nel campione, errore)."""
    a = DesignComuniHtmlAdapter(r["comune"], base_url(r["sito"]), r["comune"], r["provincia"], r["regione"],
                                PROVINCES.get(r["provincia"], ("", None))[1], r["url_eventi"],
                                max_pages=1, max_details=SAMPLE_PAGES)
    try:
        return sum(1 for _ in a.events(client, now, 60)), ""
    except Exception as e:  # un comune difettoso non ferma gli altri
        return None, type(e).__name__


def recommend(r: dict, n: int | None) -> tuple[str, str]:
    lic = r["licenza"]
    if r["robots_ok"] == "no" or lic.startswith(("CC-BY-NC", "CC-BY-ND")) or lic == "riservata":
        return "escludere", "robots o licenza restrittiva"
    if not is_open(lic):
        return "da verificare a mano", "licenza sui contenuti non confermata"
    if n is None:
        return "da verificare a mano", "sito non leggibile dall'adapter"
    if n == 0:
        return "da verificare a mano", "licenza ok ma nessun evento futuro nel campione"
    return "attivare", f"licenza aperta, almeno {n} eventi futuri"


def render(rows: list[dict], est: dict[str, tuple[int | None, str]]) -> str:
    seen = [r for r in rows if r["cms"]]
    out = [f"# Copertura Emilia-Romagna ({datetime.now().date()})", "",
           f"{len(rows)} comuni nel registro, {len(seen)} analizzati. Nessuno stato è stato modificato da questo report.", "",
           "## Comuni per CMS / adapter", "", "| CMS | adapter | comuni | attivi | licenza aperta sui contenuti |", "|---|---|---|---|---|"]
    for cms, n in Counter(r["cms"] for r in seen).most_common():
        grp = [r for r in seen if r["cms"] == cms]
        out.append(f"| {cms} | {'sì' if cms in CMS_ADAPTERS else 'no'} | {n} | {sum(r['stato'] == 'attivo' for r in grp)} "
                   f"| {sum(is_open(r['licenza']) for r in grp)} |")
    html = [r for r in rows if r["cms"] == "design_comuni_html"]
    out += ["", "## Modello Design Comuni (design_comuni_html) per fornitore", "", "| fornitore | comuni |", "|---|---|",
            *[f"| {v or '(non riconosciuto)'} | {n} |" for v, n in Counter(r["fornitore"] for r in html).most_common()], ""]
    out += ["## Stato del registro", "", *[f"- {k}: {v}" for k, v in Counter(r["stato"] for r in rows).most_common()], ""]
    if est:
        recs = {r["comune"]: recommend(r, est[r["comune"]][0]) for r in html if r["comune"] in est}
        out += ["## Raccomandazioni per i comuni design_comuni_html", "",
                "- " + ", ".join(f"{k}: {v}" for k, v in Counter(x[0] for x in recs.values()).most_common()),
                f"- Eventi futuri trovati nel campione (minimo, ≤{SAMPLE_PAGES} pagine a comune): "
                f"{sum(n or 0 for n, _ in est.values())}", "",
                "| comune | prov. | fornitore | licenza | robots | eventi (campione) | raccomandazione | motivo |",
                "|---|---|---|---|---|---|---|---|"]
        order = {"attivare": 0, "da verificare a mano": 1, "escludere": 2}
        for r in sorted(html, key=lambda r: (order[recs[r["comune"]][0]], -(est[r["comune"]][0] or 0), r["comune"])):
            n, err = est[r["comune"]]
            rec, why = recs[r["comune"]]
            out.append(f"| {r['comune']} | {r['provincia']} | {r['fornitore'] or '?'} | {r['licenza'] or '?'} | "
                       f"{r['robots_ok'] or '?'} | {n if n is not None else err} | {rec}{' (attivo)' * (r['stato'] == 'attivo')} | {why} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-estimate", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    rows = read_rows()
    est: dict[str, tuple[int | None, str]] = {}
    if not args.no_estimate:
        todo = [r for r in rows if r["cms"] == "design_comuni_html" and r["sito"]]
        now = datetime.now(timezone.utc)
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client, \
                ThreadPoolExecutor(args.workers) as pool:
            for r, res in zip(todo, pool.map(lambda r: estimate(client, r, now), todo)):
                est[r["comune"]] = res
                print(f"{r['comune']:<28} {res[0] if res[0] is not None else res[1]}", flush=True)
    REPORT.write_text(render(rows, est), encoding="utf-8")
    print(f"Scritto {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
