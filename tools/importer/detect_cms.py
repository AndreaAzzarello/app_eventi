"""Visita i siti del registro e riconosce CMS, pagina eventi, licenza delle note legali e robots.txt.

Uso:  python detect_cms.py                        # righe non ancora analizzate
      python detect_cms.py --comune Modena        # una riga (ripetibile)
      python detect_cms.py --force                # rianalizza anche le righe già fatte
      python detect_cms.py --report               # solo il riepilogo, senza visitare nulla
Rispetta robots.txt prima di ogni richiesta, al massimo 1 richiesta al secondo per sito, User-Agent
identificativo. Non tocca mai le righe con stato attivo o manuale. Non attiva nessuna fonte:
al massimo propone "candidato"; "attivo" lo imposti tu nel CSV.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from fetch import CACHE_DIR, Blocked, Fetcher, RobotsUnknown
from geo import slugify
from registry import PROTECTED, USER_AGENT, base_url, read_rows, write_rows

OPEN_LICENSE = re.compile(r"^(CC0|CC-BY(-SA)?(-\d\.\d)?|IODL(-\d\.\d)?)$")
CANDIDATE_CMS = ("plone", "wordpress-dci", "design_comuni_html")
PLONE_API = "/++api++/@search?portal_type=Event&b_size=1"


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href") or "", []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def links_of(html: str, base: str) -> list[tuple[str, str]]:
    p = _Links()
    p.feed(html)
    return [(urljoin(base, h), t) for h, t in p.links if h and not h.startswith(("#", "mailto:", "tel:", "javascript:"))]


def cms_of(html: str) -> str:
    h = html.lower()
    if "design-comuni-plone-theme" in h or "/++plone++" in h or "/++theme++" in h or 'content="plone' in h:
        return "plone"
    if "design-comuni-italia" in h or "design-comuni-wordpress" in h:
        return "wordpress-dci"
    if MODEL_RE.search(h):
        return "design_comuni_html"
    return "altro"


#: marcatori del modello Designers Italia / Bootstrap Italia nell'HTML (classi cmp-*, it-*, asset del tema)
MODEL_RE = re.compile(r"bootstrap-italia|\bcmp-[a-z]|it-header-slim-wrapper|it-page-section|design-comuni")
VENDORS = [
    ("WordPress", r"wp-content/|name=.generator. content=.wordpress"), ("Drupal", r"drupal|/sites/default/files"),
    ("Joomla", r"joomla|/media/jui/"), ("ComWeb", r"epublic\.it|comweb"), ("Halley", r"halley"),
    ("Maggioli", r"maggioli|\bj-?suite\b"), ("ISWEB", r"isweb"), ("ASP.NET", r"__viewstate|\.aspx"),
]


def vendor_of(html: str) -> str:
    """Fornitore/piattaforma riconoscibile da generator, asset o piè di pagina ("" se non si capisce)."""
    h = html.lower()
    return next((name for name, rx in VENDORS if re.search(rx, h)), "")


def find_link(html: str, base: str, kind: str) -> str:
    """Prima pagina 'eventi' (kind='eventi') o 'note legali' (kind='legali') dello stesso sito."""
    host = urlsplit(base).netloc
    # "Termine" no: in tedesco sono gli appuntamenti con gli uffici
    pats = {"eventi": (r"^(eventi|agenda|eventi e manifestazioni|veranstaltungen|veranstaltungskalender|[ée]v[ée]nements|manifestations)$",
                       r"/(eventi|agenda|veranstaltungen|veranstaltungskalender|evenements|%c3%a9v%c3%a9nements)(/|$)"),
            "legali": (r"note legali|termini d.uso|condizioni d.uso|licenza", r"note[-_]legali|termini[-_]")}[kind]
    ranked = []
    for url, text in links_of(html, base):
        if urlsplit(url).netloc != host:
            continue
        if re.search(pats[0], text.lower()):
            ranked.append((0, url))
        elif re.search(pats[1], urlsplit(url).path.lower()):
            ranked.append((1, url))
    return min(ranked)[1] if ranked else ""


def license_of(text: str) -> str:
    t = " ".join(text.lower().split())
    ver = lambda m: f"-{m}" if m else ""  # noqa: E731
    # Nome per esteso in tedesco/francese ("Creative Commons Namensnennung - Nicht kommerziell 4.0"): prima le varianti restrittive
    if m := re.search(r"(?:namensnennung|attribution)\b([^.]{0,60}?)(?:(\d\.\d)|[.,;)]|$)", t):
        rest = m.group(1)
        v = ver(m.group(2) or (re.search(r"(\d\.\d)", t[m.end():m.end() + 6]) or [None, None])[1])
        if re.search(r"nicht[- ]kommerziell|non[- ]?commercial|pas d.utilisation commerciale|sans usage commercial", rest):
            return "CC-BY-NC" + v
        if re.search(r"keine bearbeitung|no[- ]?deriv|pas de modification|sans modification", rest):
            return "CC-BY-ND" + v
        if re.search(r"gleichen bedingungen|share[- ]?alike|m[êe]mes conditions", rest):
            return "CC-BY-SA" + v
        # un trattino non riconosciuto dopo "Attribution" è una variante (NC, ND…): non è CC-BY semplice
        if "creative commons" in t[:m.start()][-30:] and not rest.lstrip().startswith(("-", "–", "—")):
            return "CC-BY" + v
    if m := re.search(r"creativecommons\.org/licenses/by-(nc|nd)[a-z-]*/(\d\.\d)|cc[\s-]*by[\s-]*(nc|nd)", t):
        return f"CC-BY-{(m.group(1) or m.group(3)).upper()}" + ver(m.group(2))  # restrittiva (NC o ND)
    if m := re.search(r"creativecommons\.org/licenses/by-sa/(\d\.\d)|cc[\s-]*by[\s-]*sa[\s-]*(\d\.\d)?", t):
        return "CC-BY-SA" + ver(m.group(1) or m.group(2))
    if m := re.search(r"creativecommons\.org/licenses/by/(\d\.\d)|cc[\s-]*by[\s-]*(\d\.\d)", t):
        return "CC-BY" + ver(m.group(1) or m.group(2))
    if re.search(r"\bcc0\b|creative commons zero|publicdomain/zero", t):
        return "CC0"
    if re.search(r"\biodl\b|italian open data license", t):
        return "IODL"
    if any(x in t for x in ("tutti i diritti riservati", "all rights reserved", "alle rechte vorbehalten",
                            "tous droits réservés", "tous droits reserves")):
        return "riservata"
    return "non trovata"


def is_restrictive(lic: str) -> bool:
    return lic.startswith(("CC-BY-NC", "CC-BY-ND")) or lic == "riservata"


def is_open(lic: str) -> bool:
    return bool(OPEN_LICENSE.match(lic))


def _text(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def detect(f: Fetcher, sito: str) -> dict:
    """Campi rilevati per un sito: cms, url_eventi, licenza, robots_ok, stato, note."""
    out = {"cms": "", "fornitore": "", "url_eventi": "", "licenza": "", "robots_ok": "", "stato": "da_verificare"}
    notes: list[str] = []
    blocked = False
    try:
        home = f.get(base_url(sito) + "/")
    except Blocked:
        return out | {"robots_ok": "no", "stato": "escluso", "cms": "altro", "note": "auto: robots.txt vieta la home"}
    except RobotsUnknown:
        return out | {"cms": "irraggiungibile", "note": "auto: robots.txt non raggiungibile"}
    except httpx.HTTPError as e:
        return out | {"cms": "irraggiungibile", "note": f"auto: {type(e).__name__}"}
    if home.status_code >= 400:
        return out | {"cms": "irraggiungibile", "note": f"auto: home HTTP {home.status_code}"}

    base = base_url(str(home.url))  # dopo i redirect (es. www)
    html = home.text
    out["cms"] = cms = cms_of(html)
    out["fornitore"] = vendor_of(html)

    def fetch(url: str) -> httpx.Response | None:
        nonlocal blocked
        try:
            res = f.get(url)
            return res if res.status_code < 400 else None
        except Blocked:
            blocked = True
        except (RobotsUnknown, httpx.HTTPError):
            pass
        return None

    api_ok = False
    if cms == "plone":
        res = fetch(base + PLONE_API)
        try:
            n = res.json().get("items_total") if res is not None else None
        except ValueError:
            n = None
        api_ok = n is not None
        notes.append(f"API Plone ok, {n} eventi" if api_ok else "API Plone non disponibile")
    out["url_eventi"] = find_link(html, base, "eventi")
    if cms == "wordpress-dci":  # WordPress DCI "nativo": senza REST degli eventi serve l'adapter HTML
        res = fetch(base + "/wp-json/wp/v2/eventi?per_page=1")
        if res is None or not res.headers.get("content-type", "").startswith("application/json"):
            out["cms"] = cms = "design_comuni_html"
            notes.append("niente REST degli eventi: adapter HTML")
    if out["url_eventi"] and (res := fetch(out["url_eventi"])) is None:
        notes.append("pagina eventi non leggibile")

    legal_url = find_link(html, base, "legali")
    legal = fetch(legal_url) if legal_url else None
    out["licenza"] = lic = license_of(_text(legal.text)) if legal is not None else "non trovata"
    if lic == "non trovata":
        lic = out["licenza"] = license_of(html)  # ripiego: link alla licenza nel piè di pagina
        if lic != "non trovata":
            notes.append("licenza dal piè di pagina, non dalle note legali")
    if not legal_url:
        notes.append("note legali non trovate")

    out["robots_ok"] = "no" if blocked else "si"
    if blocked or is_restrictive(lic):
        out["stato"] = "escluso"
    elif cms in CANDIDATE_CMS and out["robots_ok"] == "si" and is_open(lic) and (api_ok or cms != "plone")             and (out["url_eventi"] or cms != "design_comuni_html"):
        out["stato"] = "candidato"
    return out | {"note": "auto: " + "; ".join(notes) if notes else ""}


def apply(row: dict, found: dict) -> None:
    keep_note = row["note"] and not row["note"].startswith("auto:")
    row.update({k: v for k, v in found.items() if not (k == "note" and keep_note)})


def report(rows: list[dict]) -> str:
    """Riepilogo in markdown: comuni per CMS, per licenza, candidati."""
    seen = [r for r in rows if r["cms"]]
    out = [f"## Registro: {len(rows)} comuni, {len(seen)} analizzati, "
           f"{sum(1 for r in rows if not r['sito'])} senza sito in IndicePA", ""]
    table = lambda title, c: out.extend(  # noqa: E731
        [f"**{title}**", "", "| | n |", "|---|---|", *[f"| {k or '(vuoto)'} | {v} |" for k, v in c.most_common()], ""])
    table("Per CMS", Counter(r["cms"] for r in seen))
    table("Per fornitore", Counter(r["fornitore"] for r in seen))
    table("Per licenza delle note legali", Counter(r["licenza"] for r in seen))
    open_n = sum(1 for r in seen if is_open(r["licenza"]))
    out += [f"**Licenza aperta: {open_n} su {len(seen)}**", ""]
    table("Per stato", Counter(r["stato"] for r in rows))
    table("robots.txt", Counter(r["robots_ok"] or "non verificato" for r in seen))
    cand = Counter((r["cms"], r["provincia"]) for r in rows if r["stato"] == "candidato")
    if cand:
        out += ["**Candidati per CMS e provincia**", "", *[f"- {c} {p}: {n}" for (c, p), n in sorted(cand.items())], ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--comune", action="append", help="solo questo comune (ripetibile)")
    p.add_argument("--force", action="store_true", help="rianalizza anche le righe già fatte")
    p.add_argument("--report", action="store_true", help="solo riepilogo")
    p.add_argument("--regione", action="append", help="solo questa regione (ripetibile), per esempio lombardia")
    p.add_argument("--limit", type=int, help="massimo di righe da analizzare")
    p.add_argument("--workers", type=int, default=8, help="siti in parallelo (1 richiesta/s per sito)")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    rows = read_rows()
    todo = [r for r in rows if r["stato"] not in PROTECTED and r["sito"]
            and (not args.regione or slugify(r["regione"]) in {slugify(x) for x in args.regione})
            and (not args.comune or r["comune"].lower() in {c.lower() for c in args.comune})
            and (args.force or not r["cms"])]
    if args.limit:
        todo = todo[:args.limit]
    if not args.report and todo:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
            fetcher = Fetcher(client, cache_dir=CACHE_DIR)

            def run(batch: list[dict]) -> None:
                with ThreadPoolExecutor(args.workers) as pool:
                    futures = {pool.submit(detect, fetcher, r["sito"]): r for r in batch}
                    for i, fut in enumerate(as_completed(futures), 1):
                        row = futures[fut]
                        try:
                            apply(row, fut.result())
                        except Exception as e:  # una riga difettosa non ferma le altre
                            apply(row, {"cms": "irraggiungibile", "note": f"auto: errore {type(e).__name__}"})
                        print(f"[{i}/{len(batch)}] {row['comune']:<28} {row['cms']:<14} {row['licenza']:<12} {row['stato']}", flush=True)
                        if i % 25 == 0:
                            write_rows(rows)

            run(todo)
            # una volta sola, a fine giro: i siti irraggiungibili si riprovano (guasti passeggeri, rate limit)
            retry = [r for r in todo if r["cms"] == "irraggiungibile"]
            if retry:
                print(f"\nSecondo tentativo su {len(retry)} siti irraggiungibili", flush=True)
                run(retry)
        write_rows(rows)
    print("\n" + report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
