"""Supporto al workflow import-events.yml.

  python ci_report.py matrix                       # regioni con fonti attive e quote per job → GITHUB_OUTPUT
  python ci_report.py summary <cartella> [cleanup.json]   # riepilogo unico → stdout e GITHUB_STEP_SUMMARY

Quote Spark giornaliere (50.000 letture, 20.000 scritture, 20.000 cancellazioni) divise tra i job della matrice.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from geo import slugify
from registry import read_rows

QUOTA = {"reads": 50_000, "writes": 20_000, "deletes": 20_000}
BUDGET = {"reads": 40_000, "writes": 15_000, "geocode": 3_000}  # con margine, vedi run.py


def matrix(rows: list[dict], only: str = "") -> dict:
    regions = sorted({slugify(r["regione"]) for r in rows if r["stato"] == "attivo"})
    regions = [r for r in regions if not only or r == slugify(only)]
    n = max(1, len(regions))
    return {"regions": regions, **{k: v // n for k, v in BUDGET.items()}}


def summary(stats: list[dict], cleanup: dict | None) -> str:
    cleanup = cleanup or {}
    head = ["| regione | comuni | eventi | letture | confronto | scritture | invariati | nascosti | geocoding | rimandati |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for s in sorted(stats, key=lambda s: s["region"]):
        head.append(f"| {s['region']} | {s.get('sources', '')} | {s['events']} | {s['reads']} | {s.get('compare', '')} | {s['writes']} | "
                    f"{s['unchanged']} | {s['hidden']} | {s.get('geocode', 0)} | {s.get('deferred', 0)} |")
    total = {k: sum(s.get(k, 0) for s in stats) for k in ("events", "reads", "writes", "unchanged", "hidden")}
    reads, deletes = total["reads"] + cleanup.get("reads", 0), cleanup.get("deleted", 0)
    lines = ["## Import eventi", "", *head, "",
             f"**Totali**: {total['events']} eventi, {total['unchanged']} invariati, {total['hidden']} nascosti.", "",
             "| quota Spark | usata | limite | |", "|---|---|---|---|"]
    for name, used, key in (("letture", reads, "reads"), ("scritture", total["writes"], "writes"),
                            ("cancellazioni", deletes, "deletes")):
        lines.append(f"| {name} | {used} | {QUOTA[key]} | {'⚠️ oltre il 75%' if used > 0.75 * QUOTA[key] else 'ok'} |")
    if cleanup:
        lines += ["", f"Pulizia: {cleanup.get('deleted', 0)} documenti eliminati su {cleanup.get('due', 0)} da eliminare."]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if argv[:1] == ["matrix"]:
        m = matrix(read_rows(), os.environ.get("ONLY", ""))
        out = "\n".join(f"{k}={json.dumps(v) if k == 'regions' else v}" for k, v in m.items())
        print(out)
        if path := os.environ.get("GITHUB_OUTPUT"):
            with open(path, "a", encoding="utf-8") as f:
                f.write(out + "\n")
        return 0 if m["regions"] else 1
    if argv[:1] == ["summary"] and len(argv) >= 2:
        stats = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(argv[1]).rglob("stats-*.json"))]
        cleanup = json.loads(Path(argv[2]).read_text(encoding="utf-8")) if len(argv) > 2 and Path(argv[2]).exists() else None
        text = summary(stats, cleanup)
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
        if path := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
