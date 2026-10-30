"""Supporto al workflow import-events.yml.

  python ci_report.py matrix                       # regioni con fonti attive e quote per job → GITHUB_OUTPUT
  python ci_report.py summary <cartella> [cleanup.json]   # riepilogo unico → stdout e GITHUB_STEP_SUMMARY
  python ci_report.py simulate [regioni.json]      # quote per giorno della settimana (scenario Italia)

Quote Spark giornaliere (50.000 letture, 20.000 scritture, 20.000 cancellazioni) divise tra i job della matrice.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from geo import slugify
from registry import read_rows

QUOTA = {"reads": 50_000, "writes": 20_000, "deletes": 20_000}
BUDGET = {"reads": 40_000, "writes": 15_000, "geocode": 3_000}  # con margine, vedi run.py


SKIPPED_SHARE = 0.05  # oltre questa quota di fonti saltate il job segnala un avviso
BIG_COMUNE = 50  # un comune che ieri aveva più di tanti eventi e oggi non risponde segnala sempre un avviso


RECONCILE_WEIGHT = 7  # una riconciliazione legge ~tutti gli eventi della regione: pesa come 7 giorni di import normale
TURNOVER = 0.07  # quota di eventi nuovi o modificati ogni giorno (stima, vedi README §10)
HORIZON_DAYS = 60


def reconcile_days(weights: dict[str, int]) -> dict[str, int]:
    """Giorno della settimana (0 = lunedì) in cui ogni regione si riconcilia con Firestore.

    LPT deterministico: le regioni più pesanti per prime, ciascuna nel giorno meno carico (a parità, il primo).
    Non dipende dall'ordine d'ingresso, quindi lo stesso input dà sempre la stessa assegnazione."""
    load = [0] * 7
    out: dict[str, int] = {}
    for region in sorted(weights, key=lambda r: (-weights[r], r)):
        day = min(range(7), key=lambda d: (load[d], d))
        load[day] += weights[region]
        out[region] = day
    return out


def matrix(rows: list[dict], only: str = "", weekday: int | None = None, force_reconcile: bool = False) -> dict:
    """Regioni da importare con il budget di letture per job.

    Il giorno di riconciliazione si assegna su tutte le regioni attive (anche con `only`), così non cambia
    quando si lancia una regione sola. Il budget di 40.000 letture si divide in proporzione al peso
    (fonti attive) × 7 per chi si riconcilia oggi: la somma non supera mai il budget."""
    weights: dict[str, int] = {}
    for r in rows:
        if r["stato"] == "attivo":
            weights[slugify(r["regione"])] = weights.get(slugify(r["regione"]), 0) + 1
    days = reconcile_days(weights)
    regions = [r for r in sorted(weights) if not only or r == slugify(only)]
    n = max(1, len(regions))
    flags = {r: force_reconcile or (weekday is not None and days[r] == weekday) for r in regions}
    shares = {r: weights[r] * (RECONCILE_WEIGHT if flags[r] else 1) for r in regions}
    total = sum(shares.values()) or 1
    include = [{"region": r, "reads": BUDGET["reads"] * shares[r] // total, "reconcile": flags[r]} for r in regions]
    # Scritture: quota in parti uguali, ma mai sotto un terzo del budget, altrimenti con 20 job (750 ciascuno) il primo
    # caricamento di una regione grande (Trentino-Alto Adige: ~1.900 eventi) supera il tetto e non scrive nulla.
    per_job = {k: v // n for k, v in BUDGET.items() if k != "reads"}
    per_job["writes"] = max(per_job["writes"], BUDGET["writes"] // 3)
    return {"regions": regions, "include": include, **per_job}


def simulate(regions: dict[str, dict]) -> dict:
    """Quote per giorno della settimana nello scenario dato.

    regions: slug → {"events": N, "sources": comuni attivi}. Modello: ogni giorno importState (1) + eventi manuali
    (1) + nuovi eventi in lettura; nel giorno assegnato la riconciliazione legge tutti gli eventi. Scritture:
    eventi cambiati + 2 importState + 1 coverage per regione. Cancellazioni: la pulizia elimina ~eventi/60 al
    giorno. Durata: 3 min + 0,15 min per fonte, regioni in parallelo su 4 job."""
    days = reconcile_days({r: v["sources"] for r, v in regions.items()})
    table = []
    for d in range(7):
        reads = writes = 0
        minutes = []
        for r, v in regions.items():
            changed = round(v["events"] * TURNOVER)
            reads += 2 + changed + (v["events"] if days[r] == d else 0)
            writes += changed + 3
            minutes.append(3 + 0.15 * v["sources"])
        deletes = round(sum(v["events"] for v in regions.values()) / HORIZON_DAYS)
        reads += deletes + 1  # la pulizia legge ciò che elimina
        makespan = max(max(minutes), sum(minutes) / 4) if minutes else 0
        table.append({"day": d, "reads": reads, "writes": writes, "deletes": deletes, "minutes": round(makespan),
                      "user_reads": QUOTA["reads"] - reads,
                      "worst": max(reads / QUOTA["reads"], writes / QUOTA["writes"], deletes / QUOTA["deletes"])})
    return {"days": table, "assignment": days}


DAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def simulate_text(sim: dict) -> str:
    lines = ["| giorno | letture | scritture | cancellazioni | durata job | letture per gli utenti | quota peggiore | riconciliano |",
             "|---|---|---|---|---|---|---|---|"]
    for t in sim["days"]:
        who = ", ".join(r for r, d in sorted(sim["assignment"].items()) if d == t["day"]) or "-"
        flag = " ⚠️" if t["worst"] > 0.8 else ""
        lines.append(f"| {DAYS[t['day']]} | {t['reads']} | {t['writes']} | {t['deletes']} | ~{t['minutes']} min | "
                     f"{t['user_reads']} | {t['worst']:.0%}{flag} | {who} |")
    return "\n".join(lines)


def skipped_report(stats: list[dict]) -> tuple[list[str], list[str]]:
    """(righe del riepilogo, avvisi ::warning) per le fonti che non hanno risposto nemmeno al secondo tentativo.

    Avviso se sono più del 5% delle fonti dell'import o se tra loro c'è un comune (o una fonte regionale) con più di 50 eventi
    ieri. Il job resta verde ma la pagina dell'esecuzione mostra l'avviso: l'import non fallisce, la copertura di ieri resta."""
    total = sum(s.get("sources", 0) for s in stats)
    skipped = sorted((x for s in stats for x in s.get("skipped_sources", [])), key=lambda x: (-x["before"], x["region"], x["city"]))
    recovered = sorted(c for s in stats for c in s.get("retried_ok", []))
    lines = []
    if recovered:
        lines += ["", f"Fonti recuperate al secondo tentativo: {len(recovered)} ({', '.join(recovered[:30])}{'…' if len(recovered) > 30 else ''})."]
    if not skipped:
        return lines, []
    share = len(skipped) / max(1, total)
    big = [x for x in skipped if x["before"] > BIG_COMUNE]
    lines += ["", f"### ⚠️ Fonti saltate: {len(skipped)} su {total} ({share:.0%})", "",
              "Non hanno risposto nemmeno al secondo tentativo: i loro eventi restano in Firestore e la copertura di ieri è stata mantenuta.", "",
              "| comune | regione | eventi ieri | errore |", "|---|---|---|---|"]
    lines += [f"| {x['city']} | {x['region']} | {x['before']} | {x['error'].replace('|', '/')} |" for x in skipped]
    warnings = []
    if share > SKIPPED_SHARE or big:
        why = [f"{len(skipped)} fonti su {total} ({share:.0%}) non hanno risposto"] if share > SKIPPED_SHARE else []
        if big:
            why.append("comuni con più di %d eventi: %s" % (BIG_COMUNE, ", ".join(f"{x['city']} ({x['before']})" for x in big[:10])))
        warnings.append("::warning title=Import: fonti saltate::" + "; ".join(why) + ". Elenco nel riepilogo dell'esecuzione.")
    return lines, warnings


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
    lines += skipped_report(stats)[0]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if argv[:1] == ["matrix"]:
        m = matrix(read_rows(), os.environ.get("ONLY", ""), datetime.now(ZoneInfo("Europe/Rome")).weekday(),
                   os.environ.get("RECONCILE") == "true")
        out = "\n".join(f"{k}={json.dumps(v) if k in ('regions', 'include') else v}" for k, v in m.items())
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
        for w in skipped_report(stats)[1]:
            print(w)  # annotazione GitHub: compare in cima alla pagina dell'esecuzione
        if path := os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(path, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        return 0
    if argv[:1] == ["simulate"]:
        if len(argv) > 1:
            data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        else:  # senza dati: fonti attive dei CSV, eventi = 4 per fonte (stima)
            data = {}
            for r in read_rows():
                if r["stato"] == "attivo":
                    v = data.setdefault(slugify(r["regione"]), {"events": 0, "sources": 0})
                    v["events"] += 4
                    v["sources"] += 1
        sys.stdout.reconfigure(encoding="utf-8")
        print(simulate_text(simulate(data)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
