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


def test_documento_coverage():
    from types import SimpleNamespace

    from run import coverage_doc

    src = [SimpleNamespace(city="Lecco", province="LC"), SimpleNamespace(city="Como", province="CO"),
           SimpleNamespace(city="Senza Centro", province="CO")]
    events = [event(1, citySlug="lecco"), event(2, citySlug="lecco"), event(3, citySlug="como"),
              event(4, citySlug="lecco", importRegion="veneto")]
    centers = {("Lombardia", "lecco"): (45.85612, 9.39771), ("Lombardia", "como"): (45.81, 9.08)}
    doc = coverage_doc("Lombardia", src, events, centers, 5)
    assert doc == {"name": "Lombardia", "updatedAt": 5, "comuni": [
        {"name": "Como", "slug": "como", "province": "CO", "lat": 45.81, "lng": 9.08, "events": 1},
        {"name": "Lecco", "slug": "lecco", "province": "LC", "lat": 45.8561, "lng": 9.3977, "events": 2}]}


def test_primo_import_grande_legge_i_mancanti_a_blocchi():
    db = FakeFirestore()
    calls = []
    original = db.get_all
    db.get_all = lambda refs, field_paths=None: (calls.append(len(refs)), original(refs, field_paths))[1]
    s = run(db, [event(i) for i in range(700)])
    assert calls == [300, 300, 100] and s["written"] == 700


# ---- manifest locale ---------------------------------------------------------------------------------------------

DAY2 = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)


def mrun(db, events, tmp_path, now=NOW, **kw):
    return run(db, events, now, manifest_dir=tmp_path, **kw)


def test_manifest_secondo_giro_senza_leggere_gli_eventi(tmp_path):
    db, events = FakeFirestore(), [event(i) for i in range(50)]
    s1 = mrun(db, events, tmp_path)
    assert s1["compare"] == "firestore" and s1["written"] == 50
    db.reads = db.writes = 0
    s2 = mrun(db, events, tmp_path, now=DAY2)
    assert (s2["compare"], s2["written"], s2["unchanged"], db.writes) == ("manifest", 0, 50, 0)
    assert s2["reads"] <= 3 and db.reads <= s2["reads"]  # importState + query manuali (min 1), non 50


def test_manifest_scrive_solo_le_modifiche_e_resta_coerente(tmp_path):
    db, events = FakeFirestore(), [event(i) for i in range(5)]
    mrun(db, events, tmp_path)
    events[1] = event(1, title="Cambiato")
    s = mrun(db, events, tmp_path, now=DAY2)
    assert (s["compare"], s["written"]) == ("manifest", 1) and db.data["events/e1"]["createdAt"] == NOW_MS
    s = mrun(db, events, tmp_path, now=datetime(2026, 11, 3, 6, 0, tzinfo=timezone.utc))
    assert (s["compare"], s["written"], s["unchanged"]) == ("manifest", 0, 5)


@pytest.mark.parametrize("case", ["assente", "vecchio", "reconcile", "token", "illeggibile"])
def test_manifest_fallback_alla_riconciliazione(tmp_path, case):
    db, events = FakeFirestore(), [event(i) for i in range(4)]
    mrun(db, events, tmp_path)
    now, kw = DAY2, {}
    if case == "assente":
        (tmp_path / "lombardia.json").unlink()
    elif case == "vecchio":
        now = datetime(2026, 11, 10, 6, 1, tzinfo=timezone.utc)  # più di 8 giorni dopo la riconciliazione
    elif case == "reconcile":
        kw["reconcile"] = True
    elif case == "token":
        db.data["importState/lombardia"]["token"] = "altro"
    else:
        (tmp_path / "lombardia.json").write_text("{non json", encoding="utf-8")
    s = mrun(db, events, tmp_path, now=now, **kw)
    assert (s["compare"], s["written"], s["unchanged"]) == ("firestore", 0, 4)  # niente scritture duplicate
    assert mrun(db, events, tmp_path, now=now)["compare"] == "manifest"  # la riconciliazione rinnova il manifest


