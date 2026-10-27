"""Fonti attive, lette da sources/comuni.csv (righe con stato "attivo"). Vedi README, sezione Importer.

Aggiungere un CMS: una classe con l'interfaccia di adapters/base.py e un ramo in load_sources().
"""

from __future__ import annotations

import logging

from geo import PROVINCES, slugify
from registry import base_url, read_rows

from .base import Adapter, fallback_place
from .plone import PloneAdapter

log = logging.getLogger("importer")


def load_sources(rows: list[dict] | None = None) -> dict[str, Adapter]:
    out: dict[str, Adapter] = {}
    for r in read_rows() if rows is None else rows:
        if r["stato"] != "attivo":
            continue
        if r["cms"] != "plone":
            log.warning("%s: nessun adapter per il CMS %r, saltato", r["comune"], r["cms"])
            continue
        name = slugify(r["comune"])
        out[name] = PloneAdapter(name, base_url(r["sito"]), r["comune"], r["provincia"], r["regione"],
                                 PROVINCES.get(r["provincia"], ("", None))[1])
    return out


SOURCES = load_sources()

__all__ = ["Adapter", "SOURCES", "fallback_place", "load_sources"]
