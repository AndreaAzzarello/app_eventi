"""Qualità dei dati: coordinate dentro la provincia, fallback sul comune, deduplica, pulizia indirizzi."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).parents[1]))
from geo import PROVINCES, enrich  # noqa: E402
from geocode import Geocoder  # noqa: E402
from mapping import clean_street, dedupe_key, geocode_queries  # noqa: E402
from run import locate  # noqa: E402

SASSUOLO = SimpleNamespace(city="Sassuolo", province="MO", viewbox=PROVINCES["MO"][1])
BOX = PROVINCES["MO"][1]


def geocoder(tmp_path, answers: dict):
    """Nominatim finto: risponde per sottostringa della query e registra le richieste."""
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        q = req.url.params["q"]
        seen.append(dict(req.url.params))
        for needle, (lat, lng) in answers.items():
            if q == needle[1:] if needle.startswith("=") else needle in q:
                return httpx.Response(200, json=[{"lat": str(lat), "lon": str(lng)}])
        return httpx.Response(200, json=[])

    g = Geocoder(httpx.Client(transport=httpx.MockTransport(handler)), tmp_path / "c.json")
    g._last = float("-inf")  # niente attesa di 1 s nei test
    return g, seen


def ev(**kw):
    return {"lat": None, "lng": None, "approxLocation": False, "sourceUrl": "https://x/e",
            "_geocode": [], **kw}


def test_palazzo_ducale_non_finisce_in_umbria(tmp_path):
    # Caso reale: la fonte dà 42.83333, 12.83333 (Campello sul Clitunno).
    g, seen = geocoder(tmp_path, {"Palazzo Ducale": (44.5340, 10.7841)})
    e = ev(lat=42.83333, lng=12.83333, _geocode=["Palazzo Ducale, Sassuolo"])
    locate(e, SASSUOLO, g)
    assert (e["lat"], e["lng"]) == (44.5340, 10.7841) and not e["approxLocation"]
    assert seen[0]["q"] == "Palazzo Ducale, Sassuolo, Modena"
    assert seen[0]["viewbox"] == BOX and seen[0]["bounded"] == "1"


def test_valore_condiviso_non_finisce_a_varsi(tmp_path):
    # Caso reale: coordinate di Varsi (PR) per una sala di Sassuolo.
    g, _ = geocoder(tmp_path, {"Biasin": (44.5365, 10.7845)})
    e = ev(lat=44.6466534, lng=9.8315683, _geocode=["Sala Gian Paolo Biasin, Sassuolo"])
    locate(e, SASSUOLO, g)
    assert e["lng"] > 10.4 and not e["approxLocation"]


def test_coordinate_valide_della_fonte_restano(tmp_path):
    g, seen = geocoder(tmp_path, {})
    e = ev(lat=44.53, lng=10.78, _geocode=["Via Rocca 20, Sassuolo"])
    locate(e, SASSUOLO, g)
    assert (e["lat"], e["lng"]) == (44.53, 10.78) and seen == []


def test_luogo_introvabile_usa_il_centro_del_comune(tmp_path, caplog):
    g, _ = geocoder(tmp_path, {"=Sassuolo, Modena": (44.5447, 10.7849)})
    e = ev(_geocode=["Sedi strane, Sassuolo"])
    locate(e, SASSUOLO, g)
    assert (e["lat"], e["lng"]) == (44.5447, 10.7849) and e["approxLocation"] is True


def test_risultato_fuori_provincia_scartato_anche_dalla_cache(tmp_path):
    g, _ = geocoder(tmp_path, {})
    g._cache["palazzo ducale, sassuolo, modena"] = [42.83333, 12.83333]
    assert g.lookup("Palazzo Ducale, Sassuolo, Modena", BOX) is None


def test_pulizia_cache(tmp_path):
    g, _ = geocoder(tmp_path, {})
    g._cache.update({"a, sassuolo, modena": [44.5, 10.7], "b, sassuolo, modena": [42.8, 12.8],
                     "c, sassuolo, modena": None, "rev:44.500,10.700": {"city": "X"}})
    assert g.clean({n.lower(): b for n, b in PROVINCES.values()}) == 2
    assert set(g._cache) == {"a, sassuolo, modena", "rev:44.500,10.700"}


def test_deduplica_titolo_normalizzato():
    base = {"startTime": 1793000000000, "city": "Sassuolo", "citySlug": "sassuolo", "venueName": "x"}
    a = {**base, "title": "Generare valore condiviso"}
    b = {**base, "title": "Generare  Valore Condiviso!", "venueName": "Sala Biasin"}
    assert dedupe_key(a) == dedupe_key(b)
    assert dedupe_key(a) != dedupe_key({**b, "citySlug": "modena"})
    assert dedupe_key(a) == dedupe_key({**a, "title": "GENERARE VALORE CONDIVISO"})


def test_indirizzi_da_ripulire():
    assert clean_street("sedi diverse") == "" and clean_street("vedi nel programma") == ""
    assert clean_street("ritrovo presso la biglietteria della Torre, via Lanfranco") == "via Lanfranco"
    assert clean_street("Ingresso da viale Berengario") == "viale Berengario"
    assert clean_street("Largo Porta Sant'Agostino, 337") == "Largo Porta Sant'Agostino, 337"
    assert geocode_queries("sedi varie", "Sedi diverse", "Modena") == []
    assert geocode_queries("Largo X, 337", "Museo Civico, Palazzo", "Modena") == [
        "Largo X, 337, Modena", "Largo X, Modena", "Museo Civico, Modena"]
