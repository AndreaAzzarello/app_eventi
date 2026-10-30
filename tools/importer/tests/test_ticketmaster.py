"""Ticketmaster Discovery API: mappatura, comune del luogo, finestre di date, chiave mai nei messaggi, doppioni."""

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import run  # noqa: E402
from adapters import load_sources  # noqa: E402
from adapters import ticketmaster as tm  # noqa: E402
from adapters.ticketmaster import TicketmasterAdapter, find_comune  # noqa: E402

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)
RAW = json.loads((Path(__file__).parent / "fixtures" / "ticketmaster_events.json").read_text(encoding="utf-8"))
KEY = "chiave-segreta-di-prova"


def adapter(region: str) -> TicketmasterAdapter:
    return TicketmasterAdapter(f"ticketmaster-{region}", tm.BASE, "Ticketmaster", "", region)


def evs(region: str) -> dict[str, dict]:
    a = adapter(region)
    return {e["title"]: e for i in copy.deepcopy(RAW["_embedded"]["events"]) if (e := a._event(i, NOW, 60))}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    tm._CACHE.clear()
    monkeypatch.setattr(tm.time, "sleep", lambda s: None)
    monkeypatch.setenv("TICKETMASTER_API_KEY", KEY)


def test_fixture_senza_chiave():
    assert "apikey" not in json.dumps(RAW).lower()


def test_concerto_mappato():
    e = evs("Lombardia")["Artista Uno - Tour 2026"]
    assert e["category"] == "music" and e["priceType"] == "premium" and e["source"] == "scraper"
    assert e["ticketUrl"] == "https://www.ticketmaster.it/event/1" and e["sourceUrl"].startswith(tm.BASE)
    assert e["_place"] == {"city": "Assago", "citySlug": "assago", "province": "MI", "region": "Lombardia", "locality": ""}
    assert e["shortDescription"] == "Biglietti da 45.5 €. Apertura porte alle 19:00."
    assert e["address"] == "Via Di Vittorio 6, 20090 Assago" and e["venueName"] == "Unipol Forum"
    assert e["imageUrl"].endswith("img_16_9_1024.jpg")  # 16:9, non fallback, larghezza più vicina a 1024
    assert datetime.fromtimestamp(e["startTime"] / 1000, timezone.utc).hour == 20  # 21:00 a Roma
    assert e["lat"] == 45.4 and not e["approxLocation"] and e["_geocode"] == []


def test_categorie_e_prezzo():
    lomb, pie, ero, laz = evs("Lombardia"), evs("Piemonte"), evs("Emilia-Romagna"), evs("Lazio")
    assert pie["Derby di esempio"]["category"] == "sport" and pie["Derby di esempio"]["priceType"] == "low"
    assert ero["Il lago dei cigni"]["category"] == "culture" and ero["Il lago dei cigni"]["priceType"] == "low"
    fam = laz["Spettacolo per famiglie"]
    assert fam["category"] == "kids" and fam["priceType"] == "free" and fam["tags"] == ["kids"] and fam["shortDescription"] == ""
    assert lomb["Rassegna senza coordinate"]["priceType"] == "low"  # senza prezzo: mai "gratis"


def test_filtro_per_regione():
    assert set(evs("Piemonte")) == {"Derby di esempio", "Concerto a Samone"}
    assert evs("Veneto") == {}


def test_scarti():
    lomb = evs("Lombardia")
    assert "Parking Unipol Forum" not in lomb  # servizio, non evento
    assert "Data da definire" not in lomb and "Evento di luglio" not in evs("Lazio")  # data non fissata / oltre 60 giorni
    assert lomb["Concerto annullato"]["_excluded"] == "annullato"


def test_senza_coordinate_centro_del_comune():
    e = evs("Lombardia")["Rassegna senza coordinate"]
    assert e["approxLocation"] is True and (e["lat"], e["lng"]) == (45.467, 9.19)


def test_comune_dal_nome_dalla_sigla_e_dal_piu_vicino():
    assert find_comune("Samone", "TO", None, None)[5] == "samone-to"  # omonimo risolto dalla sigla
    assert find_comune("Samone", "", None, None) is None  # omonimo senza sigla né coordinate: non si indovina
    assert find_comune("Fiera Milano Rho", "MI", 45.53, 9.04)[0] == "Rho"  # non è un comune: il più vicino entro 15 km
    assert find_comune("Luogo ignoto", "", 45.0, 3.0) is None  # troppo lontano da tutto
    assert evs("Piemonte")["Concerto a Samone"]["_place"]["citySlug"] == "samone-to"


