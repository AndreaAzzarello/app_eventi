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
