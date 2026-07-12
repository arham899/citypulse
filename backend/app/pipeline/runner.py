"""Ingestion pipeline orchestrator.

fetch (per source) -> staging (raw_events) -> normalize -> dedupe -> upsert.
Run manually with `python -m app.pipeline.runner` or on a schedule via the
in-process scheduler (see main.py lifespan).
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import SessionLocal, engine, Base
from ..models import Category, Event, IngestRun, Organizer, RawEvent, Venue
from .categorize import CATEGORIES
from .dedupe import fingerprint, is_duplicate
from .normalize import normalize
from .sources import ALL_SOURCES

log = logging.getLogger(__name__)


def ensure_categories(db: Session) -> dict[str, Category]:
    existing = {c.slug: c for c in db.scalars(select(Category))}
    for slug, name, icon in CATEGORIES:
        if slug not in existing:
            cat = Category(slug=slug, name=name, icon=icon)
            db.add(cat)
            existing[slug] = cat
    db.flush()
    return existing


def _get_or_create_venue(db: Session, record: dict) -> Venue | None:
    name = record["venue_name"]
    if not name:
        return None
    venue = db.scalar(select(Venue).where(func.lower(Venue.name) == name.lower(), Venue.city == record["city"]))
    if venue is None:
        venue = Venue(name=name, address=record["address"], city=record["city"],
                      latitude=record["latitude"], longitude=record["longitude"])
        db.add(venue)
        db.flush()
    return venue


def _get_or_create_organizer(db: Session, name: str) -> Organizer | None:
    if not name:
        return None
    org = db.scalar(select(Organizer).where(func.lower(Organizer.name) == name.lower()))
    if org is None:
        org = Organizer(name=name)
        db.add(org)
        db.flush()
    return org


def _merge_into(existing: Event, record: dict) -> None:
    """Enrich an existing event with fields the new listing knows better."""
    if len(record["description"]) > len(existing.description or ""):
        existing.description = record["description"]
    if not existing.image_url and record["image_url"]:
        existing.image_url = record["image_url"]
    if existing.price_min is None and record["price_min"] is not None:
        existing.price_min = record["price_min"]
        existing.price_max = record["price_max"]
        existing.currency = record["currency"]
    if not existing.source_url and record["source_url"]:
        existing.source_url = record["source_url"]
    if existing.end_time is None and record["end_time"] is not None:
        existing.end_time = record["end_time"]
    if not existing.organizer_name and record["organizer_name"]:
        existing.organizer_name = record["organizer_name"]


def _apply_fields(event: Event, record: dict, categories: dict[str, Category]) -> None:
    event.title = record["title"]
    event.description = record["description"]
    event.category_id = categories[record["category_slug"] or "other"].id
    event.subcategory = record["subcategory"]
    event.start_time = record["start_time"]
    event.end_time = record["end_time"]
    event.venue_name = record["venue_name"]
    event.address = record["address"]
    event.city = record["city"]
    event.latitude = record["latitude"]
    event.longitude = record["longitude"]
    event.price_min = record["price_min"]
    event.price_max = record["price_max"]
    event.currency = record["currency"]
    event.is_free = record["is_free"]
    event.image_url = record["image_url"]
    event.source_url = record["source_url"]
    event.organizer_name = record["organizer_name"]
    event.fingerprint = fingerprint(record["title"], record["start_time"], record["city"])


def _upsert(db: Session, source_name: str, record: dict, categories: dict[str, Category], run: IngestRun) -> None:
    fp = fingerprint(record["title"], record["start_time"], record["city"])

    # 1. Same listing seen before (same source + external id) -> refresh in place.
    if record["external_id"]:
        existing = db.scalar(select(Event).where(Event.source == source_name,
                                                 Event.external_id == record["external_id"]))
        if existing is not None:
            _apply_fields(existing, record, categories)
            run.updated += 1
            return

    # 2. Exact fingerprint from any source -> merge.
    existing = db.scalar(select(Event).where(Event.fingerprint == fp))
    if existing is not None:
        _merge_into(existing, record)
        run.merged_duplicates += 1
        return

    # 3. Fuzzy: same city + same calendar day, similar title, nearby venue.
    day_start = record["start_time"].replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    same_day = db.scalars(select(Event).where(Event.city == record["city"],
                                              Event.start_time >= day_start,
                                              Event.start_time < day_end)).all()
    for candidate in same_day:
        if is_duplicate(record, candidate):
            _merge_into(candidate, record)
            run.merged_duplicates += 1
            return

    # 4. Genuinely new event.
    venue = _get_or_create_venue(db, record)
    organizer = _get_or_create_organizer(db, record["organizer_name"])
    event = Event(source=source_name, external_id=record["external_id"], status="approved",
                  venue_id=venue.id if venue else None,
                  organizer_id=organizer.id if organizer else None)
    _apply_fields(event, record, categories)
    db.add(event)
    run.created += 1


def run_pipeline(db: Session | None = None) -> IngestRun:
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    run = IngestRun()
    db.add(run)
    try:
        categories = ensure_categories(db)
        for source in ALL_SOURCES:
            if not source.enabled():
                log.info("source %s disabled (missing API key), skipping", source.name)
                continue
            try:
                payloads = source.fetch()
            except Exception:
                log.exception("fetch failed for source %s", source.name)
                run.errors += 1
                continue
            for payload in payloads:
                raw = RawEvent(source=source.name,
                               external_id=str(payload.get("id") or payload.get("external_id") or ""),
                               payload=payload)
                db.add(raw)
                run.fetched += 1
                try:
                    record = normalize(source.map_raw(payload))
                    if record is None:
                        raw.error = "unusable: missing title or start time"
                        continue
                    _upsert(db, source.name, record, categories, run)
                    raw.processed = True
                except Exception as exc:
                    log.exception("normalize/upsert failed (%s)", source.name)
                    raw.error = str(exc)
                    run.errors += 1
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        log.info("ingest done: fetched=%s created=%s updated=%s merged=%s errors=%s",
                 run.fetched, run.created, run.updated, run.merged_duplicates, run.errors)
        return run
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Base.metadata.create_all(engine)
    result = run_pipeline()
    print(f"fetched={result.fetched} created={result.created} updated={result.updated} "
          f"merged_duplicates={result.merged_duplicates} errors={result.errors}")
