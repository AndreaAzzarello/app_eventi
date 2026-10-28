"""Open Data Hub Alto Adige: solo record con licenza aperta dichiarata nel record, comune italiano, deduplica."""

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
from adapters.opendatahub import API, OpenDataHubAdapter, is_open  # noqa: E402

NOW = datetime(2026, 11, 26, 6, 0, tzinfo=timezone.utc)
RAW = json.loads((Path(__file__).parent / "fixtures" / "opendatahub_events.json").read_text(encoding="utf-8"))
ADAPTER = OpenDataHubAdapter("open-data-hub", "https://tourism.opendatahub.com", "Open Data Hub Alto Adige", "BZ",
                             "Trentino-Alto Adige", None)


def items() -> list[dict]:
    return copy.deepcopy(RAW["Items"])


def convert(item: dict) -> dict | None:
    return ADAPTER._event(item, NOW, 60)


def test_record_reali_diventano_eventi_con_comune_italiano():
    evs = [ev for i in items() if (ev := convert(i))]
    assert len(evs) == 8
    first = evs[0]
    assert first["title"] == "Avvento nel bosco di larici"  # italiano, non tedesco
    assert first["_place"] == {"city": "Nova Ponente", "citySlug": "nova-ponente", "province": "BZ",
                               "region": "Trentino-Alto Adige", "locality": ""}
    assert first["sourceUrl"].startswith(f"{API}/") and first["source"] == "scraper"
    assert first["lat"] and first["lng"] and first["endTime"] > first["startTime"]
    # fuso: DateBegin 2026-12-11T16:00 ora locale = 15:00 UTC
    assert datetime.fromtimestamp(first["startTime"] / 1000, timezone.utc).hour == 15
    assert len({e["id"] for e in evs}) == 8


def test_alias_tedesco_dal_registro():
    ev = convert(items()[0])
    ev.update(city=ev["_place"]["city"], citySlug=ev["_place"]["citySlug"], province="BZ", region="Trentino-Alto Adige")
    run.use_italian_name(ev)
    assert (ev["city"], ev["citySlug"], ev["cityAlt"]) == ("Nova Ponente", "nova-ponente", "Deutschnofen")


@pytest.mark.parametrize("change", [
    lambda i: i["LicenseInfo"].update(ClosedData=True),
    lambda i: i["LicenseInfo"].update(License="CC-BY-NC-4.0"),
    lambda i: i["LicenseInfo"].update(License="CC-BY-SA-4.0"),
    lambda i: i["LicenseInfo"].update(License="CC-BY-ND-4.0"),
    lambda i: i["LicenseInfo"].update(License=""),
    lambda i: i["LicenseInfo"].pop("ClosedData"),
    lambda i: i.pop("LicenseInfo"),
    lambda i: i.update(Active=False),
    lambda i: i.update(OdhActive=False),
    lambda i: i["LocationInfo"].pop("MunicipalityInfo"),
    lambda i: [d.update(Cancelled="1") for d in i["EventDate"]],
])
def test_scarta_cio_che_non_ha_licenza_aperta_o_non_e_pubblicabile(change):
    item = items()[1]
    assert convert(item) is not None
    change(item)
    assert convert(item) is None


def test_licenze_aperte_ammesse():
    for lic in ("CC0", "CC-BY", "CC-BY-4.0"):
        item = items()[0]
        item["LicenseInfo"]["License"] = lic
        assert is_open(item), lic


def test_orizzonte_e_durata():
    item = items()[0]  # inizia l'11/12
    assert ADAPTER._event(item, NOW, 5) is None  # oltre l'orizzonte
    assert ADAPTER._event(item, datetime(2027, 1, 10, tzinfo=timezone.utc), 60) is None  # già finito
    item["DateEndUTC"] = item["DateBeginUTC"] + 400 * 86_400_000
    assert convert(item) is None  # oltre 365 giorni


def client(pages: list[dict], seen: list | None = None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        if status != 200:
            return httpx.Response(status)
        n = int(request.url.params["pagenumber"])
        return httpx.Response(200, json=pages[n - 1])
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_paginazione_referer_e_filtri(monkeypatch):
    monkeypatch.setattr("adapters.opendatahub.time.sleep", lambda s: None)
    its = items()
    pages = [{"TotalPages": 2, "NextPage": "x", "Items": its[:4]}, {"TotalPages": 2, "NextPage": None, "Items": its[4:]}]
    seen: list[httpx.Request] = []
    evs = list(ADAPTER.events(client(pages, seen), NOW, 60))
    assert len(evs) == 8 and len(seen) == 2
    req = seen[0]
    assert req.headers["Referer"].startswith("https://eventi-vicini.pages.dev")
    assert dict(req.url.params) | {"pagenumber": "1"} == dict(req.url.params)
    assert req.url.params["active"] == "true" and req.url.params["odhactive"] == "true"
    assert req.url.params["begindate"] == "2026-11-26" and req.url.params["enddate"] == "2027-01-25"


def test_limite_superato_ferma_la_fonte():
    with pytest.raises(httpx.HTTPStatusError):
        list(ADAPTER.events(client([], status=429), NOW, 60))


def fake_source(name: str, evs: list[dict], regional: bool):
    return SimpleNamespace(name=name, base=f"https://{name}.example", city="Lana", province="BZ", region="Trentino-Alto Adige",
                           viewbox=None, regional=regional, events=lambda client, now, horizon: iter(evs))


class NoGeocoder:
    deferred: list = []
    requests = 0

    def reverse(self, *a, **k):
        return None

    def lookup(self, *a, **k):
        return None


def test_deduplica_vince_la_fonte_comunale(monkeypatch):
    hub_ev = convert(items()[1])  # Lana, 12/12 15:30 "Racconti d'Avvento…"
    comune_ev = dict(hub_ev) | {"id": "comune1", "sourceUrl": "https://comune.lana.example/e/1", "shortDescription": "più ricco",
                                "startTime": hub_ev["startTime"] + 30 * 60_000, "endTime": hub_ev["endTime"] + 30 * 60_000}
    comune_ev.pop("_place")
    srcs = {"hub": fake_source("hub", [hub_ev], True), "comune": fake_source("comune", [comune_ev], False)}
    monkeypatch.setattr(run, "SOURCES", srcs)
    stats: dict = {}
    out = run.collect(None, NoGeocoder(), ["hub", "comune"], NOW, 60, stats)
    assert [e["id"] for e in out] == ["comune1"]
    assert (stats["hub"]["events"], stats["comune"]["events"]) == (0, 1)
    # senza il doppione l'evento regionale entra
    monkeypatch.setattr(run, "SOURCES", {"hub": fake_source("hub", [convert(items()[1])], True)})
    out = run.collect(None, NoGeocoder(), ["hub"], NOW, 60, {})
    assert len(out) == 1 and out[0]["city"] == "Lana" and "_place" not in out[0]
