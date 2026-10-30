"""Controllo anti-doppio-avvio dell'import giornaliero: riconosce gli import completi senza guardare il titolo del run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from ci_report import import_done_today, is_full_import  # noqa: E402

TODAY = "2026-10-31"


def run(id, event="workflow_dispatch", day=TODAY, conclusion=None):
    # il titolo è volutamente quello vecchio: non deve contare
    return {"id": id, "event": event, "display_title": ".github/workflows/import-events.yml",
            "created_at": f"{day}T08:17:03Z", "conclusion": conclusion}


def job(name, conclusion="success"):
    return {"name": name, "conclusion": conclusion}


def full(dry="false", regione="", plan="success", cleanup="success"):
    return [job(f"guard (dry_run={dry}, regione={regione})"), job("plan", plan), job("import (lombardia, 100, false)"),
            job("import (veneto, 100, false)"), job("cleanup", cleanup)]


def done(runs, jobs, current=99):
    return import_done_today(runs, TODAY, current, lambda rid: jobs[rid])


def test_nessun_run_oggi_si_parte():
    assert not done([], {})
    assert not done([run(1, day="2026-10-30", conclusion="success")], {1: full()})  # ieri


def test_import_completo_di_oggi_blocca_in_ogni_stato():
    assert done([run(1)], {1: full(plan=None, cleanup=None)})  # in corso
    assert done([run(1, conclusion="success")], {1: full()})
    assert done([run(1, conclusion="failure")], {1: full()})  # fallito: niente rilettura completa a ripetizione
    assert done([run(1, "schedule")], {1: full()})


def test_il_run_corrente_non_conta():
    assert not done([run(99)], {99: full()})


def test_dry_run_e_regione_singola_non_contano():
    assert not done([run(1)], {1: full(dry="true")})
    assert not done([run(1)], {1: full(regione="lombardia")})


def test_altri_eventi_cancellati_e_saltati_non_contano():
    assert not done([run(1, "push")], {1: full()})
    assert not done([run(1, conclusion="cancelled")], {1: full()})
    assert not done([run(1, conclusion="success")], {1: full(plan="skipped", cleanup="skipped")})  # saltato dal guard


def test_run_vecchi_senza_nome_del_guard_si_deducono_dai_job():
    legacy = [job("plan"), job("import (marche, 649, false)"), job("import (veneto, 4080, false)"), job("cleanup")]
    assert is_full_import(run(1, conclusion="success"), legacy)  # come il run 41043640454 del 30/10
    assert not is_full_import(run(1), [job("plan"), job("import (veneto, 4080, false)"), job("cleanup")])  # una regione sola
    assert not is_full_import(run(1), [job("plan"), *legacy[1:3], job("cleanup", "skipped")])  # dry-run
