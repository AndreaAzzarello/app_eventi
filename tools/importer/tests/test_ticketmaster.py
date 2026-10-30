"""Ticketmaster Discovery API: mappatura, comune del luogo, finestre di date, chiave mai nei messaggi, doppioni."""

import copy
import io
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import logsafe  # noqa: E402
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
    tm._COMUNE.clear()
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
    assert pie["Derby di esempio"]["category"] == "sport" and pie["Derby di esempio"]["priceType"] == "premium"  # 20-90 €: come gli altri adapter, vale il massimo
    assert ero["Il lago dei cigni"]["category"] == "culture" and ero["Il lago dei cigni"]["priceType"] == "unknown"
    fam = laz["Spettacolo per famiglie"]
    assert fam["category"] == "kids" and fam["priceType"] == "free" and fam["tags"] == ["kids"] and fam["shortDescription"] == ""
    assert lomb["Rassegna senza coordinate"]["priceType"] == "unknown"  # senza priceRanges: prezzo sul sito del venditore, mai "low" di default


def test_filtro_per_regione():
    assert set(evs("Piemonte")) == {"Derby di esempio", "Concerto a Samone"}
    assert evs("Veneto") == {}


def test_scarti():
    lomb = evs("Lombardia")
    assert lomb["Parking Unipol Forum"]["_excluded"] == "parcheggio o upgrade"  # servizio, non evento
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


def make(title: str, day: str = "2026-12-12", segment: str = "Music", genre: str = "Pop", city: str = "Assago", **over) -> dict:
    """Evento sintetico (come quelli della fixture) con titolo, giorno e classificazione a scelta."""
    item = copy.deepcopy(RAW["_embedded"]["events"][0])
    item.pop("priceRanges", None), item.pop("info", None)
    item.update(id=f"X-{title}-{day}", name=title, url=f"https://www.ticketmaster.it/e/{title}-{day}")
    item["dates"]["start"] = {"localDate": day, "localTime": "21:00:00", "dateTime": f"{day}T20:00:00Z"}
    item["classifications"] = [{"primary": True, "segment": {"name": segment}, "genre": {"name": genre}, "subGenre": {"name": "Altro"}}]
    item["_embedded"]["venues"][0]["city"] = {"name": city}
    return item | over


def convert(*items, region="Lombardia") -> list[dict]:
    a = adapter(region)
    return list(tm.merge_daily([e for i in items if (e := a._event(i, NOW, 60))]))


@pytest.mark.parametrize("title,reason", [
    ("Abbonamento Stagione 2026/27", "abbonamento o pass"),
    ("Festival Season Pass", "abbonamento o pass"),
    ("Daily Pass - Sabato", "abbonamento o pass"),
    ("2 Days Pass", "abbonamento o pass"),
    ("3-Days Ticket", "abbonamento o pass"),
    ("Pass 2 giorni", "abbonamento o pass"),
    ("Pre-Show Experience", "pre-show"),
    ("Programma Gare Sabato", "programma gare"),
    ("Parcheggio Stadio", "parcheggio o upgrade"),
    ("VIP Upgrade", "parcheggio o upgrade"),
])
def test_biglietti_che_non_sono_eventi(title, reason):
    assert convert(make(title))[0]["_excluded"] == reason


def test_classificazione_e_tipo_del_record_escludono():
    assert convert(make("Festival 2026", segment="Miscellaneous", genre="Undefined",
                        classifications=[{"primary": True, "segment": {"name": "Miscellaneous"}, "type": {"name": "Season Tickets"}}]))[0]["_excluded"] == "prodotto non evento"
    assert convert(make("Festival 2026", type="parking"))[0]["_excluded"] == "prodotto non evento"
    assert convert(make("Festival 2026", test=True))[0]["_excluded"] == "prodotto non evento"
    assert "_excluded" not in convert(make("Passaggio a nord"))[0]  # "pass" dentro un'altra parola non conta


@pytest.mark.parametrize("title", ["Under 15 Giovanili", "Torneo U16", "Juniores Nazionale", "Attività di base", "Triangolari esordienti"])
def test_sport_giovanile_escluso_solo_per_lo_sport(title):
    assert convert(make(title, segment="Sports", genre="Football"))[0]["_excluded"] == "sport giovanile"
    assert "_excluded" not in convert(make(title, segment="Arts & Theatre", genre="Theatre"))[0]


