import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# On Vercel (serverless) the project filesystem is read-only — fall back to
# /tmp for a per-instance demo DB; real deployments set DATABASE_URL to a
# hosted Postgres (Neon / Vercel Postgres) so all instances share state.
IS_SERVERLESS = bool(os.getenv("VERCEL"))
_default_sqlite = "sqlite:////tmp/citypulse.db" if IS_SERVERLESS else f"sqlite:///{BASE_DIR / 'citypulse.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", _default_sqlite)
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PAGE_IDS = [p.strip() for p in os.getenv("META_PAGE_IDS", "").split(",") if p.strip()]
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Islamabad")
INGEST_INTERVAL_MINUTES = int(os.getenv("INGEST_INTERVAL_MINUTES", "20"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me")

IS_POSTGRES = DATABASE_URL.startswith(("postgresql", "postgres"))
