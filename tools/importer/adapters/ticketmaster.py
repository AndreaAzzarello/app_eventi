"""Ticketmaster Discovery API (v2): concerti, spettacoli e sport in Italia, con il link ufficiale d'acquisto.

GET https://app.ticketmaster.com/discovery/v2/events.json?countryCode=IT, a finestre di date. Senza affiliazione.
Termini (developer.ticketmaster.com/support/terms-of-use, letti il 30/10/2026): nessun logo né dicitura obbligatori
(niente uso dei marchi), contenuti conservati solo "for reasonable periods" (qui: finché l'evento è futuro e
l'API lo restituisce; poi la pulizia esistente), rimozione entro 24 h se il titolare lo chiede, vietato ricavarne
ricavi. Limiti: 5.000 chiamate al giorno, 5 al secondo, `size * page` < 1000: qui 2 al secondo e finestre che si
dividono finché ogni pagina profonda sta sotto il tetto.
La chiave sta in TICKETMASTER_API_KEY (secret GitHub); passa solo come parametro della richiesta e mai in un messaggio d'errore.
La fonte è regionale: vince la fonte comunale nella deduplica (run.collect). Il recupero è nazionale e si fa una sola
volta per processo; ogni istanza (una per regione) tiene gli eventi dei comuni della propria regione.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, time as dtime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Iterator

import httpx

from geo import slugify
from mapping import KIDS_RE, PREMIUM_FROM_EUR, ROME, category_from_title, event_id, one_line, shorten, too_long

log = logging.getLogger("importer")

API = "https://app.ticketmaster.com/discovery/v2/events.json"
BASE = "https://app.ticketmaster.com"
COMUNI = Path(__file__).parents[3] / "web" / "src" / "lib" / "data" / "comuni.json"
PAGE_SIZE = 200
DEEP_LIMIT = 1000  # size * page deve restare sotto: oltre, la finestra si divide
WINDOW_DAYS = 7
MAX_CALLS = 300  # per giro: oltre, qualcosa non va (quota giornaliera 5.000)
PAUSE = 0.5  # secondi tra due richieste (limite 5 al secondo)
NEAREST_KM = 15  # luogo con un nome di città che non è un comune: si prende il comune più vicino entro tanti km
EVENT_HOURS = 3  # la API non dà la fine: durata presunta
#: biglietti che non sono eventi: (motivo, regex sul titolo). Da tarare sui dati reali (--dump del dry-run).
NOT_EVENTS = [
    ("abbonamento o pass", re.compile(
        r"\b(abbonament\w*|season\s*pass|carnet|tessera|(?:daily|weekend|\d+[\s-]*days?|\d+[\s-]*giorn\w*)\s*(?:pass|ticket|ingresso)"
        r"|pass\s+(?:giornalier\w*|weekend|\d+[\s-]*giorn\w*))\b", re.I)),
    ("pre-show", re.compile(r"\bpre[\s-]?show\b", re.I)),
    ("programma gare", re.compile(r"\bprogramma\s+gare\b", re.I)),
    ("parcheggio o upgrade", re.compile(r"\b(parking|parcheggio|upgrade|vip package|pacchetto|hospitality|shuttle|navetta|meet\s*&\s*greet)\b", re.I)),
]
#: nomi di tipo/sottotipo/segmento della classificazione che indicano un prodotto e non un evento
NOT_EVENT_CLASS = re.compile(r"\b(parking|upsell|pass(?:es)?|season|subscription|abbonament\w*|package|merchandise|voucher|gift)\b", re.I)
YOUTH = re.compile(r"\b(giovanili|u\s?1\d|juniores|allievi|esordienti|attivit[àa] di base|triangolar\w*|academy|prospects)\b", re.I)
#: società dilettantistiche per forma giuridica (SSD, ASD, USD): non è sport professionistico
AMATEUR = re.compile(r"\b(?:s\.?s\.?d\.?|a\.?s\.?d\.?|u\.?s\.?d\.?)(?=\s|$|-)", re.I)
#: mostre e visite a biglietto giornaliero, dalla classificazione (genere, sottotipo): sono le sole che si uniscono in una serie
EXHIBIT = re.compile(r"fine art|museum|expo|cultural|multimedia|exhibition|mostra", re.I)
WEEKDAY = re.compile(r"\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)\b", re.I)
KIDS_GENRE = re.compile(r"famil|child|bambin", re.I)
TV = re.compile(r"registrazion\w*|\bTV\b|televis\w*|talk\s*show|programma\s+televisiv\w*|pubblico in studio", re.I)
CLASSICAL = re.compile(r"classic|orchestr|symphon|sinfon|concert|recital", re.I)
SEGMENTS = {"music": "music", "sports": "sport"}
EXHIBITION_MIN_COVERAGE = 0.5  # giorni con un biglietto / giorni tra il primo e l'ultimo

_LOCK = threading.Lock()
_CACHE: dict[tuple, list[dict] | Exception] = {}
_COMUNE: dict[str, tuple | None] = {}  # id evento → comune del luogo (calcolato una volta, condiviso dalle istanze)


class _Budget:
    def __init__(self) -> None:
        self.calls = 0


def _get(client: httpx.Client, key: str, params: dict, budget: _Budget) -> dict:
    """Una richiesta. Gli errori non contengono l'URL: c'è la chiave."""
    if budget.calls >= MAX_CALLS:
        raise httpx.HTTPError(f"Ticketmaster: oltre {MAX_CALLS} chiamate in un giro")
    budget.calls += 1
    try:
        res = client.get(API, params=params | {"apikey": key}, headers={"Accept": "application/json"})
        res.raise_for_status()
        return res.json()
    except httpx.HTTPStatusError as e:
        raise httpx.HTTPError(f"Ticketmaster HTTP {e.response.status_code}") from None
    except httpx.HTTPError as e:
        raise httpx.HTTPError(f"Ticketmaster {type(e).__name__}") from None
    except ValueError:
        raise httpx.HTTPError("Ticketmaster: risposta non JSON") from None
    except Exception as e:  # anche un'eccezione inattesa (es. InvalidURL) non deve portarsi dietro l'URL
        raise httpx.HTTPError(f"Ticketmaster {type(e).__name__}") from None
    finally:
        time.sleep(PAUSE)


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _window(client, key, start: datetime, end: datetime, budget: _Budget) -> Iterator[dict]:
    """Eventi che iniziano in [start, end]: se sono troppi per la paginazione profonda la finestra si divide."""
    params = {"countryCode": "IT", "size": PAGE_SIZE, "sort": "date,asc", "startDateTime": _iso(start), "endDateTime": _iso(end)}
    first = _get(client, key, params | {"page": 0}, budget)
    total = (first.get("page") or {}).get("totalElements") or 0
    if total > DEEP_LIMIT and end - start > timedelta(hours=1):
        mid = start + (end - start) / 2
        yield from _window(client, key, start, mid.replace(microsecond=0), budget)
        yield from _window(client, key, mid.replace(microsecond=0) + timedelta(seconds=1), end, budget)
        return
    yield from (first.get("_embedded") or {}).get("events") or []
    for page in range(1, min((first.get("page") or {}).get("totalPages") or 1, DEEP_LIMIT // PAGE_SIZE)):
        data = _get(client, key, params | {"page": page}, budget)
        yield from (data.get("_embedded") or {}).get("events") or []


def fetch_italy(client: httpx.Client, now: datetime, horizon_days: int) -> list[dict]:
    """Eventi grezzi di tutta l'Italia per i prossimi `horizon_days`: una volta per processo (le fonti girano in thread)."""
    cache_key = (now.date().isoformat(), horizon_days)
    with _LOCK:
        if cache_key not in _CACHE:
            try:
                _CACHE[cache_key] = _fetch(client, now, horizon_days)
            except Exception as e:  # anche l'errore si ricorda: le altre regioni non rifanno 300 chiamate
                _CACHE[cache_key] = e
        got = _CACHE[cache_key]
    if isinstance(got, Exception):
        raise got
    return got


