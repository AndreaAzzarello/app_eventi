"""Matrice per regione e riepilogo unico del workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from ci_report import matrix, summary  # noqa: E402


def row(regione, stato="attivo"):
    return {"regione": regione, "stato": stato}


def test_matrice_solo_regioni_con_fonti_attive_e_quote_divise():
    m = matrix([row("Emilia-Romagna"), row("Emilia-Romagna"), row("Lombardia"), row("Veneto", "candidato")])
    assert m == {"regions": ["emilia-romagna", "lombardia"], "reads": 20_000, "writes": 7_500, "geocode": 1_500}
    assert matrix([row("Lombardia"), row("Veneto")], only="Veneto")["regions"] == ["veneto"]
    assert matrix([])["regions"] == []


def test_riepilogo_unico_con_quote():
    stats = [{"region": "lombardia", "events": 100, "reads": 150, "writes": 10, "unchanged": 90, "hidden": 1,
              "sources": 5, "geocode": 7, "deferred": 0},
             {"region": "veneto", "events": 50, "reads": 60, "writes": 0, "unchanged": 50, "hidden": 0}]
    text = summary(stats, {"reads": 40, "deleted": 12, "due": 12})
    assert "| lombardia | 5 | 100 | 150 |  | 10 | 90 | 1 | 7 | 0 |" in text
    assert "| letture | 250 | 50000 | ok |" in text and "| cancellazioni | 12 | 20000 | ok |" in text
    assert "oltre il 75%" in summary([{"region": "x", "events": 1, "reads": 40_000, "writes": 0, "unchanged": 0, "hidden": 0}], None)