def test_manifest_non_sovrascrive_le_modifiche_manuali(tmp_path):
    db, events = FakeFirestore(), [event(i) for i in range(3)]
    mrun(db, events, tmp_path)
    db.data["events/e1"]["source"] = "manual"  # l'admin ha ritoccato l'evento dopo l'ultimo import
    s = mrun(db, [event(0), event(1, title="Dalla fonte"), event(2)], tmp_path, now=DAY2)
    assert (s["compare"], s["kept_manual"], s["written"]) == ("manifest", 1, 0)
    assert db.data["events/e1"]["title"] == "Evento 1"


def test_manifest_run_interrotto_non_salva_e_il_giro_dopo_riconcilia(tmp_path):
    db, events = FakeFirestore(), [event(i) for i in range(3)]
    mrun(db, events, tmp_path)
    changed = [event(i, title=f"Nuovo {i}") for i in range(3)]
    real_commit, calls = db.batch, []

    def flaky():
        b = real_commit()
        orig = b.commit
        b.commit = lambda: (calls.append(1), (_ for _ in ()).throw(RuntimeError("rete")) if len(calls) == 2 else orig())[1]
        return b

    db.batch = flaky
    with pytest.raises(RuntimeError):
        mrun(db, changed, tmp_path, now=DAY2)  # il 2º commit (gli eventi) fallisce
    db.batch = real_commit
    assert db.data["importState/lombardia"]["token"] == "pending"  # non coincide col manifest su disco
    s = mrun(db, changed, tmp_path, now=DAY2)
    assert s["compare"] == "firestore" and s["written"] == 3 and len(db.data) == 4  # 3 eventi + importState


def test_manifest_documento_sparito_ripiega_sulla_riconciliazione(tmp_path):
    db, events = FakeFirestore(), [event(i) for i in range(3)]
    mrun(db, events, tmp_path)
    del db.data["events/e0"]  # cancellato a mano da Firebase
    # l'evento e0 sparisce dalla fonte: l'update di missingRuns su un documento inesistente dà NotFound
    s1 = mrun(db, events[1:], tmp_path, now=DAY2)
    assert s1["compare"] == "firestore" and "events/e0" not in db.data


def test_manifest_pota_gli_eventi_che_la_pulizia_elimina(tmp_path):
    old = event(0, startTime=NOW_MS - 9 * DAY, endTime=NOW_MS - 8 * DAY)  # già da eliminare per cleanup.py
    db = FakeFirestore()
    mrun(db, [old, event(1)], tmp_path)
    del db.data["events/e0"]  # la pulizia l'ha eliminato
    s = mrun(db, [old, event(1)], tmp_path, now=DAY2)
    assert (s["compare"], s["written"]) == ("manifest", 1) and "events/e0" in db.data  # non risulta più "noto"


def test_coverage_include_le_citta_con_eventi_anche_senza_fonte_comunale():
    """Bolzano arriva da Open Data Hub (fonte regionale): niente riga nel registro, ma ha eventi → è coperta."""
    from types import SimpleNamespace

    from run import coverage_doc

    src = [SimpleNamespace(city="Trento", province="TN")]
    centers = {("Trentino-Alto Adige", "trento"): (46.07, 11.12)}
    odh = {"importRegion": "trentino-alto-adige", "city": "Bolzano", "citySlug": "bolzano", "cityAlt": "Bozen", "province": "BZ"}
    events = [event(1, **odh, lat=46.49, lng=11.35), event(2, **odh, lat=46.51, lng=11.37),
              event(3, **odh, lat=40.0, lng=10.0, approxLocation=True),  # centro approssimato: non sposta la media
              event(4, citySlug="trento", importRegion="trentino-alto-adige", city="Trento", province="TN")]
    doc = coverage_doc("Trentino-Alto Adige", src, events, centers, 5)
    assert doc["comuni"] == [
        {"name": "Bolzano", "slug": "bolzano", "province": "BZ", "lat": 46.5, "lng": 11.36, "events": 3, "alt": "Bozen"},
        {"name": "Trento", "slug": "trento", "province": "TN", "lat": 46.07, "lng": 11.12, "events": 1}]
