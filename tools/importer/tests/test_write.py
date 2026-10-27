"""Scritture incrementali: hash del contenuto, solo i cambiamenti, limiti di quota."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
from fake_firestore import FakeFirestore  # noqa: E402
from mapping import content_hash  # noqa: E402
from run import QuotaExceeded, plan_writes, write  # noqa: E402

NOW = datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
DAY = 86_400_000
OK = {"www.comune.test.it"}


def event(i: int, **over) -> dict:
    ev = {"id": f"e{i}", "title": f"Evento {i}", "startTime": NOW_MS + DAY, "endTime": NOW_MS + 2 * DAY,
          "source": "scraper", "sourceUrl": f"https://www.comune.test.it/e/{i}", "importRegion": "lombardia"} | over
    ev["contentHash"] = content_hash(ev)
    return ev


def run(db, events, now=NOW, **kw):
    return write([dict(e) for e in events], now, OK, db=db, **kw)


def test_content_hash_ignora_i_campi_di_servizio():
    ev = event(1)
    assert content_hash(ev) == content_hash(ev | {"updatedAt": 5, "createdAt": 1, "missingRuns": 1, "removedAt": 3,
                                                  "importRegion": "veneto", "contentHash": "x", "id": "z"})
    assert content_hash(ev) != content_hash(ev | {"title": "Altro"})
    assert content_hash(ev) == content_hash(dict(reversed(list(ev.items()))))  # indipendente dall'ordine


def test_plan_writes_solo_nuovi_o_cambiati():
    a, b, c = event(1), event(2), event(3)
    existing = {"e1": {"source": "scraper", "contentHash": a["contentHash"]},
                "e2": {"source": "scraper", "contentHash": "vecchio"}}
    p = plan_writes([a, b, c], existing, OK, NOW_MS, 60 * DAY)
    assert [e["id"] for e in p["write"]] == ["e2", "e3"] and p["unchanged"] == 1


def test_plan_writes_ripristina_i_nascosti_e_salta_i_manuali():
    a, b = event(1), event(2)
    existing = {"e1": {"source": "scraper", "contentHash": a["contentHash"], "removedAt": 5},
                "e2": {"source": "manual", "contentHash": "x"}}
    p = plan_writes([a, b], existing, OK, NOW_MS, 60 * DAY)
    assert [e["id"] for e in p["write"]] == ["e1"] and p["kept_manual"] == 1


def test_primo_import_scrive_tutto_il_secondo_niente():
    db, events = FakeFirestore(), [event(i) for i in range(5)]
    s1 = run(db, events)
    assert (s1["written"], s1["unchanged"], db.writes) == (5, 0, 5)
    assert db.data["events/e0"]["createdAt"] == NOW_MS and "id" not in db.data["events/e0"]
    db.writes = db.reads = 0
    s2 = run(db, events)
    assert (s2["written"], s2["unchanged"], db.writes) == (0, 5, 0)
    assert s2["reads"] == db.reads  # le letture stimate sono quelle fatte davvero


def test_modifica_riscrive_solo_quell_evento_e_tiene_createdat():
    db, events = FakeFirestore(), [event(i) for i in range(5)]
    run(db, events)
    events[2] = event(2, title="Nuovo titolo")
    s = run(db, events, datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc))
    assert s["written"] == 1 and db.data["events/e2"]["title"] == "Nuovo titolo"
    assert db.data["events/e2"]["createdAt"] == NOW_MS


def test_spariti_dalla_fonte_poi_nascosti_e_ripristinati():
    db, events = FakeFirestore(), [event(i) for i in range(3)]
    run(db, events)
    for _ in range(2):
        s = run(db, events[:2], regions={"lombardia"})
    assert s["hidden"] == 1 and db.data["events/e2"]["removedAt"] == NOW_MS
    run(db, events)  # ricompare
    assert "removedAt" not in db.data["events/e2"] and "missingRuns" not in db.data["events/e2"]


def test_vecchio_documento_senza_importregion_si_riscrive_una_volta():
    db = FakeFirestore({"events/e0": {"source": "scraper", "createdAt": 7, "title": "vecchio"}})
    s = run(db, [event(0)])
    assert s["written"] == 1 and db.data["events/e0"]["createdAt"] == 7 and db.data["events/e0"]["importRegion"]


def test_manuale_non_si_tocca():
    db = FakeFirestore({"events/e0": {"source": "manual", "title": "mio"}})
    s = run(db, [event(0)])
    assert s["written"] == 0 and db.data["events/e0"]["title"] == "mio"


def test_limiti_di_quota_fermano_prima_di_scrivere():
    db, events = FakeFirestore(), [event(i) for i in range(5)]
    with pytest.raises(QuotaExceeded):
        run(db, events, max_writes=4)
    assert db.writes == 0
    db.data.update({f"events/x{i}": {"importRegion": "lombardia", "source": "scraper"} for i in range(10)})
    with pytest.raises(QuotaExceeded):
        run(db, events, max_reads=5)
    assert db.writes == 0


def test_batch_da_400():
    db = FakeFirestore()
    run(db, [event(i) for i in range(1000)])
    assert db.writes == 1000 and db.commits == 3
