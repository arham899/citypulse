import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import INGEST_INTERVAL_MINUTES, IS_SERVERLESS
from .db import Base, SessionLocal, engine
from .models import Event  # noqa: F401 — ensure models are registered
from .pipeline.runner import ensure_categories, run_pipeline
from .routers import admin, events, meta, submissions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("citypulse")


async def _ingest_loop():
    """Regular ingestion cycles keep the feed fresh (NFR: freshness)."""
    while True:
        await asyncio.sleep(INGEST_INTERVAL_MINUTES * 60)
        try:
            await asyncio.to_thread(run_pipeline)
        except Exception:
            log.exception("scheduled ingest failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_categories(db)
        db.commit()
        empty = db.query(Event).count() == 0
    if IS_SERVERLESS:
        # Serverless: no long-lived process, so no in-process scheduler and no
        # blocking boot ingest (cold starts must stay fast). Freshness comes
        # from an external cron hitting POST /api/admin/ingest every 20 min.
        yield
        return
    if empty:
        # First boot on an empty database: run one ingest cycle so the feed
        # is populated immediately.
        log.info("empty database — running initial ingest")
        await asyncio.to_thread(run_pipeline)
    task = asyncio.create_task(_ingest_loop())
    yield
    task.cancel()


app = FastAPI(
    title="CityPulse API",
    description="Location-aware city events aggregator — Islamabad launch.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(meta.router)
app.include_router(submissions.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "citypulse-api"}