def _fetch(client: httpx.Client, now: datetime, horizon_days: int) -> list[dict]:
    key = os.environ.get("TICKETMASTER_API_KEY", "")
    if not key:
        raise httpx.HTTPError("Ticketmaster: TICKETMASTER_API_KEY non impostata")
    budget, seen, out = _Budget(), set(), []
    t, stop = now.replace(microsecond=0), now + timedelta(days=horizon_days)
    while t < stop:
        end = min(t + timedelta(days=WINDOW_DAYS), stop) - timedelta(seconds=1)
        for item in _window(client, key, t, end, budget):
            if item.get("id") and item["id"] not in seen:
                seen.add(item["id"])
                out.append(item)
        t = end + timedelta(seconds=1)
    unplaced = sum(1 for item in out if _comune_of(item) is None)
    log.info("Ticketmaster: %d eventi in Italia, %d chiamate, %d senza comune riconosciuto (scartati)", len(out), budget.calls, unplaced)
    return out


# --- comune del luogo -------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _comuni() -> tuple[list[tuple], dict[str, list[tuple]]]:
    """(tutti i comuni, indice per slug del nome): (nome, sigla, regione, lat, lng, slug)."""
    raw = json.loads(COMUNI.read_text(encoding="utf-8"))
    rows, by_name = [], {}
    for nome, alt, sigla, reg, lat, lng, _pop, slug in raw["c"]:
        row = (nome, sigla, raw["regioni"][reg], lat, lng, slug or slugify(nome))
        rows.append(row)
        for n in (nome, alt):
            if n:
                by_name.setdefault(slugify(n), []).append(row)
    return rows, by_name


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dx = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(lat2 - lat1, dx) * 111.2


