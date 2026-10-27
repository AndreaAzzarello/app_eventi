"""Regola di attivazione automatica: una condizione per test, più le righe protette."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from activate import check, judge, note_with_reason, select  # noqa: E402
from registry import COLUMNS  # noqa: E402

NOW = 1_800_000_000_000
BOX = "10.4,45.0,11.4,44.1"
OK_ROW = {"regione": "Lombardia", "comune": "Lecco", "cms": "plone", "robots_ok": "si", "licenza": "CC-BY-4.0",
          "url_eventi": "", "note": "licenza[attivare]: https://x.it/note-legali — «CC-BY 4.0»", "stato": "candidato"}


def row(**kw):
    return {c: "" for c in COLUMNS} | OK_ROW | kw


def test_tutto_a_posto():
    assert check(row()) is None
    assert check(row(cms="design_comuni_html", url_eventi="https://x.it/eventi")) is None
    assert check(row(licenza="CC0")) is None


def test_a_adapter_disponibile():
    assert "adapter" in check(row(cms="altro"))
    assert "adapter" in check(row(cms=""))
    assert "pagina eventi" in check(row(cms="design_comuni_html"))


@pytest.mark.parametrize("lic", ["CC-BY-SA-4.0", "CC-BY-NC-4.0", "CC-BY-ND", "CC-BY-NC/ND", "IODL", "riservata",
                                 "non-chiara", "non trovata", "solo-software", ""])
def test_b_licenza_non_aperta(lic):
    assert "licenza" in check(row(licenza=lic))


def test_b_note_legali_non_verificate_o_con_clausola():
    assert "non verificata" in check(row(note="auto: sito"))
    assert "restrittiva" in check(row(note="licenza[attivare] conflitto: x"))
    assert "controllare" in check(row(note="licenza[verificare]: x"))


def test_c_robots():
    assert "robots" in check(row(robots_ok="no"))
    assert "robots" in check(row(robots_ok=""))
    assert "robots" in check(row(note="licenza[escludere]: robots vieta"))


def test_d_dry_run():
    ev = {"title": "Sagra", "startTime": NOW + 1, "endTime": NOW + 2, "lat": 44.6, "lng": 10.9}
    assert judge([ev], BOX, NOW, None) is None
    assert "nessun evento" in judge([], BOX, NOW, None)
    assert "nessun evento" in judge([ev | {"endTime": NOW - 1, "startTime": NOW - 2}], BOX, NOW, None)  # passato
    assert "nessun evento" in judge([ev | {"title": ""}], BOX, NOW, None)
    assert "fuori provincia" in judge([ev | {"lat": 50.0}], BOX, NOW, None)
    no_coords = ev | {"lat": None, "lng": None}
    assert judge([no_coords], BOX, NOW, (44.6, 10.9)) is None  # vale il centro del comune
    assert "fuori provincia" in judge([no_coords], BOX, NOW, None)


def test_righe_protette_non_si_toccano():
    rows = [row(stato=s, comune=s) for s in ("manuale", "escluso", "attivo", "candidato", "da_verificare")]
    rows.append(row(stato="candidato", regione="Veneto", comune="altra"))
    assert [r["comune"] for r in select(rows, {"lombardia"})] == ["candidato", "da_verificare"]


def test_motivo_nelle_note_e_idempotente():
    r = row(note="licenza[attivare]: x")
    n = note_with_reason(r, "dry-run: nessun evento futuro valido")
    assert n.startswith("attivazione: dry-run: nessun evento futuro valido | licenza[attivare]")
    assert note_with_reason(r | {"note": n}, "altro motivo") == "attivazione: altro motivo | licenza[attivare]: x"
    assert note_with_reason(r | {"note": n}, None) == "licenza[attivare]: x"
