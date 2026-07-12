"""Direct organizer submissions — the webhook/manual entry path of the
ingestion layer. Submissions land in the moderation queue as `pending` and
only appear in the public feed once an admin approves them."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Category, Event, Organizer, RawEvent
from ..pipeline.dedupe import fingerprint
from ..pipeline.normalize import normalize
from ..schemas import EventOut, SubmissionIn

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("", response_model=EventOut, status_code=201)
def submit_event(body: SubmissionIn, db: Session = Depends(get_db)):
    payload = body.model_dump(mode="json")
    db.add(RawEvent(source="organizer_submission", payload=payload, processed=True))

    record = normalize({
        **payload,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "category_hint": "",
        "source_url": body.ticket_url,
        "external_id": "",
    })
    if record is None:
        raise HTTPException(status_code=422, detail="Submission is missing a usable title or start time")

    category_slug = body.category_slug or record["category_slug"] or "other"
    category = db.scalar(select(Category).where(Category.slug == category_slug))
    if category is None:
        category = db.scalar(select(Category).where(Category.slug == "other"))

    organizer = db.scalar(select(Organizer).where(Organizer.name == body.organizer_name))
    if organizer is None:
        organizer = Organizer(name=body.organizer_name, email=body.organizer_email)
        db.add(organizer)
        db.flush()

    event = Event(
        title=record["title"],
        description=record["description"],
        category_id=category.id if category else None,
        subcategory=record["subcategory"],
        start_time=record["start_time"],
        end_time=record["end_time"],
        venue_name=record["venue_name"],
        address=record["address"],
        city=record["city"],
        latitude=record["latitude"],
        longitude=record["longitude"],
        price_min=record["price_min"],
        price_max=record["price_max"],
        currency=record["currency"],
        is_free=record["is_free"],
        image_url=record["image_url"],
        source="organizer_submission",
        source_url=body.ticket_url,
        organizer_id=organizer.id,
        organizer_name=body.organizer_name,
        status="pending",
        fingerprint=fingerprint(record["title"], record["start_time"], record["city"]),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
