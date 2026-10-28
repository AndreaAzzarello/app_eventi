"""Open Data Hub Alto Adige / Südtirol: API regionale degli eventi (JSON, nessuno scraping).

GET https://tourism.opendatahub.com/v1/Event, paginata. Si importano solo i record con licenza aperta dichiarata nel
record stesso: LicenseInfo.ClosedData == false e LicenseInfo.License CC0 o CC-BY (mai NC, ND, SA), più Active e OdhActive.
Limiti d'uso (docs.opendatahub.com, "Quotas"): anonimi 10 richieste/s, 20 con l'header Referer, che l'API richiede;
qui 1 richiesta al secondo. Oltre il limite risponde 429, che ferma la fonte per quel giro (errore della fonte).
Il comune è quello italiano di LocationInfo.MunicipalityInfo: niente reverse geocoding.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar, Iterator

import httpx

from geo import slugify
from mapping import (KIDS_RE, ROME, category_from_title, event_id, geocode_queries, html_to_text, map_price,
                     shorten, too_long)

log = logging.getLogger("importer")

API = "https://tourism.opendatahub.com/v1/Event"
REFERER = "https://eventi-vicini.pages.dev/"  # l'API lo richiede per i client anonimi
OPEN_LICENSE = re.compile(r"CC0|CC-BY(-\d\.\d)?")  # fullmatch: niente -NC, -ND, -SA
LANGS = ("it", "de", "en")
PAGE_SIZE = 100
MAX_PAGES = 60  # 6.000 eventi: oltre, qualcosa non va
PAUSE = 1.0  # secondi tra due richieste


def _pick(by_lang, key: str) -> str:
    """Valore di `key` nella prima lingua disponibile (italiano, tedesco, inglese)."""
    if not isinstance(by_lang, dict):
        return ""
    for lang in LANGS:
        v = (by_lang.get(lang) or {}).get(key) if isinstance(by_lang.get(lang), dict) else None
        if v and str(v).strip():
            return str(v).strip()
    return ""


def _name(names) -> str:
    """Nome del comune {"it": "Valle di Casies", "de": "Gsies"}: italiano, poi le altre lingue."""
    if not isinstance(names, dict):
        return ""
    return next((str(names[k]).strip() for k in (*LANGS, *names) if names.get(k)), "")


def _instant(item: dict, utc_key: str, local_key: str) -> datetime | None:
    """Istante (Roma): l'epoch UTC del record, o l'ora locale scritta senza fuso."""
    try:
        if item.get(utc_key):
            return datetime.fromtimestamp(float(item[utc_key]) / 1000, UTC).astimezone(ROME)
        return datetime.fromisoformat(item[local_key]).replace(tzinfo=ROME)
    except (KeyError, TypeError, ValueError):
        return None


def is_open(item: dict) -> bool:
    """Licenza aperta dichiarata nel singolo record e record pubblicato; tutto il resto si scarta."""
    lic = item.get("LicenseInfo")
    return (isinstance(lic, dict) and lic.get("ClosedData") is False and bool(OPEN_LICENSE.fullmatch(str(lic.get("License") or "")))
            and item.get("Active") is True and item.get("OdhActive") is True)


@dataclass(frozen=True)
class OpenDataHubAdapter:
    name: str
    base: str
    city: str
    province: str
    region: str
    viewbox: str | None = None
    #: fonte regionale: niente scheda comune nella copertura, e nella deduplica vince la fonte comunale
    regional: ClassVar[bool] = True

    def events(self, client: httpx.Client, now: datetime, horizon_days: int) -> Iterator[dict]:
        params = {"pagesize": PAGE_SIZE, "active": "true", "odhactive": "true", "removenullvalues": "true",
                  "begindate": now.astimezone(ROME).date().isoformat(),
                  "enddate": (now + timedelta(days=horizon_days)).astimezone(ROME).date().isoformat()}
        for page in range(1, MAX_PAGES + 1):
            res = client.get(API, params=params | {"pagenumber": page}, headers={"Accept": "application/json", "Referer": REFERER})
            res.raise_for_status()
            data = res.json()
            for item in data.get("Items") or []:
                ev = self._event(item, now, horizon_days)
                if ev is not None:
                    yield ev
            if page >= (data.get("TotalPages") or 1) or not data.get("NextPage"):
                return
            time.sleep(PAUSE)
        log.warning("%s: oltre %d pagine, mi fermo", self.name, MAX_PAGES)

    def _event(self, item: dict, now: datetime, horizon_days: int) -> dict | None:
        if not is_open(item) or not item.get("Id"):
            return None
        title = _pick(item.get("Detail"), "Title")
        start, end = _instant(item, "DateBeginUTC", "DateBegin"), _instant(item, "DateEndUTC", "DateEnd")
        if not title or start is None or end is None or end < start:
            return None
        dates = item.get("EventDate") or []
        if dates and all(str(d.get("Cancelled")) == "1" for d in dates if isinstance(d, dict)):
            return None  # annullato
        url = f"{API}/{item['Id']}"
        if end < now or start > now + timedelta(days=horizon_days) or too_long(start, end, url):
            return None
        municipality = _name(((item.get("LocationInfo") or {}).get("MunicipalityInfo") or {}).get("Name"))
        if not municipality:
            return None  # senza comune non si sa dove metterlo
        contact = item.get("ContactInfos")
        street = _pick(contact, "Address")
        zip_city = f"{_pick(contact, 'ZipCode')} {municipality}".strip()
        description = shorten(html_to_text(_pick(item.get("Detail"), "BaseText") or _pick(item.get("Detail"), "IntroText")))
        lat, lng = item.get("Latitude"), item.get("Longitude")
        has_geo = isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and (lat or lng)
        images = item.get("ImageGallery") if isinstance(item.get("ImageGallery"), list) else []
        return {
            "id": event_id(url),
            "title": title,
            "shortDescription": description,
            "category": category_from_title(title) or "other",
            "priceType": map_price(description),
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
            "venueName": "",
            "address": ", ".join(p for p in (street, zip_city) if p),
            "lat": float(lat) if has_geo else None,
            "lng": float(lng) if has_geo else None,
            "imageUrl": next((i["ImageUrl"] for i in images if isinstance(i, dict) and str(i.get("ImageUrl", "")).startswith("https://")), ""),
            "ticketUrl": "",
            "tags": ["kids"] if KIDS_RE.search(f"{title} {description}") else [],
            "source": "scraper",
            "sourceUrl": url,
            "approxLocation": False,
            "_geocode": geocode_queries(street, "", municipality),
            # comune dal record (nome italiano): run.py non fa il reverse geocoding
            "_place": {"city": municipality, "citySlug": slugify(municipality), "province": self.province,
                       "region": self.region, "locality": ""},
        }
