"""Fonti attive, lette da sources/comuni.csv (righe con stato "attivo"). Vedi README, sezione Importer.

Aggiungere un CMS: una classe con l'interfaccia di adapters/base.py e un ramo in load_sources().
"""

from __future__ import annotations

import logging

from geo import slugify
from registry import base_url, read_rows

from .base import Adapter, fallback_place
from .plone import PloneAdapter

log = logging.getLogger("importer")

# Provincia di Modena (lon_min, lat_max, lon_max, lat_min): scarta omonimie in altre regioni.
PROVINCE_VIEWBOX = {"MO": "10.40,45.00,11.40,44.10"}


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
                                 PROVINCE_VIEWBOX.get(r["provincia"]))
    return out


SOURCES = load_sources()

__all__ = ["Adapter", "SOURCES", "fallback_place", "load_sources"]
