"""Import incrementale sull'emulatore Firestore (query vere: count, select, in).

Si salta se manca FIRESTORE_EMULATOR_HOST. Lancio (JDK 21 solo per questo comando):
  firebase emulators:exec --only firestore --project demo-eventi "python -m pytest tests/test_emulator.py"
da una cartella con firebase.json (firebase/).
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
from test_write import NOW, event  # noqa: E402

pytestmark = pytest.mark.skipif(not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="emulatore non attivo")


def test_due_import_consecutivi_il_secondo_non_scrive():
    from run import write
    from seed_demo import emulator_client

    db = emulator_client()
    events = [event(i, importRegion="test-emulatore") for i in range(30)]
    ok = {"www.comune.test.it"}
    first = write([dict(e) for e in events], NOW, ok, db=db)
    second = write([dict(e) for e in events], NOW, ok, db=db)
    assert first["written"] == 30
    assert (second["written"], second["unchanged"], second["writes"]) == (0, 30, 0)
    print(f"letture del secondo giro: {second['reads']} per 30 eventi")


def test_manifest_sull_emulatore_il_secondo_giro_non_rilegge(tmp_path):
    from run import write
    from seed_demo import emulator_client

    db = emulator_client()
    events = [event(100 + i, importRegion="test-manifest") for i in range(30)]
    ok = {"www.comune.test.it"}
    first = write([dict(e) for e in events], NOW, ok, db=db, manifest_dir=tmp_path)
    second = write([dict(e) for e in events], NOW, ok, db=db, manifest_dir=tmp_path)
    assert (first["compare"], first["written"]) == ("firestore", 30)
    assert (second["compare"], second["written"], second["writes"]) == ("manifest", 0, 0)
    assert second["reads"] <= 3 < first["reads"]  # importState + query manuali, non i 30 eventi
    third = write([dict(e) for e in events], NOW, ok, db=db, manifest_dir=tmp_path, reconcile=True)
    assert (third["compare"], third["written"]) == ("firestore", 0)  # riconciliazione: nessun duplicato
