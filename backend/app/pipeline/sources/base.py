"""Source connector contract.

Each connector fetches raw payloads from one upstream (API, scraper, or
curated file) and knows how to map its own payload format into the unified
event dict consumed by the normalization layer.

Unified dict keys:
    title, description, category_hint, start_time (ISO str), end_time,
    venue_name, address, city, latitude, longitude, price_min, price_max,
    currency, is_free, image_url, source_url, external_id, organizer_name
"""

from abc import ABC, abstractmethod


class Source(ABC):
    name: str = "base"

    def enabled(self) -> bool:
        return True

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Return raw payloads exactly as received upstream."""

    @abstractmethod
    def map_raw(self, payload: dict) -> dict:
        """Map one raw payload to the unified event dict."""
