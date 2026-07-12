from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Category, Event, IngestRun
from ..schemas import CategoryOut, StatsOut

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id)).all()


@router.get("/cities", response_model=list[str])
def list_cities(db: Session = Depends(get_db)):
    rows = db.scalars(select(Event.city).where(Event.status == "approved").distinct().order_by(Event.city)).all()
    return [c for c in rows if c]


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    total = db.scalar(select(func.count(Event.id)).where(Event.status == "approved"))
    upcoming = db.scalar(select(func.count(Event.id)).where(Event.status == "approved",
                                                            Event.start_time >= now))
    pending = db.scalar(select(func.count(Event.id)).where(Event.status == "pending"))
    by_cat = dict(db.execute(
        select(Category.slug, func.count(Event.id))
        .join(Event, Event.category_id == Category.id)
        .where(Event.status == "approved")
        .group_by(Category.slug)
    ).all())
    by_source = dict(db.execute(
        select(Event.source, func.count(Event.id))
        .where(Event.status == "approved")
        .group_by(Event.source)
    ).all())
    last_run = db.scalar(select(IngestRun.finished_at).order_by(IngestRun.id.desc()).limit(1))
    return StatsOut(total_events=total or 0, upcoming_events=upcoming or 0,
                    pending_submissions=pending or 0, by_category=by_cat,
                    by_source=by_source, last_ingest_at=last_run)
