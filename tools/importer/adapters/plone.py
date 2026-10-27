"""Siti comunali su design-comuni-plone (io-Comune): API REST pubblica ++api++."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import httpx

from mapping import to_event

PAGE_SIZE = 25


@dataclass(frozen=True)
class PloneAdapter:
    name: str
    base: str
    city: str
    province: str
    region: str
    viewbox: str | None = None

    def fetch(self, client: httpx.Client, now: datetime) -> Iterator[dict]:
        """Eventi Plone non ancora finiti, pagina per pagina, 1 richiesta al secondo."""
        url = f"{self.base}/++api++/@search"
        params = {
            "portal_type": "Event", "end.query": now.strftime("%Y-%m-%d"), "end.range": "min",
            "sort_on": "start", "b_size": PAGE_SIZE, "fullobjects": 1,
        }
        while url:
            res = client.get(url, params=params, headers={"Accept": "application/json"})
            res.raise_for_status()
            data = res.json()
            yield from data.get("items", [])
            url, params = (data.get("batching") or {}).get("next"), None
            if url:
                time.sleep(1)

    def events(self, client: httpx.Client, now: datetime, horizon_days: int) -> Iterator[dict]:
        for item in self.fetch(client, now):
            ev = to_event(item, {"city": self.city}, now, horizon_days)
            if ev is not None:
                yield ev
