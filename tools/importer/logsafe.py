"""Log degli script dell'importer senza segreti: httpx e httpcore tacciono (il loro log INFO stampa l'URL completo, con
`apikey=` nella query) e ogni riga scritta, traceback compresi, passa da un filtro che sostituisce il valore con ***."""

from __future__ import annotations

import logging
import os
import re
import sys

APIKEY = re.compile(r"(apikey=)[^&\s'\"]+", re.I)
SECRETS = ("TICKETMASTER_API_KEY",)  # variabili d'ambiente il cui valore non deve comparire mai, in nessuna forma


def redact(text: str) -> str:
    for name in SECRETS:
        if (value := os.environ.get(name)):
            text = text.replace(value, "***")
    return APIKEY.sub(r"\1***", text)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def quiet() -> None:
    """httpx e httpcore a WARNING: niente 'HTTP Request: GET <url con la chiave>'."""
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def handler(stream=None) -> logging.Handler:
    h = logging.StreamHandler(stream or sys.stderr)
    h.setFormatter(RedactingFormatter("%(message)s"))
    return h


def setup(level: int = logging.INFO) -> None:
    """Sostituisce logging.basicConfig + il silenzio di httpx negli script dell'importer."""
    logging.basicConfig(level=level, handlers=[handler()], force=True)
    quiet()
