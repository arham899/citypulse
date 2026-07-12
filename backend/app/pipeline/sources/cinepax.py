"""Cinepax cinema scraper — powers the Movies section.

Cinepax runs Vista cinema software; each cinema's browsing page carries the
full now-showing schedule as server-rendered HTML (film title, poster,
trailer, and exact <time datetime="..."> showtimes with direct ticketing
links). We scrape the twin-city cinemas and emit one event per film per
cinema, refreshed every ingest cycle so the next showtime is always current.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup

from .base import Source

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

PKT = timezone(timedelta(hours=5))

CINEMAS = {
    "0000000011": {
        "name": "Cinepax World Trade Center",
        "address": "World Trade Center, Giga Mall Extension, DHA Phase 2, Islamabad",
        "city": "Islamabad",
        "lat": 33.5231,
        "lng": 73.1560,
    },
    "0000000003": {
        "name": "Cinepax Jinnah Park",
        "address": "Jinnah Park, Rawalpindi",
        "city": "Rawalpindi",
        "lat": 33.5946,
        "lng": 73.0530,
    },
}

MAX_SHOWTIMES_LISTED = 12


def _abs(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url


class CinepaxSource(Source):
    name = "cinepax"

    def fetch(self) -> list[dict]:
        payloads = []
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            for cinema_id, cinema in CINEMAS.items():
                url = f"https://cinepax.com/Browsing/Cinemas/Details/{cinema_id}"
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    log.warning("Cinepax fetch failed for %s: %s", cinema["name"], exc)
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                for film in soup.select("div.film-item"):
                    title_el = film.select_one(".film-title")
                    if not title_el:
                        continue
                    movie_id = film.get("data-movie-id", "")
                    poster_el = film.select_one(".movie-image img")
                    detail_el = film.select_one(".film-header a[href]")
                    sessions = []
                    for time_el in film.select("time[datetime]"):
                        booking = time_el.find_parent("a")
                        sessions.append({
                            "datetime": time_el.get("datetime", ""),
                            "booking_url": _abs(booking.get("href", "")) if booking else "",
                        })
                    if not sessions:
                        continue
                    payloads.append({
                        "cinema_id": cinema_id,
                        "cinema": cinema,
                        "movie_id": movie_id,
                        "title": title_el.get_text(strip=True),
                        "poster": _abs(poster_el.get("src", "")) if poster_el else "",
                        "detail_url": _abs(detail_el.get("href", "")) if detail_el else url,
                        "sessions": sessions,
                    })
        return payloads

    def map_raw(self, p: dict) -> dict:
        cinema = p.get("cinema") or {}
        now = datetime.now(PKT)
        parsed = []
        for s in p.get("sessions", []):
            try:
                dt = datetime.fromisoformat(s["datetime"]).replace(tzinfo=PKT)
            except (KeyError, ValueError):
                continue
            parsed.append((dt, s.get("booking_url", "")))
        parsed.sort(key=lambda x: x[0])
        upcoming = [s for s in parsed if s[0] >= now] or parsed
        if not upcoming:
            return {"title": "", "start_time": None}
        next_show, next_booking = upcoming[0]

        lines = [f"Now showing at {cinema.get('name', 'Cinepax')}.", "", "Showtimes:"]
        for dt, _ in upcoming[:MAX_SHOWTIMES_LISTED]:
            lines.append(dt.strftime("%a %d %b — %I:%M %p"))
        if len(upcoming) > MAX_SHOWTIMES_LISTED:
            lines.append(f"…and {len(upcoming) - MAX_SHOWTIMES_LISTED} more shows.")

        # Request a bigger poster from the Vista CDN.
        poster = (p.get("poster") or "").replace("width=121", "width=500").replace("height=180", "height=740")
        return {
            "title": p.get("title", ""),
            "description": "\n".join(lines),
            "category_hint": "movies",
            "start_time": next_show.isoformat(),
            "end_time": None,
            "venue_name": cinema.get("name", ""),
            "address": cinema.get("address", ""),
            "city": cinema.get("city", "Islamabad"),
            "latitude": cinema.get("lat"),
            "longitude": cinema.get("lng"),
            "price_min": None,
            "price_max": None,
            "currency": "PKR",
            "is_free": False,
            "image_url": poster,
            "source_url": next_booking or p.get("detail_url", ""),
            "external_id": f"{p.get('cinema_id', '')}:{p.get('movie_id', '')}",
            "organizer_name": "Cinepax Cinemas",
        }
