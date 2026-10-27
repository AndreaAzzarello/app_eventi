"""Verifica la licenza dei CONTENUTI dei siti candidati (+ Modena, Formigine, Sassuolo, Mirandola).

Uso:  python licenses.py                    # tutti i 27, scrive reports/licenze_er.md e aggiorna sources/*.csv
      python licenses.py --comune Imola     # solo alcuni (ripetibile; il report e il CSV coprono solo quelli)
      python licenses.py --no-csv           # non tocca i CSV
Per ogni sito cerca nella home (anche nel piè di pagina) e nei percorsi tipici le pagine "Note legali",
"Termini d'uso", "Licenza", "Privacy", ne estrae la frase testuale sulla licenza e dice se riguarda i
contenuti o solo il tema/software. Rispetta robots.txt (protego), 1 richiesta/s per host, UA del registro.
Non cambia MAI la colonna `stato`.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import unquote
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from detect_cms import is_open, is_restrictive, license_of, links_of
from fetch import CACHE_DIR, Blocked, Fetcher, RobotsUnknown
from geo import slugify
from registry import USER_AGENT, base_url, read_rows, write_rows

EXTRA = {"modena", "formigine", "sassuolo", "mirandola"}
REPORT = Path(__file__).parent / "reports" / "licenze_er.md"
LINK_TEXT = re.compile(r"note legali|termini d.uso|condizioni d.uso|licenz|privacy|condizioni di utilizzo|copyright", re.I)
LINK_PATH = re.compile(r"note[-_]legali|termini|condizioni|licenz|privacy|copyright", re.I)
TYPICAL = ["/note-legali", "/it/note-legali", "/it-it/note-legali", "/note-legali-e-privacy", "/privacy",
           "/it/privacy", "/termini-di-utilizzo", "/licenza", "/amministrazione-trasparente"]
MAX_PAGES = 8
LICENSE_HIT = re.compile(r"creative\s*commons|creativecommons\.org|\bcc[\s-]*by\b|\bcc0\b|\biodl\b|licenz|riutilizzo|riutilizzabil|riuso|"
                         r"diritti riservati|copyright|riproduzione|diritto d.autore", re.I)
SOFTWARE = re.compile(r"\btema\b|theme|software|codice|\bcode\b|design system|open source|github|sviluppat|"
                      r"riusabil|riuso del|template|\bplugin\b|agid", re.I)
CONTENT = re.compile(r"contenut|testi|\bdati\b|immagin|informazioni|documenti|pubblicat|materiali|sito", re.I)
BLOCK = re.compile(r"</?(p|div|li|ul|ol|br|h[1-6]|tr|td|footer|section|article|nav|header|table)\b[^>]*>", re.I)


def sentences(html: str) -> list[str]:
    """Frasi del testo visibile; i link a creativecommons.org restano come URL nel testo."""
    h = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", html)
    h = re.sub(r'(?is)<a\b[^>]*href=["\']([^"\']*creativecommons[^"\']*)["\'][^>]*>', r" \1 ", h)
    h = BLOCK.sub("\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"https?://\S*safelinks\S*?url=(https?%3A%2F%2F[^&\s]+)\S*", lambda m: unquote(m.group(1)), unescape(h))
    h = re.sub(r"https?://(?![^\s]*creativecommons)\S+", " ", h)  # URL non-CC (safelinks ecc.) sono rumore
    out = []
    for line in h.split("\n"):
        line = " ".join(line.split())
        out += [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú])", line) if s.strip()]
    return out


def best_sentence(html: str) -> str:
    """La frase più pertinente sulla licenza: prima CC/Creative Commons, poi 'licenza', poi il resto."""
    ss = sentences(html)
    # un titolo ("Riutilizzo dei dati pubblicati") da solo non dice nulla: gli si accoda la frase dopo
    ss = [s + " " + ss[i + 1] if len(s) < 60 and not s.endswith(".") and i + 1 < len(ss) else s for i, s in enumerate(ss)]
    hits = [s for s in ss if LICENSE_HIT.search(s) and 25 <= len(s)]
    def rank(s: str) -> int:
        return 0 if re.search(r"creative\s*commons|creativecommons|\bcc[\s-]*by", s, re.I) else 1 if re.search(r"licenz", s, re.I) else 2
    hits = [s for s in hits if rank(s) < 2 or re.search(r"riutilizzo|riutilizzabil|riuso|tutti i contenuti|riproduzione", s, re.I)]  # copyright/privacy generici no
    if not hits:
        return ""
    s = min(hits, key=lambda s: (rank(s), license_of(s) == "non trovata", not re.search(r"riuso|riutilizz|contenut", s, re.I), len(s)))
    if len(s) > 300 and (m := LICENSE_HIT.search(s)):  # tronca attorno alla licenza, non in testa
        a = max(0, min(m.start() - 150, len(s) - 300))
        s = s[a:a + 300]
    return s[:300]


def classify(sentence: str) -> str:
    if not sentence:
        return "non-trovata"
    sw, ct = bool(SOFTWARE.search(sentence)), bool(CONTENT.search(sentence))
    if sw and not re.search(r"contenut|\bdati\b|testi", sentence, re.I):
        return "solo-software"
    return "contenuti" if ct and not sw else "non-chiara"


def robots_state(f: Fetcher, url: str) -> str:
    p = urlsplit(url)
    ok = f.allowed(url)
    return "sconosciuto" if ok is None else "si" if ok else "no"


def get(f: Fetcher, url: str) -> httpx.Response | None:
    try:
        r = f.get(url)
        return r if r.status_code < 400 else None
    except (Blocked, RobotsUnknown, httpx.HTTPError):
        return None


def analyze(f: Fetcher, r: dict) -> dict:
    base = base_url(r["sito"])
    res = {"comune": r["comune"], "cms": r["cms"], "url_eventi": r["url_eventi"], "pagina": "", "frase": "",
           "classe": "non-trovata", "conflitto": False, "robots_eventi": "n/d", "robots_api": "", "api": "", "errore": ""}
    api = base + ("/++api++/@search" if r["cms"] == "plone" else "/wp-json/wp/v2/")
    if r["cms"] == "design_comuni_html":  # l'adapter legge le pagine HTML della sezione eventi
        api = r["url_eventi"] or base + "/"
    res["api"] = api
    res["robots_api"] = robots_state(f, api)
    if r["url_eventi"]:
        res["robots_eventi"] = robots_state(f, r["url_eventi"])
    home = get(f, base + "/")
    if home is None:
        res["errore"] = "home non raggiungibile o vietata da robots"
        return res
    base = base_url(str(home.url))
    host = urlsplit(base).netloc
    cands: list[str] = []
    for url, text in links_of(home.text, base):
        if urlsplit(url).netloc == host and (LINK_TEXT.search(text) or LINK_PATH.search(urlsplit(url).path)):
            if url not in cands:
                cands.append(url)
    cands += [base + t for t in TYPICAL if base + t not in cands]
    # prima il piè di pagina della home (link CC diretti), poi le pagine legali
    pages = [(base + "/", home.text)]
    for url in cands[:MAX_PAGES + len(TYPICAL)]:
        if len(pages) > MAX_PAGES:
            break
        if (resp := get(f, url)) is not None and resp.text.strip():
            pages.append((str(resp.url), resp.text))
    found = []
    # clausola restrittiva sulla stessa pagina della licenza aperta: l'automatismo non può decidere
    res["conflitto"] = any(re.search(r"esclusiva proprietà|tutti i diritti riservati", html, re.I) for _, html in pages[1:])
    for url, html in pages:
        if s := best_sentence(html):
            found.append((0 if re.search(r"creative\s*commons|creativecommons|\bcc[\s-]*by", s, re.I) else 1, url != base + "/", url, s))
    if found:
        # tra le frasi sulla licenza, preferisci quella che dice "contenuti" (le note legali valgono più del footer)
        _, _, res["pagina"], res["frase"] = min(found, key=lambda x: (classify(x[3]) != "contenuti", x[0], x[1]))
        res["classe"] = classify(res["frase"])
    else:
        res["errore"] = f"{len(pages)} pagine controllate, nessuna frase sulla licenza"
    return res


def recommend(a: dict) -> tuple[str, str]:
    """(licenza per il CSV, raccomandazione)."""
    lic = license_of(a["frase"]) if a["frase"] else "non trovata"
    if a["robots_api"] == "no" or a["robots_eventi"] == "no" or is_restrictive(lic):
        return (lic if a["classe"] == "contenuti" else a["classe"]), "escludere"
    csv_lic = lic if a["classe"] == "contenuti" and lic != "non trovata" else         {"contenuti": "non-chiara", "non-trovata": "non trovata"}.get(a["classe"], a["classe"])
    ok = not a["conflitto"] and a["classe"] == "contenuti" and is_open(lic) and a["robots_api"] == "si" and a["robots_eventi"] in ("si", "n/d")
    return csv_lic, "attivare" if ok else "da verificare a mano"


def render(results: list[dict]) -> str:
    cnt = Counter(a["raccomandazione"] for a in results)
    cls = Counter(a["classe"] for a in results)
    out = ["# Licenze dei contenuti: comuni Emilia-Romagna", "",
           "## Metodo", "",
           "- Per ogni comune (candidati WordPress/Plone più Modena, Formigine, Sassuolo, Mirandola) lo script `licenses.py` "
           "scarica la home e cerca i link a note legali, termini d'uso, condizioni d'uso, licenza, privacy (anche nel piè di pagina) "
           "e prova percorsi tipici (`/note-legali`, `/it/note-legali`, `/privacy`, `/amministrazione-trasparente`...).",
           "- Dalle pagine estrae la frase testuale che nomina CC-BY / Creative Commons / licenza (max 300 caratteri, riportata senza modifiche).",
           "- Classe: `contenuti` (la licenza riguarda testi, dati, immagini del sito), `solo-software` (riguarda tema, codice, design system), "
           "`non-chiara`, `non-trovata`. La classificazione è euristica sulle parole della frase: le `contenuti` vanno comunque lette.",
           "- Robots (protego, UA `" + USER_AGENT + "`): pagina eventi e percorso API usato dall'adapter "
           "(Plone `/++api++/@search`, WordPress `/wp-json/wp/v2/`).",
           "- Regola: **attivare** solo se la frase attesta licenza aperta sui CONTENUTI e robots permette l'API; **escludere** se robots vieta "
           "o la licenza è restrittiva; altrimenti **da verificare a mano**. Nessuno `stato` è stato modificato.", "",
           "## Riepilogo", "",
           f"- Comuni analizzati: {len(results)}",
           "- Raccomandazione: " + ", ".join(f"{k} {v}" for k, v in cnt.most_common()),
           "- Classe licenza: " + ", ".join(f"{k} {v}" for k, v in cls.most_common()), "",
           "## Tabella", "",
           "| comune | CMS | licenza | frase (pagina) | robots | raccomandazione |", "|---|---|---|---|---|---|"]
    for a in results:
        frase = f"«{a['frase']}» ({a['pagina']})" if a["frase"] else (a["errore"] or "nessuna frase trovata")
        frase += " **Attenzione: nelle note legali c'è anche una clausola restrittiva (esclusiva proprietà / diritti riservati).**" * a["conflitto"]
        robots = f"eventi: {a['robots_eventi']}; API: {a['robots_api']}"
        out.append("| " + " | ".join(x.replace("|", "\\|") for x in
                   (a["comune"], a["cms"], a["licenza"], frase, robots, a["raccomandazione"])) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--comune", action="append", help="solo questo comune (ripetibile)")
    p.add_argument("--cms", help="tutti i comuni con questo CMS (es. design_comuni_html), non solo i candidati")
    p.add_argument("--regione", action="append", help="solo questa regione (ripetibile), per esempio lombardia")
    p.add_argument("--out", type=Path, default=REPORT, help="file del report")
    p.add_argument("--no-csv", action="store_true", help="non aggiornare i CSV")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    rows = read_rows()
    only = {c.lower() for c in args.comune} if args.comune else None
    regions = {slugify(x) for x in args.regione or []}
    todo = [r for r in rows if r["sito"] and (not regions or slugify(r["regione"]) in regions) and (r["comune"].lower() in only if only else
                                              r["cms"] == args.cms if args.cms else
                                              r["stato"] == "candidato" or r["comune"].lower() in EXTRA)]
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
        fetcher = Fetcher(client, cache_dir=CACHE_DIR)
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda r: analyze(fetcher, r), todo))
    for r, a in zip(todo, results):
        a["licenza"], a["raccomandazione"] = recommend(a)
        print(f"{a['comune']:<24} {a['cms']:<14} {a['classe']:<14} {a['licenza']:<12} {a['raccomandazione']}", flush=True)
        if not args.no_csv:  # `stato` non si tocca
            r["licenza"] = a["licenza"]
            # [raccomandazione] e "conflitto" servono ad activate.py: la clausola restrittiva non sta in altre colonne
            tag = f"licenza[{a['raccomandazione'].split()[0]}]" + (" conflitto" if a["conflitto"] else "")
            r["note"] = (f"{tag}: {a['pagina']} — «{a['frase']}»" if a["frase"]
                         else f"{tag}: non trovata ({a['errore'] or 'nessuna pagina'})")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(results), encoding="utf-8")
    if not args.no_csv:
        write_rows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
