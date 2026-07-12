"""Duplicate detection.

Two layers:
1. Exact fingerprint — normalized title + local date + city. Catches the same
   listing re-fetched from the same or another source.
2. Fuzzy match — for events on the same date in the same city, title
   similarity (difflib ratio) plus venue proximity. Catches "Qawwali Night at
   PNCA" vs "Qawwali Night - Pakistan National Council of the Arts".

The fuzzy scorer is intentionally isolated so it can be replaced with an
embedding-based similarity model later.
"""

import hashlib
import re
from difflib import SequenceMatcher

from ..geo import haversine_km

_STOPWORDS = {"the", "a", "an", "at", "in", "of", "and", "&", "-", "with", "by", "for", "live"}
_NONWORD = re.compile(r"[^a-z0-9\s]")

TITLE_SIMILARITY_THRESHOLD = 0.82
VENUE_PROXIMITY_KM = 1.5


def normalize_title(title: str) -> str:
    text = _NONWORD.sub(" ", title.lower())
    words = [w for w in text.split() if w not in _STOPWORDS]
    return " ".join(words)


def fingerprint(title: str, start_time, city: str) -> str:
    key = f"{normalize_title(title)}|{start_time.date().isoformat()}|{city.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def titles_similar(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def is_duplicate(candidate: dict, existing) -> bool:
    """candidate: normalized dict; existing: Event ORM row on the same date/city."""
    sim = titles_similar(candidate["title"], existing.title)
    if sim < TITLE_SIMILARITY_THRESHOLD:
        return False
    # Same-ish title on the same date: confirm with location if both sides have it.
    lat, lng = candidate.get("latitude"), candidate.get("longitude")
    if lat is not None and lng is not None and existing.latitude is not None and existing.longitude is not None:
        return haversine_km(lat, lng, existing.latitude, existing.longitude) <= VENUE_PROXIMITY_KM
    return True
