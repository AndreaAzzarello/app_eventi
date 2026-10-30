"""Dataset dei comuni per la ricerca del sito: unione ISTAT + Wikidata e controlli sul file generato (web/src/lib/data/comuni.json)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from build_comuni import CACHE, OUT, SLUG_DIR, build, outside_province, parse_istat, parse_wikidata, slug_chunks  # noqa: E402
from geo import slugify  # noqa: E402

ISTAT = ("Codice Regione;Codice Comune formato alfanumerico;Denominazione in italiano;Denominazione altra lingua;"
         "Denominazione Regione;Sigla automobilistica\n"
         "01;001235;Samone;;Piemonte;TO\n"
         "04;022165;Samone;;Trentino-Alto Adige/Südtirol;TN\n"
         "04;021008;Bolzano;Bozen;Trentino-Alto Adige/Südtirol;BZ\n"
         "02;007003;Aosta;;Valle d'Aosta/Vallée d'Aoste;AO\n"
         "20;090003;Alghero;;Sardegna;SS\n"
         "01;001999;Senza Coordinate;;Piemonte;TO\n")


def wd(code, lng, lat, pop=None, day="", fr="", it=""):
    b = {"code": {"value": code}, "coord": {"value": f"Point({lng} {lat})"}}
    if pop is not None:
        b["pop"] = {"value": str(pop)}
        if day:
            b["d"] = {"value": day}
    if fr:
        b["fr"] = {"value": fr}
    if it:
        b["it"] = {"value": it}
    return b


WIKI = {"results": {"bindings": [
    wd("001235", 7.84, 45.45, 1400, "2018-01-01T00:00:00Z"),
    wd("001235", 7.84, 45.45, 1491, "2024-01-01T00:00:00Z"),  # la più recente vince, in qualunque ordine
    wd("022165", 11.52, 46.08, 545),
    wd("021008", 11.35, 46.5, 106107),
    wd("007003", 7.32, 45.74, 33093, fr="Aoste"),
    wd("090099", 8.32, 40.56, 40000, it="Alghero"),  # codice diverso da ISTAT: si abbina per nome
]}}


def test_parse_istat_nomi_bilingui_e_regione():
    rows = {r["codice"]: r for r in parse_istat(ISTAT)}
    assert rows["021008"]["alt"] == "Bozen" and rows["021008"]["regione"] == "Trentino-Alto Adige"
    assert rows["007003"]["regione"] == "Valle d'Aosta"


def test_parse_wikidata_popolazione_piu_recente():
    assert parse_wikidata(WIKI)["001235"]["pop"] == 1491


def test_build_omonimi_aoste_nome_e_mancanti():
    data, missing = build(parse_istat(ISTAT), parse_wikidata(WIKI))
    by = {(c[0], c[2]): c for c in data["c"]}
    assert by[("Samone", "TO")][7] == "samone-to" and by[("Samone", "TN")][7] == "samone-tn"
    assert by[("Bolzano", "BZ")][1] == "Bozen" and by[("Bolzano", "BZ")][7] == ""
    assert by[("Aosta", "AO")][1] == "Aoste"
    assert ("Alghero", "SS") in by
    assert [m["nome"] for m in missing] == ["Senza Coordinate"]
    assert data["regioni"][by[("Samone", "TN")][3]] == "Trentino-Alto Adige"


def test_outside_province_segnala_coordinate_sbagliate():
    data, _ = build(parse_istat(ISTAT), parse_wikidata(WIKI))
    assert outside_province(data) == []
    bolzano = next(c for c in data["c"] if c[0] == "Bolzano")
    bolzano[4], bolzano[5] = 41.9, 12.5  # Roma
    assert outside_province(data) == ["Bolzano (BZ)"]


def test_slug_chunks_un_file_per_iniziale():
    data, _ = build(parse_istat(ISTAT), parse_wikidata(WIKI))
    chunks = slug_chunks(data)
    assert set(chunks) == {"s", "b", "a"}
    assert chunks["s"]["samone-to"] == ["Samone", 45.45, 7.84, "TO", "Piemonte"]
    assert chunks["b"]["bolzano"][4] == "Trentino-Alto Adige"
    assert sum(len(c) for c in chunks.values()) == len(data["c"])


# --- file generato (python build_comuni.py) ---

needs_file = pytest.mark.skipif(not OUT.exists(), reason="comuni.json non generato")


@pytest.fixture(scope="module")
def data():
    return json.loads(OUT.read_text(encoding="utf-8"))


@needs_file
def test_tutti_i_comuni_istat(data):
    istat = parse_istat((CACHE / "comuni-istat.csv").read_bytes().decode("cp1252")) if (CACHE / "comuni-istat.csv").exists() else None
    if istat is None:
        pytest.skip("elenco ISTAT non in cache")
    assert len(data["c"]) == len(istat) >= 7800


@needs_file
def test_slug_e_comuni_unici(data):
    keys = [(slugify(c[0]), c[2]) for c in data["c"]]
    assert len(set(keys)) == len(keys)
    slugs = [c[7] or slugify(c[0]) for c in data["c"]]
    assert len(set(slugs)) == len(slugs)


@needs_file
def test_coordinate_dentro_la_provincia(data):
    assert outside_province(data) == []


@needs_file
def test_bilingui_e_omonimi_noti(data):
    by = {(c[0], c[2]): c for c in data["c"]}
    assert by[("Bolzano", "BZ")][1] == "Bozen"
    assert by[("Aosta", "AO")][1] == "Aoste"
    assert by[("Merano", "BZ")][1] == "Meran"
    assert {by[("Samone", "TO")][7], by[("Samone", "TN")][7]} == {"samone-to", "samone-tn"}


@needs_file
def test_indice_del_server_coincide_con_il_file(data):
    files = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in SLUG_DIR.glob("*.json")}
    assert files == slug_chunks(data)
    assert max(p.stat().st_size for p in SLUG_DIR.glob("*.json")) < 150_000  # un file solo si carica nel Worker: pochi KB di JSON da leggere
