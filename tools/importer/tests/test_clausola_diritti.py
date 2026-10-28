"""Regola di licenza: "tutti i diritti riservati" è accettato solo se riferito esplicitamente a loghi, stemmi, marchi
o elementi grafici; "esclusiva proprietà" è sempre una restrizione. Casi reali in fixtures/html/note_legali_*.html."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from licenses import classify, restrictive_clause, sentences  # noqa: E402
from detect_cms import license_of  # noqa: E402

HTML = Path(__file__).parent / "fixtures" / "html"


def page(name: str) -> str:
    return (HTML / f"note_legali_{name}.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("comune", ["bolzano", "ala"])
def test_diritti_riservati_su_marchi_e_loghi_non_e_una_restrizione(comune):
    """Casi reali (Bolzano, Ala/Trentino): CC-BY 4.0 sui contenuti, diritti riservati solo su marchi, loghi, banner."""
    html = page(comune)
    assert "Tutti i diritti riservati" in html and not restrictive_clause(html)
    licenza = next(s for s in sentences(html) if "CC-BY" in s or "creativecommons" in s)
    assert license_of(licenza) == "CC-BY-4.0" and classify(licenza) == "contenuti"


def test_diritti_riservati_nel_piede_di_pagina_resta_una_restrizione():
    """Caso reale (Acqui Terme): "© Comune … Tutti i diritti riservati" senza riferimento a loghi o marchi."""
    assert restrictive_clause(page("acqui"))


@pytest.mark.parametrize("testo,atteso", [
    ("I loghi e gli stemmi sono di proprietà del Comune. Tutti i diritti riservati.", False),
    ("Tutti i diritti riservati sui marchi e sui loghi presenti nel sito.", False),
    ("Die Logos und das Wappen der Gemeinde sind Eigentum der Gemeinde. Alle Rechte vorbehalten.", False),
    ("Les logos et les armoiries de la commune sont sa propriété. Tous droits réservés.", False),
    ("Tutti i diritti riservati.", True),
    ("I testi del sito sono liberi. Il Comune è sempre al lavoro. Tutti i diritti riservati.", True),
    ("Alle Rechte vorbehalten.", True),
    ("Tous droits réservés.", True),
    # "esclusiva proprietà" resta una restrizione anche se la frase nomina i loghi
    ("I loghi sono di esclusiva proprietà del Comune.", True),
    ("I contenuti sono di esclusiva proprietà del Comune.", True),
])
def test_clausola_in_testo_sintetico(testo, atteso):
    assert restrictive_clause(f"<p>{testo}</p>") is atteso