def pages(totals):
    """Client finto: totalElements dato da (inizio, fine) della finestra, un evento per pagina."""
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        p = dict(req.url.params)
        seen.append(p)
        ev = copy.deepcopy(RAW["_embedded"]["events"][0]) | {"id": f"{p['startDateTime']}-{p['page']}"}
        page = {"totalElements": totals(p["startDateTime"], p["endDateTime"]), "totalPages": 1}
        return httpx.Response(200, json={"page": page, "_embedded": {"events": [ev]}})
    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_finestre_di_sette_giorni_e_parametri():
    client, seen = pages(lambda a, b: 5)
    items = tm.fetch_italy(client, NOW, 60)
    assert len(seen) == 9 and len(items) == 9  # 60 giorni a finestre di 7: 9 richieste, una pagina ciascuna
    p = seen[0]
    assert p["countryCode"] == "IT" and p["size"] == "200" and p["apikey"] == KEY and p["sort"] == "date,asc"
    assert p["startDateTime"] == "2026-11-26T06:00:00Z"
    assert tm.fetch_italy(client, NOW, 60) is items and len(seen) == 9  # nazionale una sola volta per processo


def test_finestra_troppo_piena_si_divide():
    def span(a, b):
        return datetime.fromisoformat(b.replace("Z", "+00:00")) - datetime.fromisoformat(a.replace("Z", "+00:00"))

    client, seen = pages(lambda a, b: 1500 if span(a, b).days >= 6 else 3)
    tm.fetch_italy(client, NOW, 7)
    assert len(seen) == 3  # la finestra da 1.500 si divide in due da 3
    assert seen[1]["startDateTime"] == seen[0]["startDateTime"] and seen[1]["endDateTime"] < seen[0]["endDateTime"]


def test_errore_senza_chiave_e_ricordato():
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(401, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    for _ in range(2):  # due regioni: la seconda non rifà le richieste
        with pytest.raises(httpx.HTTPError) as e:
            list(adapter("Lombardia").events(client, NOW, 60))
        assert KEY not in str(e.value) and "apikey" not in str(e.value) and "401" in str(e.value)
    assert len(calls) == 1


def test_limite_chiamate(monkeypatch):
    monkeypatch.setattr(tm, "MAX_CALLS", 3)
    client, _ = pages(lambda a, b: 1)
    with pytest.raises(httpx.HTTPError, match="oltre 3 chiamate"):
        tm.fetch_italy(client, NOW, 60)


def test_manca_la_chiave(monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY")
    with pytest.raises(httpx.HTTPError, match="non impostata"):
        tm.fetch_italy(httpx.Client(), NOW, 60)


def test_load_sources_solo_con_chiave(monkeypatch):
    rows = [{"stato": "attivo", "cms": "plone", "comune": "Modena", "sito": "https://www.comune.modena.it", "provincia": "MO",
             "regione": "Emilia-Romagna", "url_eventi": ""}]
    assert "ticketmaster-emilia-romagna" in load_sources(rows)
    monkeypatch.delenv("TICKETMASTER_API_KEY")
    assert "ticketmaster-emilia-romagna" not in load_sources(rows)


class NoGeocoder:
    deferred: list = []
    requests = 0

    def reverse(self, *a, **k):
        return None

    def lookup(self, *a, **k):
        return None


@pytest.mark.parametrize("order", [["ticketmaster-x", "comune-x"], ["comune-x", "ticketmaster-x"]])
def test_doppione_comunale_vince_e_prende_il_link(order):
    mine = evs("Lombardia")["Artista Uno - Tour 2026"]
    comunal = copy.deepcopy(mine) | {"ticketUrl": "", "sourceUrl": "https://www.comune.assago.mi.it/e/1"}

    def src(name, ev, regional):
        return SimpleNamespace(name=name, base=f"https://{name}.example", city="Assago", province="MI", region="Lombardia",
                               viewbox=None, regional=regional, events=lambda c, n, h: iter([copy.deepcopy(ev)]))

    run.SOURCES.update({"ticketmaster-x": src("ticketmaster-x", mine, True), "comune-x": src("comune-x", comunal, False)})
    try:
        stats = {}
        out = run.collect(None, NoGeocoder(), order, NOW, 60, stats)
    finally:
        del run.SOURCES["ticketmaster-x"], run.SOURCES["comune-x"]
    assert len(out) == 1 and out[0]["sourceUrl"].startswith("https://www.comune.") and out[0]["ticketUrl"] == mine["ticketUrl"]
    assert out[0]["contentHash"] == run.content_hash(out[0])
    assert stats["ticketmaster-x"]["duplicates"] + stats["comune-x"]["duplicates"] == 1
    assert stats["comune-x"]["events"] == 1 and stats["ticketmaster-x"]["events"] == 0
