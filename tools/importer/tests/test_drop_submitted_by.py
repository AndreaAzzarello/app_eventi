import sys
from pathlib import Path

from google.cloud.firestore import DELETE_FIELD

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
from fake_firestore import FakeFirestore  # noqa: E402

import drop_submitted_by  # noqa: E402

DATA = {
    "events/a": {"source": "user", "submittedBy": "uid1", "title": "A"},
    "events/b": {"source": "user", "title": "B"},  # già pulito
    "events/c": {"source": "scraper", "title": "C", "submittedBy": "non-toccare"},
}


def test_dry_run_non_scrive():
    db = FakeFirestore(DATA)
    st = drop_submitted_by.run(db)
    assert st == {"reads": 2, "due": 1, "writes": 0} and db.writes == 0
    assert db.data["events/a"]["submittedBy"] == "uid1"


def test_apply_toglie_solo_dove_serve():
    db = FakeFirestore(DATA)
    st = drop_submitted_by.run(db, apply=True)
    assert st["writes"] == 1 and db.writes == 1
    assert db.data["events/a"]["submittedBy"] is DELETE_FIELD and db.data["events/a"]["title"] == "A"
    assert db.data["events/c"]["submittedBy"] == "non-toccare"


def test_tetto_di_scritture():
    db = FakeFirestore({f"events/{i}": {"source": "user", "submittedBy": "u"} for i in range(5)})
    assert drop_submitted_by.run(db, apply=True, max_writes=2)["writes"] == 2
