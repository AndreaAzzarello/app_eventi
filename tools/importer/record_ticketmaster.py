"""Registra una fixture reale della Discovery API: un campione ridotto di eventi veri, senza la chiave.

Uso:  $env:TICKETMASTER_API_KEY = "..."; python record_ticketmaster.py [--out tests/fixtures/ticketmaster_real.json]
Fa le stesse chiamate di un import (una trentina) e tiene: 2 eventi per ogni coppia segmento/genere, quelli che i filtri
escludono (abbonamenti, pass, giovanili, TV…) e qualche serie di date nella stessa sede, al massimo MAX_ITEMS in tutto.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

from adapters import ticketmaster as tm
from registry import USER_AGENT

OUT = Path(__file__).parent / "tests" / "fixtures" / "ticketmaster_real.json"
MAX_ITEMS = 80


def sample(items: list[dict]) -> list[dict]:
    picked: dict[str, dict] = {}
    seen = Counter()
    series = defaultdict(list)
    for item in items:
        c = tm._classes(item)
        title = item.get("name") or ""
        venue = next(iter((item.get("_embedded") or {}).get("venues") or []), {})
        series[(title, venue.get("id"))].append(item)
        if tm._not_event(item, title, tm._category(item, title)) or tm.TV.search(title):
            picked[item["id"]] = item
        if seen[(c["segment"], c["genre"])] < 2:
            seen[(c["segment"], c["genre"])] += 1
            picked[item["id"]] = item
    for group in sorted(series.values(), key=len, reverse=True)[:4]:
        if len(group) >= 3:
            picked.update({i["id"]: i for i in group[:12]})
    return list(picked.values())[:MAX_ITEMS]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    now = datetime.now(timezone.utc)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
        items = tm.fetch_italy(client, now, 60)
    chosen = sample(items)
    text = json.dumps({"_embedded": {"events": chosen}, "page": {"totalElements": len(chosen)},
                       "_nota": f"Risposta reale della Discovery API, campione di {len(chosen)} su {len(items)} eventi, registrata il {now:%d/%m/%Y}."},
                      ensure_ascii=False, indent=1)
    if "apikey" in text.lower():
        print("Nel campione compare 'apikey': non scrivo il file.", file=sys.stderr)
        return 1
    args.out.write_text(text, encoding="utf-8")
    print(f"{len(chosen)} eventi su {len(items)} salvati in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
