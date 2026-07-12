from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    icon: str


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: CategoryOut | None
    subcategory: str
    start_time: datetime
    end_time: datetime | None
    venue_name: str
    address: str
    city: str
    latitude: float | None
    longitude: float | None
    price_min: float | None
    price_max: float | None
    currency: str
    is_free: bool
    image_url: str
    source: str
    source_url: str
    organizer_name: str
    status: str
    distance_km: float | None = None

    # SQLite returns naive datetimes; everything we store is UTC, so make
    # that explicit before it reaches JSON (clients parse "Z" correctly).
    @field_validator("start_time", "end_time")
    @classmethod
    def _ensure_utc(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class EventListOut(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    page_size: int
    has_more: bool


class SubmissionIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=10000)
    category_slug: str | None = None
    start_time: datetime
    end_time: datetime | None = None
    venue_name: str = Field(min_length=2, max_length=255)
    address: str = Field(default="", max_length=500)
    city: str = Field(min_length=2, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    is_free: bool = False
    image_url: str = Field(default="", max_length=1000)
    ticket_url: str = Field(default="", max_length=1000)
    organizer_name: str = Field(min_length=2, max_length=255)
    organizer_email: str = Field(default="", max_length=255)


class StatsOut(BaseModel):
    total_events: int
    upcoming_events: int
    pending_submissions: int
    by_category: dict[str, int]
    by_source: dict[str, int]
    last_ingest_at: datetime | None
