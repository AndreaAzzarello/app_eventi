"""Fonti attive, lette da sources/<regione>.csv (righe con stato "attivo"). Vedi README, sezione Importer.

Aggiungere un CMS: una classe con l'interfaccia di adapters/base.py e un ramo in load_sources().
"""

from __future__ import annotations

import logging
import os

from geo import PROVINCES, slugify
from registry import base_url, read_rows

from .base import Adapter, fallback_place
from .design_comuni_html import DesignComuniHtmlAdapter
from .opendatahub import OpenDataHubAdapter
from .plone import PloneAdapter
from .ticketmaster import BASE as TICKETMASTER_BASE, TicketmasterAdapter
from .wordpress import WordpressAdapter

log = logging.getLogger("importer")


CMS_ADAPTERS = {"plone": PloneAdapter, "wordpress-dci": WordpressAdapter, "design_comuni_html": DesignComuniHtmlAdapter,
                "opendatahub": OpenDataHubAdapter}


def load_sources(rows: list[dict] | None = None) -> dict[str, Adapter]:
    out: dict[str, Adapter] = {}
    for r in read_rows() if rows is None else rows:
        if r["stato"] != "attivo":
            continue
        cls = CMS_ADAPTERS.get(r["cms"])
        if cls is None:
            log.warning("%s: nessun adapter per il CMS %r (supportati: %s), saltato",
                        r["comune"], r["cms"], ", ".join(CMS_ADAPTERS))
            continue
        name = slugify(r["comune"])
        extra = {"url_eventi": r["url_eventi"]} if cls is DesignComuniHtmlAdapter else {}
        out[name] = cls(name, base_url(r["sito"]), r["comune"], r["provincia"], r["regione"],
                        PROVINCES.get(r["provincia"], ("", None))[1], **extra)
    if os.environ.get("TICKETMASTER_API_KEY"):  # senza chiave la fonte non esiste: né CI né test cambiano
        for region in sorted({a.region for a in out.values()}, key=slugify):
            name = f"ticketmaster-{slugify(region)}"
            out[name] = TicketmasterAdapter(name, TICKETMASTER_BASE, "Ticketmaster", "", region)
    return out


SOURCES = load_sources()

__all__ = ["Adapter", "SOURCES", "fallback_place", "load_sources"]
