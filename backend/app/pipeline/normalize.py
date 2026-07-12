"""Normalization layer: unified dict -> validated, geocoded, categorized record."""

import logging
from datetime import datetime, timedelta, timezone

from .categorize import categorize
from .geocode import geocode

log = logging.getLogger(__name__)

PKT = timezone(timedelta(hours=5))

# Map upstream category hints (e.g. Ticketmaster segments) onto our slugs.
# Our own slugs are included identity-mapped so sources that pre-map (like
# AllEvents) pass straight through.
HINT_MAP = {
    "sports": "sports",
    "music": "music",
    "education": "education",
    "business": "business",
    "cultural": "cultural",
    "religious": "religious",
    "food": "food",
    "family": "family",
    "travel": "travel",
    "movies": "movies",
    "international": "international",
    "arts & theatre": "cultural",
    "arts and theatre": "cultural",
    "film": "movies",
    "miscellaneous": "other",
}


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    # Naive timestamps from local sources are assumed to be Pakistan time.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PKT)
    return dt.astimezone(timezone.utc)


def normalize(unified: dict) -> dict | None:
    """Validate and enrich a unified event dict. Returns None if unusable."""
    title = (unified.get("title") or "").strip()
    start = _parse_dt(unified.get("start_time"))
    # Quality gate: drop unusable rows and junk listings ("hp", "..") that
    # occasionally appear on aggregator sites.
    if len(title) < 4 or start is None:
        return None

    end = _parse_dt(unified.get("end_time"))
    if end and end < start:
        end = None

    city = (unified.get("city") or "Islamabad").strip().title()
    description = (unified.get("description") or "").strip()

    lat, lng = unified.get("latitude"), unified.get("longitude")
    if lat is None or lng is None:
        lat, lng, _exact = geocode(unified.get("venue_name", ""), unified.get("address", ""), city)

    hint = (unified.get("category_hint") or "").strip().lower()
    category_slug = HINT_MAP.get(hint) or ""
    subcategory = ""
    if not category_slug:
        category_slug, subcategory = categorize(title, description)

    price_min, price_max = unified.get("price_min"), unified.get("price_max")
    is_free = bool(unified.get("is_free")) or (price_min == 0 and (price_max or 0) == 0)

    return {
        "title": title,
        "description": description,
        "category_slug": category_slug,
        "subcategory": subcategory,
        "start_time": start,
        "end_time": end,
        "venue_name": (unified.get("venue_name") or "").strip(),
        "address": (unified.get("address") or "").strip(),
        "city": city,
        "latitude": lat,
        "longitude": lng,
        "price_min": price_min,
        "price_max": price_max,
        "currency": unified.get("currency") or "PKR",
        "is_free": is_free,
        "image_url": unified.get("image_url") or "",
        "source_url": unified.get("source_url") or "",
        "external_id": unified.get("external_id") or "",
        "organizer_name": (unified.get("organizer_name") or "").strip(),
    }
