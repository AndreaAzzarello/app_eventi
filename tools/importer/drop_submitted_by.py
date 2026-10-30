"""Una tantum: toglie `submittedBy` (uid dell'autore) dagli eventi pubblici già approvati.

Gli eventi nuovi non lo hanno più (web/src/lib/admin.ts); qui si ripuliscono quelli vecchi.
Legge solo gli eventi con source == "user" (una lettura ciascuno) e scrive solo dove il campo c'è.

Uso:  python drop_submitted_by.py            # dry-run: conta, non scrive
      python drop_submitted_by.py --apply    # toglie il campo (una scrittura per evento)
Credenziali: come run.py (FIREBASE_SERVICE_ACCOUNT o GOOGLE_APPLICATION_CREDENTIALS).
"""

from __future__ import annotations

import argparse
import logging
import sys

import logsafe
from run import commit_in_batches

log = logging.getLogger("importer")
MAX_WRITES = 15_000  # quota Spark 20.000 scritture al giorno, con margine


def run(db, apply: bool = False, max_writes: int = MAX_WRITES) -> dict:
    from google.cloud.firestore import DELETE_FIELD
    from google.cloud.firestore_v1.base_query import FieldFilter

    events = db.collection("events")
    docs = list(events.where(filter=FieldFilter("source", "==", "user")).select(["submittedBy"]).stream())
    due = [d.id for d in docs if "submittedBy" in (d.to_dict() or {})]
    todo = due[:max_writes]
    if len(due) > len(todo):
        log.warning("Da aggiornare %d eventi, oltre il tetto di %d: rilancia domani", len(due), max_writes)
    if apply:
        commit_in_batches(db, [lambda b, i=i: b.update(events.document(i), {"submittedBy": DELETE_FIELD}) for i in todo])
    stats = {"reads": len(docs), "due": len(due), "writes": len(todo) if apply else 0}
    log.info("submittedBy%s: %d eventi user, %d con il campo, %d scritture", "" if apply else " (dry-run)",
             len(docs), len(due), stats["writes"])
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="scrive davvero (senza, è un dry-run)")
    p.add_argument("--max-writes", type=int, default=MAX_WRITES)
    args = p.parse_args(argv)
    logsafe.setup()
    from db import client

    run(client(), args.apply, args.max_writes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
