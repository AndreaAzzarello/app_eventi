"""Statistiche mensili stats/{regione}_{AAAA-MM}: una scrittura al giorno per regione, unione degli id."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
from fake_firestore import FakeFirestore  # noqa: E402
from run import month_bounds, write_month_stats  # noqa: E402

DAY = 86_400_000
D1 = datetime(2026, 11, 3, 5, 0, tzinfo=timezone.utc)
D2 = datetime(2026, 11, 10, 5, 0, tzinfo=timezone.utc)
START = month_bounds(D1)[1]


def ev(i, city="modena", region="emilia-romagna", day=5, span=1):
    return {"id": f"e{i}", "citySlug": city, "city": city.title(), "importRegion": region,
            "startTime": START + day * DAY, "endTime": START + (day + span) * DAY}


def test_confini_del_mese_a_ora_di_roma():
    month, start, end = month_bounds(datetime(2026, 10, 31, 23, 30, tzinfo=timezone.utc))  # già 1 novembre a Roma
    assert month == "2026-11"
    assert (end - start) // DAY == 30


def test_primo_giro_conta_solo_gli_eventi_del_mese_e_scrive_una_volta_per_regione():
    db = FakeFirestore()
    events = [ev(1), ev(2, "sassuolo"), ev(3, day=40), ev(4, region="veneto", city="verona"), ev(5, day=-20, span=2)]
    assert write_month_stats(db, events, {"emilia-romagna", "veneto"}, D1) == (2, 2)
    assert (db.writes, db.reads) == (2, 2)
    d = db.data["stats/emilia-romagna_2026-11"]
    assert (d["events"], d["comuni"], d["month"]) == (2, 2, "2026-11")
    assert db.data["stats/veneto_2026-11"]["events"] == 1


def test_il_giorno_dopo_gli_eventi_gia_contati_restano_anche_se_spariti_dalla_fonte():
    db = FakeFirestore()
    write_month_stats(db, [ev(1), ev(2)], {"emilia-romagna"}, D1)
    write_month_stats(db, [ev(2), ev(6, "carpi")], {"emilia-romagna"}, D2)  # e1 è finito e non c'è più
    d = db.data["stats/emilia-romagna_2026-11"]
    assert d["events"] == 3 and d["comuni"] == 2
    assert d["cities"][0] == {"slug": "modena", "name": "Modena", "n": 2}


def test_cambio_mese_nuovo_documento_senza_ereditare():
    db = FakeFirestore()
    write_month_stats(db, [ev(1)], {"emilia-romagna"}, D1)
    dec = datetime(2026, 12, 2, 5, 0, tzinfo=timezone.utc)
    nxt = {**ev(9), "startTime": month_bounds(dec)[1] + DAY, "endTime": month_bounds(dec)[1] + 2 * DAY}
    write_month_stats(db, [nxt], {"emilia-romagna"}, dec)
    assert db.data["stats/emilia-romagna_2026-11"]["events"] == 1
    assert db.data["stats/emilia-romagna_2026-12"]["events"] == 1


def test_solo_le_dieci_citta_principali():
    db = FakeFirestore()
    write_month_stats(db, [ev(i, f"citta{i:02d}") for i in range(15)], {"emilia-romagna"}, D1)
    assert len(db.data["stats/emilia-romagna_2026-11"]["cities"]) == 10