def test_categorie_da_classificazione():
    cat = lambda **k: convert(make("Serata", **k))[0]["category"]  # noqa: E731
    assert cat(segment="Music", genre="Classical") == "music"
    assert cat(segment="Arts & Theatre", genre="Classical") == "music"  # concerto di classica sotto Arti e teatro
    assert cat(segment="Arts & Theatre", genre="Theatre") == "culture"
    assert cat(segment="Sports", genre="Basketball") == "sport"
    assert cat(segment="Music", genre="Pop") == "music"
    assert convert(make("Registrazione TV Amici", segment="Music"))[0]["category"] == "other"
    assert convert(make("Talk show dal vivo", segment="Music"))[0]["category"] == "other"


def test_prezzo_vuoto_o_fascia_corretta():
    price = lambda *ranges: convert(make("Serata", priceRanges=list(ranges)))[0]["priceType"]  # noqa: E731
    eur = lambda lo, hi: {"currency": "EUR", "min": lo, "max": hi}  # noqa: E731
    assert convert(make("Serata"))[0]["priceType"] == "unknown"  # nessuna fascia: mai "low"
    assert price() == "unknown" and price({"currency": "USD", "min": 10, "max": 20}) == "unknown"
    assert price(eur(0, 0)) == "free" and price(eur(10, 20)) == "low" and price(eur(10, 25)) == "premium"
    assert price(eur(15, 20), eur(30, 80)) == "premium"  # più fasce: vale il massimo


def test_biglietti_giornalieri_uniti_in_un_evento_lungo():
    days = [f"2026-12-{d:02d}" for d in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11)]
    mostra = [make("MARTIN PARR", d, segment="Arts & Theatre", genre="Fine Art", priceRanges=[{"currency": "EUR", "min": 12, "max": 12}]) for d in days]
    (ev,) = convert(*mostra)
    assert ev["longRunning"] is True and ev["priceType"] == "low" and ev["sourceUrl"].startswith(f"{tm.BASE}/discovery/v2/series/")
    assert datetime.fromtimestamp(ev["startTime"] / 1000, timezone.utc).day == 1 and datetime.fromtimestamp(ev["endTime"] / 1000, timezone.utc).day == 12 - 1
    assert convert(*mostra[2:])[0]["id"] == ev["id"]  # l'id non dipende dal primo giorno ancora in vendita
    assert convert(*mostra[:2])[0].get("longRunning") is None and len(convert(*mostra[:2])) == 2  # due date non fanno una serie


def test_residency_resta_in_date_separate():
    residency = [make("Mengoni Live", f"2026-12-{d:02d}", priceRanges=[{"currency": "EUR", "min": 50, "max": 90}]) for d in (3, 4, 6, 9, 10, 13, 14, 17)]
    out = convert(*residency)
    assert len(out) == 8 and not any(e.get("longRunning") for e in out)  # musica: servono 10 date all'80%


def test_serie_di_un_altro_luogo_o_titolo_non_si_mescola():
    a = [make("MARTIN PARR", f"2026-12-{d:02d}", segment="Arts & Theatre", genre="Fine Art") for d in (1, 2, 3, 4, 5, 6)]
    b = [make("ALTRA MOSTRA", f"2026-12-{d:02d}", segment="Arts & Theatre", genre="Fine Art") for d in (1, 2)]
    out = convert(*a, *b)
    assert len(out) == 3 and sum(1 for e in out if e.get("longRunning")) == 1


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


REAL = Path(__file__).parent / "fixtures" / "ticketmaster_real.json"


@pytest.mark.skipif(not REAL.exists(), reason="fixture reale non ancora registrata (record_ticketmaster.py)")
def test_fixture_reale_tutte_le_regioni():
    """Su risposte vere: nessun errore, campi validi, id unici, nessuna chiave."""
    text = REAL.read_text(encoding="utf-8")
    assert "apikey" not in text.lower()
    items = json.loads(text)["_embedded"]["events"]
    regions = sorted({r for r in tm._comuni()[0] for r in [r[2]]})
    out = [e for r in regions for e in convert(*copy.deepcopy(items), region=r)]
    assert out and len({e["id"] for e in out}) == len(out)
    for e in out:
        assert e["category"] in {"music", "food", "sport", "culture", "kids", "market", "other"} and e["priceType"] in {"free", "low", "premium", "unknown"}
        assert e["ticketUrl"].startswith("https://") and e["title"] and e["endTime"] >= e["startTime"] and e["lat"] and e["lng"]


# --- la chiave non esce mai ---------------------------------------------------------------------------------------

