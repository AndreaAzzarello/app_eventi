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
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from registry import PROTECTED, USER_AGENT, base_url, read_rows, write_rows

OPEN_LICENSE = re.compile(r"^(CC0|CC-BY(-SA)?(-\d\.\d)?|IODL(-\d\.\d)?)$")
PLONE_API = "/++api++/@search?portal_type=Event&b_size=1"


class Blocked(Exception):
    """robots.txt vieta l'URL."""


class RobotsUnknown(Exception):
    """robots.txt non raggiungibile (5xx o rete): per prudenza non si visita nulla."""


class Fetcher:
    def __init__(self, client: httpx.Client, min_interval: float = 1.0):
        self.client, self.min_interval = client, min_interval
        self._robots: dict[str, RobotFileParser | None] = {}
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def _wait(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            at = max(now, self._next.get(host, 0.0))
            self._next[host] = at + self.min_interval
        if at > now:
            time.sleep(at - now)

    def _robots_for(self, origin: str) -> RobotFileParser | None:
        with self._lock:
            if origin in self._robots:
                return self._robots[origin]
        rp: RobotFileParser | None = RobotFileParser()
        try:
            self._wait(urlsplit(origin).netloc)
            res = self.client.get(origin + "/robots.txt")
            if res.status_code < 400:
                rp.parse(res.text.splitlines())
            elif res.status_code < 500:
                rp.parse([])  # nessun robots.txt: tutto permesso (RFC 9309)
            else:
                rp = None
        except httpx.HTTPError:
            rp = None
        with self._lock:
            self._robots[origin] = rp
        return rp

    def get(self, url: str) -> httpx.Response:
        p = urlsplit(url)
        rp = self._robots_for(f"{p.scheme}://{p.netloc}")
        if rp is None:
            raise RobotsUnknown(url)
        if not rp.can_fetch(USER_AGENT, url):
            raise Blocked(url)
        self._wait(p.netloc)
        return self.client.get(url)


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
    return "altro"


def find_link(html: str, base: str, kind: str) -> str:
    """Prima pagina 'eventi' (kind='eventi') o 'note legali' (kind='legali') dello stesso sito."""
    host = urlsplit(base).netloc
    pats = {"eventi": (r"^(eventi|agenda|eventi e manifestazioni)$", r"/(eventi|agenda)(/|$)"),
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
    if m := re.search(r"creativecommons\.org/licenses/by-(nc|nd)[a-z-]*/(\d\.\d)|cc[\s-]*by[\s-]*(nc|nd)", t):
        return "CC-BY-NC/ND" + ver(m.group(2))  # restrittiva
    if m := re.search(r"creativecommons\.org/licenses/by-sa/(\d\.\d)|cc[\s-]*by[\s-]*sa[\s-]*(\d\.\d)?", t):
        return "CC-BY-SA" + ver(m.group(1) or m.group(2))
    if m := re.search(r"creativecommons\.org/licenses/by/(\d\.\d)|cc[\s-]*by[\s-]*(\d\.\d)", t):
        return "CC-BY" + ver(m.group(1) or m.group(2))
    if re.search(r"\bcc0\b|creative commons zero|publicdomain/zero", t):
        return "CC0"
    if re.search(r"\biodl\b|italian open data license", t):
        return "IODL"
    if "tutti i diritti riservati" in t or "all rights reserved" in t:
        return "riservata"
    return "non trovata"


def is_open(lic: str) -> bool:
    return bool(OPEN_LICENSE.match(lic))


def _text(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def detect(f: Fetcher, sito: str) -> dict:
    """Campi rilevati per un sito: cms, url_eventi, licenza, robots_ok, stato, note."""
    out = {"cms": "", "url_eventi": "", "licenza": "", "robots_ok": "", "stato": "da_verificare"}
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
    if blocked or lic.startswith("CC-BY-NC") or lic == "riservata":
        out["stato"] = "escluso"
    elif cms in ("plone", "wordpress-dci") and out["robots_ok"] == "si" and is_open(lic) and (api_ok or cms != "plone"):
        out["stato"] = "candidato"
        if cms == "wordpress-dci":
            notes.append("adapter WordPress da scrivere")
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
    p.add_argument("--limit", type=int, help="massimo di righe da analizzare")
    p.add_argument("--workers", type=int, default=8, help="siti in parallelo (1 richiesta/s per sito)")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    rows = read_rows()
    todo = [r for r in rows if r["stato"] not in PROTECTED and r["sito"]
            and (not args.comune or r["comune"].lower() in {c.lower() for c in args.comune})
            and (args.force or not r["cms"])]
    if args.limit:
        todo = todo[:args.limit]
    if not args.report and todo:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
            fetcher = Fetcher(client)
            with ThreadPoolExecutor(args.workers) as pool:
                futures = {pool.submit(detect, fetcher, r["sito"]): r for r in todo}
                for i, fut in enumerate(as_completed(futures), 1):
                    row = futures[fut]
                    try:
                        apply(row, fut.result())
                    except Exception as e:  # una riga difettosa non ferma le altre
                        apply(row, {"cms": "irraggiungibile", "note": f"auto: errore {type(e).__name__}"})
                    print(f"[{i}/{len(todo)}] {row['comune']:<28} {row['cms']:<14} {row['licenza']:<12} {row['stato']}", flush=True)
                    if i % 25 == 0:
                        write_rows(rows)
        write_rows(rows)
    print("\n" + report(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