def find_comune(city: str, province: str, lat: float | None, lng: float | None) -> tuple | None:
    """Comune (nome, sigla, regione, lat, lng, slug) del luogo: per nome (e sigla se ce n'è più d'uno), altrimenti
    il più vicino alle coordinate entro NEAREST_KM; None se non si sa dove metterlo."""
    rows, by_name = _comuni()
    hits = by_name.get(slugify(city), [])
    if len(hits) > 1 and province:
        hits = [h for h in hits if h[1] == province.upper()] or hits
    if len(hits) > 1 and lat is not None:
        hits = [min(hits, key=lambda h: _km(lat, lng, h[3], h[4]))]
    if len(hits) == 1:
        return hits[0]
    if lat is None or hits:
        return None
    near = min(rows, key=lambda r: _km(lat, lng, r[3], r[4]))
    return near if _km(lat, lng, near[3], near[4]) <= NEAREST_KM else None


# --- mappatura --------------------------------------------------------------------------------------------------

def _classes(item: dict) -> dict:
    cls = item.get("classifications") or []
    c = next((x for x in cls if x.get("primary")), cls[0] if cls else {})
    return {k: ((c.get(k) or {}).get("name") or "") for k in ("segment", "genre", "subGenre", "type", "subType")}


def _category(item: dict, title: str) -> str:
    c = _classes(item)
    segment, genres = c["segment"].lower(), f"{c['genre']} {c['subGenre']}"
    if TV.search(title) or TV.search(genres):
        return "other"  # registrazioni televisive e talk show non sono concerti
    if KIDS_GENRE.search(genres):
        return "kids"
    if segment in SEGMENTS:
        return SEGMENTS[segment]
    if segment in ("arts & theatre", "film"):
        return "music" if CLASSICAL.search(genres) else "culture"
    return category_from_title(title) or "other"


def _not_event(item: dict, title: str, category: str) -> str | None:
    """Motivo per cui non è un evento (abbonamento, pass, parcheggio…), da titolo, classificazione e tipo del record."""
    if item.get("test") or (item.get("type") or "event") != "event":
        return "prodotto non evento"
    for reason, rx in NOT_EVENTS:
        if rx.search(title):
            return reason
    c = _classes(item)
    if NOT_EVENT_CLASS.search(f"{c['segment']} {c['type']} {c['subType']}"):
        return "prodotto non evento"
    if category == "sport" and YOUTH.search(title):
        return "sport giovanile"
    if category == "sport" and AMATEUR.search(title):
        return "sport dilettantistico"
    return None