def _run_leaky(handler, status=200):
    """Esegue l'adapter con httpx a INFO (come faceva record_ticketmaster.py) e raccoglie ciò che esce da `handler`."""
    root, httpx_log = logging.getLogger(), logging.getLogger("httpx")
    old = (root.level, httpx_log.level)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    httpx_log.setLevel(logging.INFO)
    errors = []
    try:
        def respond(req):
            return httpx.Response(status, json=RAW if status == 200 else {})

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            try:
                list(adapter("Lombardia").events(client, NOW, 8))
            except Exception as e:  # noqa: BLE001
                errors.append(e)
    finally:
        root.removeHandler(handler)
        root.setLevel(old[0])
        httpx_log.setLevel(old[1])
    return errors


def test_senza_filtro_httpx_stampa_la_chiave():
    """Controllo del test: il log INFO di httpx contiene davvero l'URL con la chiave (è il bug segnalato)."""
    out = io.StringIO()
    h = logging.StreamHandler(out)
    _run_leaky(h)
    assert f"apikey={KEY}" in out.getvalue()


def test_la_chiave_non_compare_in_log_output_ed_eccezioni(capsys):
    out = io.StringIO()
    _run_leaky(logsafe.handler(out))  # httpx a INFO ma con il filtro: l'URL esce con apikey=***
    assert "apikey=***" in out.getvalue() and KEY not in out.getvalue()

    for status in (401, 429, 500):  # errori: messaggio, repr, traceback, catena delle eccezioni
        tm._CACHE.clear()
        out = io.StringIO()
        errors = _run_leaky(logsafe.handler(out), status)
        (e,) = errors
        text = "".join(traceback.format_exception(e)) + str(e) + repr(e) + out.getvalue()
        assert KEY not in text and "apikey" not in str(e).lower() and e.__cause__ is None and e.__suppress_context__
    # timeout e simili: stessa cosa
    tm._CACHE.clear()

    def boom(req):
        raise httpx.ConnectTimeout("timeout", request=req)

    with pytest.raises(httpx.HTTPError) as e:
        list(adapter("Lombardia").events(httpx.Client(transport=httpx.MockTransport(boom)), NOW, 8))
    assert KEY not in "".join(traceback.format_exception(e.value)) + repr(e.value)
    shown = capsys.readouterr()
    assert KEY not in shown.out + shown.err


def test_redact_e_silenzio_degli_script(monkeypatch):
    assert logsafe.redact("GET https://x/y?a=1&apikey=segreto123&b=2") == "GET https://x/y?a=1&apikey=***&b=2"
    assert logsafe.redact(f"errore con {KEY} nel testo") == f"errore con *** nel testo"  # anche senza "apikey=" davanti
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.DEBUG)
    logsafe.quiet()
    assert logging.getLogger("httpx").level == logging.WARNING and logging.getLogger("httpcore").level == logging.WARNING


def test_run_collect_non_riporta_la_chiave_negli_errori_di_fonte():
    """L'errore di una fonte finisce in stats e nel riepilogo CI: dev'essere già ripulito."""
    run.SOURCES["ticketmaster-x"] = SimpleNamespace(
        name="ticketmaster-x", base=tm.BASE, city="T", province="", region="Lombardia", viewbox=None, regional=True,
        events=lambda c, n, h: (_ for _ in ()).throw(httpx.HTTPError(f"GET https://x/?apikey={KEY} fallita")))
    try:
        stats = {}
        run.collect(None, NoGeocoder(), ["ticketmaster-x"], NOW, 60, stats)
    finally:
        del run.SOURCES["ticketmaster-x"]
    assert KEY not in json.dumps(stats) and "apikey=***" in stats["ticketmaster-x"]["error"]


def test_nessuna_fixture_contiene_la_chiave():
    for f in (Path(__file__).parent / "fixtures").glob("ticketmaster*.json"):
        assert "apikey" not in f.read_text(encoding="utf-8").lower(), f.name


def test_mostra_con_un_titolo_per_giorno_della_settimana_e_una_sola():
    giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    items = [make(f"Castello Volante - {giorni[d % 7]}", f"2026-12-{d:02d}", segment="Arts & Theatre", genre="Fine Art",
                  classifications=[{"primary": True, "segment": {"name": "Arts & Theatre"}, "genre": {"name": "Fine Art"},
                                    "subGenre": {"name": "Fine Art"}, "type": {"name": "Event Style"}, "subType": {"name": "Audio/Visual"}}])
             for d in range(1, 15)]
    (ev,) = convert(*items)
    assert ev["title"] == "Castello Volante" and ev["longRunning"] is True


