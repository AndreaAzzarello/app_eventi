"""Comuni bilingui (Alto Adige, Valle d'Aosta): nome ufficiale italiano in city, alias in cityAlt, slug stabili."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import run  # noqa: E402
from geo import slugify  # noqa: E402

ROWS = [{"comune": "Bolzano", "comune_alt": "Bozen", "provincia": "BZ"},
        {"comune": "Aosta", "comune_alt": "Aoste", "provincia": "AO"},
        {"comune": "Modena", "comune_alt": "", "provincia": "MO"}]


@pytest.fixture(autouse=True)
def alt(monkeypatch):
    monkeypatch.setattr(run, "ALT", run.alt_index(ROWS))


@pytest.mark.parametrize("city,province,expected", [
    ("Bolzano - Bozen", "BZ", ("Bolzano", "bolzano", "Bozen")),
    ("Bozen", "BZ", ("Bolzano", "bolzano", "Bozen")),
    ("Bolzano", "BZ", ("Bolzano", "bolzano", "Bozen")),
    ("Aoste", "AO", ("Aosta", "aosta", "Aoste")),
    ("Aosta/Aoste", "AO", ("Aosta", "aosta", "Aoste")),
])
def test_nome_italiano_e_alias(city, province, expected):
    ev = {"city": city, "citySlug": slugify(city), "province": province}
    run.use_italian_name(ev)
    assert (ev["city"], ev["citySlug"], ev["cityAlt"]) == expected


def test_comuni_non_bilingui_restano_uguali():
    ev = {"city": "Modena", "citySlug": "modena", "province": "MO"}
    run.use_italian_name(ev)
    assert ev == {"city": "Modena", "citySlug": "modena", "province": "MO"}


def test_omonimo_in_un_altra_provincia_non_si_tocca():
    ev = {"city": "Bozen", "citySlug": "bozen", "province": "MO"}
    run.use_italian_name(ev)
    assert "cityAlt" not in ev


def test_frazione_uguale_al_comune_bilingue_si_toglie():
    ev = {"city": "Bolzano - Bozen", "citySlug": "bolzano-bozen", "province": "BZ", "locality": "Bozen"}
    run.use_italian_name(ev)
    assert "locality" not in ev


def test_copertura_con_alias():
    src = [SimpleNamespace(city="Bolzano", province="BZ"), SimpleNamespace(city="Modena", province="MO")]
    centers = {("Trentino-Alto Adige", "bolzano"): (46.5, 11.35), ("Trentino-Alto Adige", "modena"): (44.6, 10.9)}
    doc = run.coverage_doc("Trentino-Alto Adige", src, [], centers, 1)
    assert [(c["slug"], c.get("alt")) for c in doc["comuni"]] == [("bolzano", "Bozen"), ("modena", None)]


@pytest.mark.parametrize("region,expected", [
    ("Trentino-Alto Adige/Südtirol", "Trentino-Alto Adige"),
    ("Valle d'Aosta/Vallée d'Aoste", "Valle d'Aosta"),
    ("Lombardia", "Lombardia"),
])
def test_regione_con_nome_bilingue_diventa_il_nome_italiano(region, expected):
    """Nominatim scrive la regione in due lingue; lo slug della pagina regione è quello italiano."""
    ev = {"city": "Modena", "citySlug": "modena", "province": "MO", "region": region}
    run.use_italian_name(ev)
    assert ev["region"] == expected
