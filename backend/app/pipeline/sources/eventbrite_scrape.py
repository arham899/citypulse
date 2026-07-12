"""Eventbrite public listing scraper (no API key required).

The public city search page carries a schema.org ItemList of Event objects in
JSON-LD — name, dates, venue with geo coordinates, image, and the canonical
booking URL. The listing only exposes start *dates*, so we fetch each event's
own page (which embeds full JSON-LD with exact times and price offers) and
fall back to the listing data when that fails.
"""

import json
import logging
import re
import time

import httpx

from ...config import DEFAULT_CITY
from .base import Source

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_LD_BLOCK = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S)
DETAIL_FETCH_DELAY_S = 0.4  # stay polite: ~12 detail pages per cycle


def _ld_objects(html: str) -> list[dict]:
    objects = []
    for block in _LD_BLOCK.findall(html):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        objects.extend(data if isinstance(data, list) else [data])
    return [o for o in objects if isinstance(o, dict)]


def _is_event(obj: dict) -> bool:
    t = obj.get("@type", "")
    return t == "Event" or (isinstance(t, list) and "Event" in t) or str(t).endswith("Event")


LOCAL_CITIES = {"islamabad", "rawalpindi"}


def _is_local_in_person(item: dict) -> bool:
    """Eventbrite's city listing mixes in online webinars and events from
    other cities — keep only in-person events actually in the launch market."""
    mode = str(item.get("eventAttendanceMode", ""))
    if "OnlineEventAttendanceMode" in mode:
        return False
    location = item.get("location") or {}
    if location.get("@type") == "VirtualLocation":
        return False
    address = location.get("address") or {}
    locality = str(address.get("addressLocality", "")).strip().lower()
    return locality in LOCAL_CITIES


class EventbriteScrapeSource(Source):
    name = "eventbrite"

    def fetch(self) -> list[dict]:
        url = f"https://www.eventbrite.com/d/pakistan--{DEFAULT_CITY.lower()}/events/"
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("Eventbrite listing fetch failed: %s", exc)
            return []

        listed = []
        for obj in _ld_objects(resp.text):
            for entry in obj.get("itemListElement", []) or []:
                item = entry.get("item", entry) if isinstance(entry, dict) else None
                if isinstance(item, dict) and _is_event(item) and _is_local_in_person(item):
                    listed.append(item)

        # Enrich with each event page's own JSON-LD (exact times, offers).
        payloads = []
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            for item in listed:
                merged = dict(item)
                page_url = item.get("url", "")
                if page_url:
                    try:
                        detail = client.get(page_url)
                        detail.raise_for_status()
                        for obj in _ld_objects(detail.text):
                            if _is_event(obj):
                                merged.update({k: v for k, v in obj.items() if v})
                                break
                        time.sleep(DETAIL_FETCH_DELAY_S)
                    except httpx.HTTPError as exc:
                        log.info("Eventbrite detail fetch failed (%s): %s", page_url, exc)
                payloads.append(merged)
        return payloads

    def map_raw(self, p: dict) -> dict:
        location = p.get("location") or {}
        address = location.get("address") or {}
        geo = location.get("geo") or {}
        offers = p.get("offers") or []
        if isinstance(offers, dict):
            offers = [offers]
        prices = []
        currency = "PKR"
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            for key in ("price", "lowPrice", "highPrice"):
                try:
                    prices.append(float(offer[key]))
                except (KeyError, TypeError, ValueError):
                    pass
            currency = offer.get("priceCurrency", currency)

        def _float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        image = p.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        return {
            "title": p.get("name", ""),
            "description": p.get("description", ""),
            "category_hint": "",
            "start_time": p.get("startDate", ""),
            "end_time": p.get("endDate"),
            "venue_name": location.get("name", ""),
            "address": address.get("streetAddress", ""),
            "city": address.get("addressLocality") or DEFAULT_CITY,
            "latitude": _float(geo.get("latitude")),
            "longitude": _float(geo.get("longitude")),
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "currency": currency,
            "is_free": bool(prices) and max(prices) == 0,
            "image_url": image,
            "source_url": p.get("url", ""),
            "external_id": (p.get("url", "").rstrip("/").rsplit("-", 1)[-1] or p.get("name", "")),
            "organizer_name": (p.get("organizer") or {}).get("name", "") if isinstance(p.get("organizer"), dict) else "",
        }
