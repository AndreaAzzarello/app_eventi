"""Filtro anti-avvisi: esclude sedute, avvisi, riepiloghi e titoli generici; non tocca gli eventi veri."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
from adapters.design_comuni_html import DesignComuniHtmlAdapter  # noqa: E402
from fake_firestore import FakeFirestore  # noqa: E402
from mapping import ROME, content_hash  # noqa: E402
from relevance import exclusion_reason  # noqa: E402
from run import excluded_report, plan_writes  # noqa: E402

ESCLUSI = [
    ("Seduta del Consiglio comunale del 12 novembre", "seduta di consiglio/giunta"),
    ("Convocazione Giunta comunale", "seduta di consiglio/giunta"),
    ("Consiglio comunale", "seduta di consiglio/giunta"),
    ("Commissione consiliare cultura", "seduta di consiglio/giunta"),
    ("Calendario raccolta rifiuti 2026", "avviso"),
    ("Attenzione alle truffe agli anziani", "avviso"),
    ("Allerta meteo rossa", "avviso"),
    ("Peste suina africana: misure in vigore", "avviso"),
    ("Bando per i contributi alle associazioni", "avviso"),
    ("Sicurezza stradale: nuove limitazioni", "avviso"),
    ("Video: messaggio del sindaco", "video"),
    ("Tutti gli eventi", "pagina riassuntiva"),
    ("Eventi 2026", "pagina riassuntiva"),
    ("Programma eventi estate", "pagina riassuntiva"),
    ("Calendario eventi di novembre", "pagina riassuntiva"),
    ("Evento culturale", "titolo generico"),
    ("Mostra", "titolo generico"),
    ("  Evento  ", "titolo generico"),
]

TENUTI = [
    "Concerto per il 4 novembre",
    "Cerimonia del 4 novembre",
    "Mostra fotografica sul Novecento",
    "Evento culturale in biblioteca: Leggere ad alta voce",
    "Incontro contro le truffe agli anziani",
    "Laboratorio di riciclo dei rifiuti per bambini",
    "Presentazione del bando per il servizio civile",
    "Band emergenti in piazza",
    "Consigli di lettura per l'autunno",
    "Eventi di Natale in centro",
    "Estate in musica al parco",
    "Sagra della castagna",
    "Esercitazione di protezione civile aperta al pubblico",
    "Spettacolo di burattini",
    "Mostra del libro",
]


@pytest.mark.parametrize("title,reason", ESCLUSI)
def test_esclusi(title, reason):
    assert exclusion_reason(title) == reason


@pytest.mark.parametrize("title", TENUTI)
def test_eventi_veri_restano(title):
    assert exclusion_reason(title) is None


def pagina(links: int, data: str) -> str:
    cards = "".join(f'<a href="/eventi/altro-{i}">Evento {i}</a>' for i in range(links))
    return f"<html><body><main><h1>Eventi autunno</h1><p>{data}</p>{cards}</main></body></html>"


def test_pagina_riassuntiva_molti_link_e_data_dal_testo():
    a = DesignComuniHtmlAdapter("x", "https://x.it", "X", "BO", "Emilia-Romagna")
    now = datetime(2026, 11, 1, tzinfo=ROME)
    url = "https://x.it/eventi/programma-autunno"
    riepilogo = a.event_from_page(pagina(8, "Dal 5 novembre al 20 dicembre 2026"), url, now, 90)
    assert riepilogo["_excluded"] == "pagina riassuntiva"
    # stessi link ma pochi: un evento con "leggi anche" resta
    assert "_excluded" not in a.event_from_page(pagina(2, "Dal 5 novembre al 20 dicembre 2026"), url, now, 90)


def test_esclusi_gia_importati_diventano_removed_subito():
    now_ms = 1_000_000_000_000
    ok = {"www.comune.test.it"}
    doc = lambda i, **k: {"source": "scraper", "sourceUrl": f"https://www.comune.test.it/e/{i}",  # noqa: E731
                          "startTime": now_ms + 1000, "endTime": now_ms + 2000} | k
    existing = {"a": doc("a"), "b": doc("b", removedAt=5), "c": doc("c", source="manual")}
    plan = plan_writes([], existing, ok, now_ms, 86_400_000, excluded={"a", "b", "c", "nuovo"})
    assert plan["stale"] == {"a": {"removedAt": now_ms}}  # b già nascosto, c manuale, "nuovo" non esiste


def test_report_per_regione():
    ex = [{"id": str(i), "title": f"Seduta {i}", "reason": "seduta di consiglio/giunta", "source": "x",
           "region": "veneto" if i % 2 else "toscana"} for i in range(30)]
    text = excluded_report(ex)
    assert "veneto: 15" in text and "toscana: 15" in text and text.count("\n  - ") == 20


def test_errore_imprevisto_in_una_fonte_non_ferma_le_altre(monkeypatch, tmp_path):
    import httpx
    import run
    from types import SimpleNamespace

    class Rotta:
        def events(self, *a):
            raise ValueError("pagina anomala")

    class Vuota:
        def events(self, *a):
            return []

    monkeypatch.setattr(run, "SOURCES", {"rotta": Rotta(), "vuota": Vuota()})
    stats: dict = {}
    run.collect(httpx.Client(), SimpleNamespace(), ["rotta", "vuota"], datetime(2026, 11, 1, tzinfo=ROME), 60, stats)
    assert stats["rotta"]["error"] == "ValueError: pagina anomala" and stats["vuota"]["error"] is None
