"""Registro delle fonti. Nuove fonti: vedi adapters/base.py e il README (sezione Importer)."""

from __future__ import annotations

from .base import Adapter, fallback_place
from .plone import PloneAdapter

# Provincia di Modena (lon_min, lat_max, lon_max, lat_min): scarta omonimie in altre regioni.
MODENA_VIEWBOX = "10.40,45.00,11.40,44.10"
_ER = "Emilia-Romagna"

# Siti design-comuni-plone: API REST pubblica (++api++), robots.txt senza Disallow.
# Termini: riuso consentito citando la fonte (l'app mostra il link "Fonte").
SOURCES: dict[str, Adapter] = {
    a.name: a
    for a in [
        PloneAdapter("modena", "https://www.comune.modena.it", "Modena", "MO", _ER, MODENA_VIEWBOX),
        PloneAdapter("formigine", "https://www.comune.formigine.mo.it", "Formigine", "MO", _ER, MODENA_VIEWBOX),
        PloneAdapter("sassuolo", "https://www.comune.sassuolo.mo.it", "Sassuolo", "MO", _ER, MODENA_VIEWBOX),
        PloneAdapter("mirandola", "https://www.comune.mirandola.mo.it", "Mirandola", "MO", _ER, MODENA_VIEWBOX),
    ]
}

__all__ = ["Adapter", "SOURCES", "fallback_place"]