def _image(item: dict) -> str:
    imgs = [i for i in item.get("images") or [] if i.get("ratio") == "16_9" and not i.get("fallback")
            and str(i.get("url", "")).startswith("https://")]
    return min(imgs, key=lambda i: abs((i.get("width") or 0) - 1024))["url"] if imgs else ""


def _times(item: dict) -> tuple[datetime, datetime] | None:
    start_d = (item.get("dates") or {}).get("start") or {}
    if start_d.get("dateTBD") or start_d.get("dateTBA"):
        return None
    if start_d.get("dateTime") and not (start_d.get("timeTBA") or start_d.get("noSpecificTime")):
        start = datetime.fromisoformat(start_d["dateTime"].replace("Z", "+00:00")).astimezone(ROME)
        return start, start + timedelta(hours=EVENT_HOURS)
    try:  # ora non nota: tutto il giorno
        day = date.fromisoformat(start_d["localDate"])
    except (KeyError, ValueError):
        return None
    return datetime.combine(day, dtime(0, 0), ROME), datetime.combine(day, dtime(23, 59), ROME)


def _comune_of(item: dict) -> tuple | None:
    venue = next(iter((item.get("_embedded") or {}).get("venues") or []), {})
    if item.get("id") not in _COMUNE:
        loc = venue.get("location") or {}
        try:
            lat, lng = float(loc["latitude"]), float(loc["longitude"])
            lat, lng = (lat, lng) if lat or lng else (None, None)
        except (KeyError, TypeError, ValueError):
            lat = lng = None
        _COMUNE[item.get("id")] = find_comune((venue.get("city") or {}).get("name", ""),
                                              (venue.get("state") or {}).get("stateCode", ""), lat, lng)
    return _COMUNE[item.get("id")]


def _series_title(title: str) -> str:
    """Titolo senza il giorno della settimana ("Castello Volante - Sabato" → "Castello Volante")."""
    return re.sub(r"\s*[-–|,:]*\s*$", "", re.sub(r"\s{2,}", " ", WEEKDAY.sub("", title))).strip() or title


def merge_daily(evs: list[dict]) -> Iterator[dict]:
    """Mostre e visite con un biglietto al giorno (stessa sede, stesso titolo a meno del giorno della settimana) → un solo
    evento longRunning dal primo all'ultimo giorno. Solo per le mostre (classificazione): le serie di date vere, come le
    residency di un cantante, restano separate. Si unisce con almeno 3 date che coprono metà del periodo (almeno 5 giorni)."""
    groups: dict[tuple, list[dict]] = {}
    for ev in evs:
        exhibit = ev.pop("_exhibit", False)
        if "_excluded" in ev or not exhibit:
            yield ev
        else:
            groups.setdefault((slugify(_series_title(ev["title"])), ev["venueName"], ev["_place"]["citySlug"]), []).append(ev)
    for (title, venue, city), group in groups.items():
        days = sorted({datetime.fromtimestamp(e["startTime"] / 1000, ROME).date() for e in group})
        span = (days[-1] - days[0]).days + 1
        if len(days) >= 3 and span >= 5 and len(days) / span >= EXHIBITION_MIN_COVERAGE:
            group.sort(key=lambda e: e["startTime"])
            known = [e["priceType"] for e in group if e["priceType"] != "unknown"]
            ev = group[0] | {"title": _series_title(group[0]["title"]), "endTime": max(e["endTime"] for e in group), "longRunning": True,
                             "sourceUrl": f"{BASE}/discovery/v2/series/{event_id(f'{title}|{venue}|{city}')}",
                             "priceType": max(known, key=("free", "low", "premium").index, default="unknown")}
            ev["id"] = event_id(ev["sourceUrl"])
            log.info("  Ticketmaster: %d date di «%s» unite in un evento", len(group), ev["title"])
            yield ev
        else:
            yield from group


