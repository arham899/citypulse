from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..db import get_db
from ..geo import bounding_box, haversine_km
from ..models import Category, Event
from ..schemas import EventListOut, EventOut

router = APIRouter(prefix="/api/events", tags=["events"])

PKT = timezone(timedelta(hours=5))
GEO_SCAN_CAP = 2000  # max candidate rows pulled for in-Python distance filtering


def _date_window(date_filter: str | None, start: datetime | None, end: datetime | None):
    """Resolve a date preset into a UTC (window_start, window_end) pair.
    Presets are computed in Pakistan local time so 'today' means the user's today."""
    now_local = datetime.now(PKT)
    today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_filter == "today":
        return now_local, today + timedelta(days=1)
    if date_filter == "tomorrow":
        return today + timedelta(days=1), today + timedelta(days=2)
    if date_filter == "weekend":
        # Upcoming Saturday 00:00 through Sunday 24:00; if already the weekend,
        # from now to the end of Sunday.
        days_to_sat = (5 - today.weekday()) % 7
        sat = today + timedelta(days=days_to_sat)
        if today.weekday() >= 5:  # already Sat/Sun
            return now_local, today + timedelta(days=7 - today.weekday())
        return sat, sat + timedelta(days=2)
    if date_filter == "week":
        return now_local, now_local + timedelta(days=7)
    if date_filter == "custom" or start or end:
        return start or now_local, end
    return now_local, None  # default: all upcoming


@router.get("", response_model=EventListOut)
def list_events(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Full-text search over title, description, venue, organizer"),
    category: str | None = Query(None, description="Category slug"),
    city: str | None = None,
    date_filter: str | None = Query(None, pattern="^(today|tomorrow|weekend|week|custom)$"),
    start: datetime | None = None,
    end: datetime | None = None,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float | None = Query(None, gt=0, le=100),
    free_only: bool = False,
    sort: str = Query("date", pattern="^(date|distance)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = (
        select(Event)
        .options(joinedload(Event.category))
        .where(Event.status == "approved")
    )

    window_start, window_end = _date_window(date_filter, start, end)
    if window_start:
        # An event still counts while it is running (multi-day festivals).
        stmt = stmt.where(or_(Event.start_time >= window_start.astimezone(timezone.utc),
                              Event.end_time >= window_start.astimezone(timezone.utc)))
    if window_end:
        stmt = stmt.where(Event.start_time < window_end.astimezone(timezone.utc))

    if category:
        stmt = stmt.join(Category, Event.category_id == Category.id).where(Category.slug == category)
    if city:
        stmt = stmt.where(func.lower(Event.city) == city.strip().lower())
    if free_only:
        stmt = stmt.where(Event.is_free.is_(True))
    if q:
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(
            func.lower(Event.title).like(term),
            func.lower(Event.description).like(term),
            func.lower(Event.venue_name).like(term),
            func.lower(Event.organizer_name).like(term),
        ))

    geo = lat is not None and lng is not None and radius_km is not None
    if geo:
        min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)
        stmt = stmt.where(Event.latitude.between(min_lat, max_lat),
                          Event.longitude.between(min_lng, max_lng))
        rows = db.scalars(stmt.order_by(Event.start_time).limit(GEO_SCAN_CAP)).all()
        pairs = [(e, haversine_km(lat, lng, e.latitude, e.longitude)) for e in rows]
        pairs = [(e, d) for e, d in pairs if d <= radius_km]
        if sort == "distance":
            pairs.sort(key=lambda p: p[1])
        total = len(pairs)
        page_slice = pairs[(page - 1) * page_size: page * page_size]
        items = []
        for e, d in page_slice:
            out = EventOut.model_validate(e)
            out.distance_km = round(d, 2)
            items.append(out)
    else:
        total = db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = db.scalars(stmt.order_by(Event.start_time)
                          .offset((page - 1) * page_size).limit(page_size)).all()
        items = [EventOut.model_validate(e) for e in rows]

    return EventListOut(items=items, total=total, page=page, page_size=page_size,
                        has_more=page * page_size < total)


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id, options=[joinedload(Event.category)])
    if event is None or event.status == "rejected":
        raise HTTPException(status_code=404, detail="Event not found")
    return event
