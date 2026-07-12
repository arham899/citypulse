"""AllEvents.in scraper — the strongest live source of local Islamabad events.

The city listing page embeds its full event payload as JSON inside a Vue
component (`events_data = [...]`), including venue coordinates, organizer,
categories, images, and ticket links. We extract that payload directly —
no headless browser needed.
"""

import json
import logging
import re
from datetime import datetime, timezone

import httpx

from ...config import DEFAULT_CITY
from .base import Source

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_EVENTS_JSON = re.compile(r"events_data\s*=\s*(\[.*?\]);", re.S)

# AllEvents category slugs -> CityPulse category slugs.
CATEGORY_MAP = {
    "sports": "sports",
    "music": "music",
    "concerts": "music",
    "parties": "music",
    "business": "business",
    "conferences": "business",
    "workshops": "education",
    "seminars": "education",
    "courses": "education",
    "festivals": "cultural",
    "art": "cultural",
    "exhibitions": "cultural",
    "theatre": "cultural",
    "entertainment": "cultural",
    "religion": "religious",
    "spirituality": "religious",
    "food-drinks": "food",
    "food": "food",
    "cooking": "food",
    "kids": "family",
    "family": "family",
    "trips-adventures": "travel",
    "adventures": "travel",
    "trips": "travel",
    "outdoor": "travel",
}


class AllEventsSource(Source):
    name = "allevents"

    # The /all page caps its embedded payload, so we also crawl the category
    # pages (which surface additional listings) and the twin city.
    def _pages(self) -> list[str]:
        city = DEFAULT_CITY.lower()
        return [
            f"{city}/all",
            f"{city}/sports",
            f"{city}/music",
            f"{city}/entertainment",
            f"{city}/workshops",
            f"{city}/parties",
            f"{city}/festivals",
            f"{city}/food-drinks",
            "rawalpindi/all",
        ]

    @staticmethod
    def _extract(html: str) -> list[dict]:
        best: list = []
        for block in _EVENTS_JSON.findall(html):
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list) and len(parsed) > len(best):
                best = parsed
        return [p for p in best if isinstance(p, dict)]

    def fetch(self) -> list[dict]:
        seen: dict[str, dict] = {}
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            for page in self._pages():
                try:
                    resp = client.get(f"https://allevents.in/{page}")
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("AllEvents fetch failed for %s: %s", page, exc)
                    continue
                for payload in self._extract(resp.text):
                    key = str(payload.get("event_id") or payload.get("event_url") or id(payload))
                    if key not in seen:
                        seen[key] = payload
        if not seen:
            log.warning("AllEvents: no embedded events_data payloads found (page layout changed?)")
        return list(seen.values())

    @staticmethod
    def _epoch(value) -> str | None:
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return None
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    def map_raw(self, p: dict) -> dict:
        venue = p.get("venue") or {}
        tickets = p.get("tickets") or {}
        organizer = p.get("organizer") or {}
        categories = p.get("categories") or []
        hint = ""
        for cat in categories:
            if str(cat).lower() in CATEGORY_MAP:
                hint = CATEGORY_MAP[str(cat).lower()]
                break

        def _float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        book_url = tickets.get("ticket_url") or p.get("event_url") or p.get("share_url") or ""
        return {
            "title": p.get("eventname_raw") or p.get("eventname") or "",
            "description": p.get("short_description") or "",
            "category_hint": hint,
            "start_time": self._epoch(p.get("start_time")),
            "end_time": self._epoch(p.get("end_time")),
            "venue_name": p.get("location_raw") or p.get("location") or venue.get("full_address", ""),
            "address": venue.get("full_address") or venue.get("street", ""),
            "city": venue.get("city") or DEFAULT_CITY,
            "latitude": _float(venue.get("latitude")),
            "longitude": _float(venue.get("longitude")),
            "price_min": None,
            "price_max": None,
            "currency": "PKR",
            "is_free": False,
            "image_url": p.get("banner_url") or p.get("thumb_url_large") or p.get("thumb_url") or "",
            "source_url": book_url,
            "external_id": str(p.get("event_id") or ""),
            "organizer_name": (organizer.get("name") or "").strip(),
        }
