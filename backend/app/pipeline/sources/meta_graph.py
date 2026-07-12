"""Facebook / Instagram page events via the official Meta Graph API.

Facebook, Instagram, and LinkedIn hard-block anonymous scraping (login walls
and bot detection on every public surface), so the supported route is the
Graph API with a real access token. Configure:

    META_ACCESS_TOKEN  — a (page or app) access token
    META_PAGE_IDS      — comma-separated Facebook page IDs/usernames to pull
                         events from (pages you manage or have granted access)

The connector stays disabled until both are set — no fake data is emitted.
"""

import logging

import httpx

from ...config import DEFAULT_CITY, META_ACCESS_TOKEN, META_PAGE_IDS
from .base import Source

log = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v19.0"
FIELDS = "id,name,description,start_time,end_time,place,cover,ticket_uri,is_online,event_times"


class MetaGraphSource(Source):
    name = "meta"

    def enabled(self) -> bool:
        return bool(META_ACCESS_TOKEN and META_PAGE_IDS)

    def fetch(self) -> list[dict]:
        payloads = []
        with httpx.Client(timeout=30) as client:
            for page_id in META_PAGE_IDS:
                try:
                    resp = client.get(
                        f"{GRAPH}/{page_id}/events",
                        params={"access_token": META_ACCESS_TOKEN, "fields": FIELDS,
                                "time_filter": "upcoming"},
                    )
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("Meta Graph fetch failed for page %s: %s", page_id, exc)
                    continue
                for event in resp.json().get("data", []):
                    if event.get("is_online"):
                        continue
                    event["_page_id"] = page_id
                    payloads.append(event)
        return payloads

    def map_raw(self, p: dict) -> dict:
        place = p.get("place") or {}
        location = place.get("location") or {}
        return {
            "title": p.get("name", ""),
            "description": p.get("description", ""),
            "category_hint": "",
            "start_time": p.get("start_time", ""),
            "end_time": p.get("end_time"),
            "venue_name": place.get("name", ""),
            "address": location.get("street", ""),
            "city": location.get("city") or DEFAULT_CITY,
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "price_min": None,
            "price_max": None,
            "currency": "PKR",
            "is_free": False,
            "image_url": (p.get("cover") or {}).get("source", ""),
            "source_url": p.get("ticket_uri") or f"https://facebook.com/events/{p.get('id', '')}",
            "external_id": str(p.get("id", "")),
            "organizer_name": str(p.get("_page_id", "")),
        }
