"""Vercel serverless entrypoint.

Exposes the FastAPI application from backend/ as an ASGI function. All /api/*
requests are rewritten here (see vercel.json); the React build is served
statically alongside it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402,F401
