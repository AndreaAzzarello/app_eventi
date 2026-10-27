import json
import sys
from datetime import datetime, time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from mapping import ROME, category_from_title, dedupe_key, is_long_running, event_id, map_category, map_price, parse_hours, to_event  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "plone_events.json"
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=ROME)
SOURCE = {"city": "Modena"}


@pytest.fixture(scope="module")
def events():
    items = json.loads(FIXTURE.read_text(encoding="utf-8"))["items"]
    return {i["title"]: to_event(i, SOURCE, NOW) for i in items}


def local(ms):
    return datetime.fromtimestamp(ms / 1000, ROME).replace(tzinfo=None)


def test_evento_normale_con_coordinate_del_luogo(events):
    e = events["Nessun dubbio"]
    assert local(e["startTime"]) == datetime(2026, 10, 30, 21, 0)  # 20:00Z, ora solare
    assert local(e["endTime"]) == datetime(2026, 10, 30, 23, 0)
    assert e["priceType"] == "low"  # "Biglietti: 10€"
    assert e["venueName"] == 'Auditorium "Spira mirabilis"'
    assert (e["lat"], e["lng"]) == pytest.approx((44.5765, 10.8393), abs=1e-3)
    assert e["_geocode"]  # sempre compilato: serve se le coordinate della fonte risultano fuori provincia
    assert e["source"] == "scraper"
    assert e["id"] == event_id(e["sourceUrl"])


def test_bambini_e_gratis(events):
    e = events["Giochetto o scherzetto?"]
    assert e["tags"] == ["kids"]
    assert e["priceType"] == "free"


def test_ricorrente_prossima_occorrenza_con_orario_da_testo(events):
    e = events["Mercato settimanale del lunedì"]
    assert local(e["startTime"]) == datetime(2026, 10, 26, 8, 0)  # "dalle ore 8 alle 14"
    assert local(e["endTime"]) == datetime(2026, 10, 26, 14, 0)
    assert e["category"] == "market"
    assert e["lat"] is None and e["_geocode"][0].endswith("Modena")
    assert e["imageUrl"].startswith("https://www.comune.modena.it/")


def test_ricorrente_rispetta_exdate(events):
    # Sabati con EXDATE fino al 7/11: la prossima data valida è il 14/11.
    e = events["Delfini Book Party"]
    assert local(e["startTime"]) == datetime(2026, 11, 14, 8, 30)
    assert local(e["endTime"]) == datetime(2026, 11, 14, 12, 30)


def test_giornata_intera_in_corso(events):
    e = events["Fiere di Ottobre 2026"]
    assert local(e["startTime"]) == datetime(2026, 10, 1, 0, 0)
    assert local(e["endTime"]) == datetime(2026, 10, 31, 23, 59)
    assert e["_geocode"] == ["Centro storico, Sassuolo"]


def test_scarta_finiti_e_oltre_orizzonte():
    base = {"@id": "https://x/e", "title": "T"}
    assert to_event({**base, "start": "2026-10-01T10:00:00Z", "end": "2026-10-01T12:00:00Z"}, SOURCE, NOW) is None
    assert to_event({**base, "start": "2027-06-01T10:00:00Z", "end": "2027-06-01T12:00:00Z"}, SOURCE, NOW) is None
    assert to_event({**base, "title": "", "start": "2026-11-01T10:00:00Z"}, SOURCE, NOW) is None


@pytest.mark.parametrize("text,expected", [
    ("Ingresso libero", "free"),
    ("Gratuito, su prenotazione", "free"),
    ("Biglietti Ingresso 15€ (riduzioni 10€)", "low"),
    ("Intero 30 euro", "premium"),
    ("a pagamento", "low"),
    ("", "low"),
])
def test_prezzo(text, expected):
    assert map_price(text) == expected


@pytest.mark.parametrize("item,expected", [
    ({"tipologia_evento": {"token": "maifestazione_musicale"}, "title": "X"}, "music"),
    ({"tipologia_evento": {"token": "mostra"}, "title": "Pittura"}, "culture"),
    ({"tipologia_evento": {"token": "eventi_sociali"}, "title": "Sagra del tortellino"}, "food"),
    ({"tipologia_evento": None, "title": "Torneo di calcio"}, "sport"),
    ({"title": "Garanzia giovani"}, "other"),  # "gara" solo come parola intera
])
def test_categoria(item, expected):
    assert map_category(item) == expected


def test_orari_dal_testo():
    assert parse_hours("dalle ore 8.30 alle 12.30") == [time(8, 30), time(12, 30)]
    assert parse_hours("il lunedì dalle ore 8 alle 14") == [time(8), time(14)]
    assert parse_hours("vedi il programma") == []


def test_dedupe_key_ignora_maiuscole_e_punteggiatura():
    a = {"title": "Concerto: Jazz!", "citySlug": "modena", "startTime": 1_793_000_000_000}
    b = {"title": "concerto jazz", "citySlug": "modena", "startTime": 1_793_000_000_000 + 3_600_000}
    assert dedupe_key(a) == dedupe_key(b)


@pytest.mark.parametrize("title,expected", [
    ("Sagra della polenta", "food"), ("Concerto di Natale", "music"), ("Torneo di tennis", "sport"),
    ("Mercatino dell'antiquariato", "market"), ("Spettacolo teatrale in piazza", "culture"),
    ("Mostra fotografica", "culture"), ("Burattini per bambini", "kids"), ("Presentazione del libro", "culture"),
    ("Consiglio comunale", None),
])
def test_category_from_title_italian_keywords(title, expected):
    assert category_from_title(title) == expected


def test_durata_tetto_365_giorni_e_long_running(caplog):
    base = {"@id": "https://x/e", "title": "Mostra"}
    mostra = {**base, "start": "2026-10-01T10:00:00Z", "end": "2027-02-01T10:00:00Z"}  # 123 giorni: si importa
    assert to_event(mostra, SOURCE, NOW) is not None
    assurda = {**base, "start": "2026-10-01T10:00:00Z", "end": "2028-01-01T10:00:00Z"}  # oltre 365: scartata e loggata
    with caplog.at_level("WARNING", logger="importer"):
        assert to_event(assurda, SOURCE, NOW) is None
    assert "scartato: https://x/e" in caplog.text


def test_is_long_running_oltre_14_giorni():
    day = 86_400_000
    assert not is_long_running({"startTime": 0, "endTime": 14 * day})
    assert is_long_running({"startTime": 0, "endTime": 14 * day + 1})