def test_musica_non_si_unisce_mai_nemmeno_se_ogni_giorno():
    """Una residency di 17 serate di fila (Einaudi) resta in date separate: la serie si unisce solo per le mostre."""
    items = [make("Ludovico Einaudi", f"2026-12-{d:02d}") for d in range(1, 18)]
    out = convert(*items)
    assert len(out) == 17 and not any(e.get("longRunning") for e in out)


@pytest.mark.parametrize("title,reason", [
    ("Club Milano SSD - U.S.D. Scanzorosciate", "sport dilettantistico"),
    ("A.S.D. Esempio - Union", "sport dilettantistico"),
    ("Milano HC Prospects vs Storm Pinerolo", "sport giovanile"),
    ("Novipiù Monferrato Basket - Varese Academy", "sport giovanile"),
])
def test_sport_dilettantistico_o_giovanile(title, reason):
    assert convert(make(title, segment="Sports", genre="Soccer"))[0]["_excluded"] == reason


def test_sport_professionistico_resta():
    for t in ("Milano HC vs EC Red Bull Salzburg", "U.S. Folgore Caratese - Union Brescia", "Olimpia Milano vs Virtus Bologna"):
        assert "_excluded" not in convert(make(t, segment="Sports", genre="Hockey"))[0]


def test_due_sessioni_nello_stesso_giorno_non_sono_doppioni():
    mattina = make("Lo Schiaccianoci", "2026-12-20", segment="Arts & Theatre", genre="Ballet")
    sera = make("Lo Schiaccianoci", "2026-12-20", segment="Arts & Theatre", genre="Ballet", id="X-sera")
    sera["dates"]["start"] = {"localDate": "2026-12-20", "localTime": "21:00:00", "dateTime": "2026-12-20T20:00:00Z"}
    mattina["dates"]["start"] = {"localDate": "2026-12-20", "localTime": "15:00:00", "dateTime": "2026-12-20T14:00:00Z"}
    a = adapter("Lombardia")
    src = SimpleNamespace(name="ticketmaster-x", base=tm.BASE, city="T", province="", region="Lombardia", viewbox=None, regional=True,
                          sessions=True, events=lambda c, n, h: iter(list(tm.merge_daily([a._event(i, NOW, 60) for i in (mattina, sera)]))))
    run.SOURCES["ticketmaster-x"] = src
    try:
        stats = {}
        out = run.collect(None, NoGeocoder(), ["ticketmaster-x"], NOW, 60, stats)
    finally:
        del run.SOURCES["ticketmaster-x"]
    assert len(out) == 2 and stats["ticketmaster-x"]["duplicates"] == 0
    assert TicketmasterAdapter.sessions is True


def test_nessun_campo_di_servizio_in_piu():
    for e in convert(make("Serata"), make("Mostra", segment="Arts & Theatre", genre="Fine Art")):
        assert {k for k in e if k.startswith("_")} <= {"_geocode", "_place", "_excluded"}


def test_fuori_vendita_resta_con_il_tag_offsale():
    item = make("Concerto esaurito")
    item["dates"]["status"] = {"code": "offsale"}
    (ev,) = convert(item)
    assert "_excluded" not in ev and ev["tags"] == ["offsale"] and ev["ticketUrl"]
    assert convert(make("In vendita"))[0]["tags"] == []


def test_solo_ticketmaster_esegue_solo_le_fonti_ticketmaster(monkeypatch):
    seen = {}

    def fake_collect(client, geocoder, names, *a, **k):
        seen["names"] = names
        return []

    monkeypatch.setattr(run, "collect", fake_collect)
    monkeypatch.setitem(run.SOURCES, "ticketmaster-lombardia", adapter("Lombardia"))
    monkeypatch.setitem(run.SOURCES, "ticketmaster-veneto", adapter("Veneto"))
    assert run.main(["--dry-run", "--solo-ticketmaster", "--retry-wait", "-1"]) == 1  # nessun evento dal finto collect
    assert sorted(seen["names"]) == sorted(n for n in run.SOURCES if n.startswith("ticketmaster-"))
    run.main(["--dry-run", "--solo-ticketmaster", "--regione", "veneto", "--retry-wait", "-1"])
    assert seen["names"] == ["ticketmaster-veneto"]


def test_solo_ticketmaster_senza_chiave(monkeypatch):
    for n in [n for n in run.SOURCES if n.startswith("ticketmaster-")]:
        monkeypatch.delitem(run.SOURCES, n)
    assert run.main(["--dry-run", "--solo-ticketmaster"]) == 1
