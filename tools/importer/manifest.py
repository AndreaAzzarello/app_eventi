"""Manifest locale degli hash: id → campi di PROJECTION (run.py) per regione, in manifests/<regione>.json.

Evita la lettura giornaliera di tutti gli eventi da Firestore: il confronto parte dal manifest e la lettura
completa (riconciliazione) avviene solo se il manifest manca, ha più di 8 giorni, non è coerente con
importState/<regione> su Firestore o con --reconcile. Il `token` del manifest deve coincidere con quello di
importState: lo cambia solo un import concluso, quindi un run interrotto o una cache persa portano alla
riconciliazione. Le scritture sono idempotenti (id deterministici), quindi il fallback non duplica né cancella.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

VERSION = 1
MAX_AGE_MS = 8 * 86_400_000  # 7 giorni di scaglionamento (ci_report.reconcile_days) + 1 di tolleranza
STATE = "importState"  # collezione con un documento {token, savedAt} per regione (solo Admin SDK)


def load(directory: Path, region: str, now_ms: int) -> dict | None:
    """Il manifest della regione se è leggibile e più giovane di 7 giorni, altrimenti None."""
    try:
        m = json.loads((directory / f"{region}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (isinstance(m, dict) and m.get("version") == VERSION and m.get("token") and isinstance(m.get("docs"), dict)):
        return None
    age = now_ms - (m.get("reconciledAt") or 0)
    return m if 0 <= age < MAX_AGE_MS else None


def save(directory: Path, region: str, m: dict) -> None:
    """Scrittura atomica: un run interrotto non lascia un file a metà."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{region}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": VERSION} | m, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def prune(docs: dict[str, dict], now_ms: int) -> dict[str, dict]:
    """Toglie i documenti che cleanup.py elimina (stessa regola), così non risultano 'noti' quando non esistono più."""
    from cleanup import expired_events  # import locale: cleanup importa run, che importa questo modulo

    gone = set(expired_events(docs, now_ms))
    return {i: d for i, d in docs.items() if i not in gone}
