"""Ticketmaster Discovery API v2 poller — covers international/commercial events.

Skipped automatically when TICKETMASTER_API_KEY is not configured.
"""

import logging

import httpx

from ...config import DEFAULT_CITY, TICKETMASTER_API_KEY
from .base import Source

log = logging.getLogger(__name__)

API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"


class TicketmasterSource(Source):
    name = "ticketmaster"

    def enabled(self) -> bool:
        return bool(TICKETMASTER_API_KEY)

    def fetch(self) -> list[dict]:
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "city": DEFAULT_CITY,
            "sort": "date,asc",
            "size": 100,
        }
        try:
            resp = httpx.get(API_URL, params=params, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("Ticketmaster fetch failed: %s", exc)
            return []
        return resp.json().get("_embedded", {}).get("events", [])

    def map_raw(self, p: dict) -> dict:
        venues = p.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}
        location = venue.get("location", {})
        prices = p.get("priceRanges", [{}])
        price = prices[0] if prices else {}
        images = p.get("images", [])
        classifications = p.get("classifications", [{}])
        segment = (classifications[0].get("segment", {}) or {}).get("name", "") if classifications else ""
        return {
            "title": p.get("name", ""),
            "description": p.get("info", "") or p.get("pleaseNote", ""),
            "category_hint": segment,
            "start_time": p.get("dates", {}).get("start", {}).get("dateTime", ""),
            "end_time": None,
            "venue_name": venue.get("name", ""),
            "address": (venue.get("address", {}) or {}).get("line1", ""),
            "city": (venue.get("city", {}) or {}).get("name", DEFAULT_CITY),
            "latitude": float(location["latitude"]) if location.get("latitude") else None,
            "longitude": float(location["longitude"]) if location.get("longitude") else None,
            "price_min": price.get("min"),
            "price_max": price.get("max"),
            "currency": price.get("currency", "USD"),
            "is_free": False,
            "image_url": images[0]["url"] if images else "",
            "source_url": p.get("url", ""),
            "external_id": p.get("id", ""),
            "organizer_name": (p.get("promoter", {}) or {}).get("name", ""),
        }
