"""Controllo anti-doppio-avvio dell'import giornaliero."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from ci_report import import_done_today  # noqa: E402

TODAY = "2026-10-31"


def run(id, title="Import eventi", day=TODAY, conclusion=None):
    return {"id": id, "display_title": title, "created_at": f"{day}T08:17:03Z", "conclusion": conclusion}


def done(runs, current=99, plan=lambda rid: True):
    return import_done_today(runs, TODAY, current, plan)


def test_nessun_run_oggi_si_parte():
    assert not done([])
    assert not done([run(1, day="2026-10-30", conclusion="success")])  # ieri


def test_run_di_oggi_in_corso_o_finito_blocca():
    assert done([run(1)])  # in corso
    assert done([run(1, conclusion="success")])
    assert done([run(1, conclusion="failure")])  # anche fallito: niente rilettura completa a ripetizione


def test_il_run_corrente_non_conta():
    assert not done([run(99)])


def test_dry_run_e_regione_singola_non_contano():
    assert not done([run(1, "Import eventi (dry-run)"), run(2, "Import eventi [lombardia]"), run(3, "Altro")])


def test_cancellato_o_saltato_non_blocca():
    assert not done([run(1, conclusion="cancelled")])
    assert not done([run(1, conclusion="success")], plan=lambda rid: False)  # ha saltato per il controllo: plan mai partito
    assert done([run(1, conclusion="success"), run(2)], plan=lambda rid: rid == 2)