@dataclass(frozen=True)
class TicketmasterAdapter:
    name: str
    base: str
    city: str
    province: str
    region: str
    viewbox: str | None = None
    #: fonte regionale: niente scheda comune nella copertura, e nella deduplica vince la fonte comunale
    regional: ClassVar[bool] = True
    #: più sessioni dello stesso titolo nello stesso giorno e comune, a orari diversi, restano eventi distinti (run.collect)
    sessions: ClassVar[bool] = True

    def events(self, client: httpx.Client, now: datetime, horizon_days: int) -> Iterator[dict]:
        found = [ev for item in fetch_italy(client, now, horizon_days) if (ev := self._event(item, now, horizon_days)) is not None]
        yield from merge_daily(found)

    def _event(self, item: dict, now: datetime, horizon_days: int) -> dict | None:
        title = one_line(item.get("name"))
        url = str(item.get("url") or "")
        times = _times(item)
        venue = next(iter((item.get("_embedded") or {}).get("venues") or []), {})
        if not item.get("id") or not title or not url.startswith("https://") or times is None or not venue:
            return None
        start, end = times
        source_url = f"{BASE}/discovery/v2/events/{item['id']}"
        if end < now or start > now + timedelta(days=horizon_days) or too_long(start, end, source_url):
            return None
        loc = venue.get("location") or {}
        try:
            lat, lng = float(loc["latitude"]), float(loc["longitude"])
            lat, lng = (lat, lng) if lat or lng else (None, None)
        except (KeyError, TypeError, ValueError):
            lat = lng = None
        comune = _comune_of(item)
        if comune is None or slugify(comune[2]) != slugify(self.region):
            return None  # luogo non riconosciuto, o di un'altra regione (la sua istanza lo tiene)
        nome, sigla, regione, clat, clng, cslug = comune
        category = _category(item, title)
        approx = lat is None
        if approx:
            lat, lng = clat, clng  # centro del comune: niente geocoding, e il dettaglio dice "luogo da confermare"
        prices = [p for p in item.get("priceRanges") or [] if p.get("currency") == "EUR" and isinstance(p.get("min"), (int, float))]
        low, high = min((p["min"] for p in prices), default=0), max((p.get("max") or p["min"] for p in prices), default=0)
        # senza fasce di prezzo in euro: "unknown" (prezzo sul sito del venditore), mai "low" di default; fasce come per gli altri adapter
        price_type = "unknown" if not prices else "free" if high == 0 else "premium" if high >= PREMIUM_FROM_EUR else "low"
        text = " ".join(filter(None, [f"Biglietti da {low:g} €." if low else "", one_line(item.get("info") or item.get("pleaseNote"))]))
        street = one_line((venue.get("address") or {}).get("line1"))
        zip_city = f"{venue.get('postalCode') or ''} {nome}".strip()
        ev = {
            "id": event_id(source_url),
            "title": title,
            "shortDescription": shorten(text),
            "category": category,
            "priceType": price_type,
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
            "venueName": one_line(venue.get("name")),
            "address": ", ".join(p for p in (street, zip_city) if p),
            "lat": lat,
            "lng": lng,
            "imageUrl": _image(item),
            "ticketUrl": url,
            "tags": ["kids"] if KIDS_RE.search(title) or KIDS_GENRE.search(json.dumps(item.get("classifications") or [])) else [],
            "source": "scraper",
            "sourceUrl": source_url,
            "approxLocation": approx,
            "_geocode": [],
            "_place": {"city": nome, "citySlug": cslug, "province": sigla, "region": regione, "locality": ""},
        }
        if (item.get("dates") or {}).get("status", {}).get("code") in ("cancelled", "canceled"):
            ev["_excluded"] = "annullato"  # run.collect lo scarta e, se già nel database, lo nasconde subito
        elif reason := _not_event(item, title, category):
            ev["_excluded"] = reason  # idem: contato per motivo nel riepilogo del dry-run
        ev["_exhibit"] = bool(EXHIBIT.search(" ".join(_classes(item).values())))  # tolto da merge_daily
        return ev
