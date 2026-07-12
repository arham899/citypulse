"""Moderation endpoints for administrators.

Auth is a shared header key (X-Admin-Key) for v1; replace with real user
accounts + roles in v2.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import ADMIN_API_KEY
from ..db import get_db
from ..models import Event
from ..pipeline.runner import run_pipeline
from ..schemas import EventOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(x_admin_key: str = Header(default="")):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.get("/pending", response_model=list[EventOut], dependencies=[Depends(require_admin)])
def pending_queue(db: Session = Depends(get_db)):
    return db.scalars(
        select(Event).options(joinedload(Event.category))
        .where(Event.status == "pending").order_by(Event.created_at)
    ).all()


def _moderate(db: Session, event_id: int, status: str) -> Event:
    event = db.get(Event, event_id, options=[joinedload(Event.category)])
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = status
    db.commit()
    db.refresh(event)
    return event


@router.post("/events/{event_id}/approve", response_model=EventOut, dependencies=[Depends(require_admin)])
def approve(event_id: int, db: Session = Depends(get_db)):
    return _moderate(db, event_id, "approved")


@router.post("/events/{event_id}/reject", response_model=EventOut, dependencies=[Depends(require_admin)])
def reject(event_id: int, db: Session = Depends(get_db)):
    return _moderate(db, event_id, "rejected")


@router.post("/ingest", dependencies=[Depends(require_admin)])
def trigger_ingest(db: Session = Depends(get_db)):
    run = run_pipeline(db)
    return {"fetched": run.fetched, "created": run.created, "updated": run.updated,
            "merged_duplicates": run.merged_duplicates, "errors": run.errors}
