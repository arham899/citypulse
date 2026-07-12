# CityPulse — City Events Aggregator

A location-aware event discovery platform for **Islamabad** (launch city). CityPulse aggregates **real, live events** from multiple sources — the AllEvents.in and Eventbrite scrapers, optional ticketing APIs, and direct organizer submissions — normalizes them into a unified schema, deduplicates cross-source listings, and serves them through a filterable, map-driven web app. The feed refreshes automatically **every 20 minutes**.

> *"What is happening in my city right now, this week, or this weekend?"* — one feed, every category.

## Architecture

```
Data Sources                Ingestion            Normalization             Core            API / Clients
─────────────               ─────────            ─────────────             ────            ─────────────
AllEvents.in      ┐
(embedded JSON)   ├──►  20-min scheduled   ──►  unified schema map   ──►  SQLite     ──►  FastAPI REST
Eventbrite public │     scrapers/pollers        geocoding                 (PostGIS-       /api/events …
pages (JSON-LD)   │     ↓                       auto-categorization       ready               │
Ticketmaster API  ┘     raw_events staging      fuzzy dedup & merge       schema)       React web app
Organizer submissions ──► moderation queue ─────────────────────────────────┘           (feed · map · search)
```

- **Ingestion layer** (`backend/app/pipeline/sources/`) — each connector fetches raw payloads and maps its own format to a unified dict:
  - **AllEvents.in** — extracts the JSON event payload embedded in the listing pages (venue coordinates, organizer, images, ticket links). Crawls the main page **plus the sports, music, entertainment, workshops, parties, festivals, and food category pages and Rawalpindi** for maximum capture. No key needed.
  - **Eventbrite** — parses schema.org JSON-LD from the public city search page, then enriches each event from its own page (exact times, prices). Online-only and out-of-city listings are filtered out. No key needed.
  - **Cinepax (Movies)** — scrapes the twin-city Cinepax cinemas (World Trade Center Islamabad, Jinnah Park Rawalpindi) for now-showing films with exact showtimes; the Book link goes straight to seat selection for the next show. No key needed.
  - **Meta Graph (Facebook/Instagram)** — pulls upcoming events from configured Facebook pages via the official Graph API when `META_ACCESS_TOKEN` + `META_PAGE_IDS` are set. Anonymous scraping of Facebook, Instagram, and LinkedIn is blocked by login walls and bot detection (verified: FB returns 404, IG 429, LinkedIn an authwall), so the token-based API is the only reliable route.
  - **Ticketmaster** — Discovery API poller, activates when `TICKETMASTER_API_KEY` is set.
- **Staging** — every raw payload is stored verbatim in `raw_events` before processing, so the pipeline is replayable and debuggable.
- **Normalization** (`pipeline/normalize.py`) — validates (with a junk-listing quality gate), converts times to UTC (naive local times assumed PKT), fills missing coordinates via a curated Islamabad venue/sector gazetteer, and auto-categorizes with a word-boundary keyword scorer (drop-in replaceable by an ML classifier).
- **Dedup** (`pipeline/dedupe.py`) — three layers: same source+external id (refresh in place), exact fingerprint (normalized title + date + city), and fuzzy title similarity + venue proximity for cross-source duplicates. Duplicate listings are *merged* — the richer description, missing prices, and image are kept.
- **Scheduler** — an in-process loop runs a full ingest cycle every `INGEST_INTERVAL_MINUTES` (**default 20**); an empty database triggers an immediate first ingest on API startup. `POST /api/admin/ingest` triggers a cycle on demand.

## Quick start

### Backend (Python 3.11+)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env          # optional — sensible defaults apply
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

On first boot the API creates the schema, scrapes live sources (~75 real Islamabad/Rawalpindi events including current cinema showings), and starts the 20-minute refresh scheduler. Interactive API docs: http://localhost:8000/docs

Run the pipeline manually at any time:

```powershell
.\.venv\Scripts\python -m app.pipeline.runner
```

### Frontend (Node 18+)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the dev server proxies `/api` to the backend on port 8000.

## Web app

- **Feed** — chronological cards with image, date badge, color-coded category, time, venue, price, and a direct **Book** link to the event's real booking/organizer page; skeleton loaders and "Load more" pagination. The UI is emoji-free — all iconography is inline SVG.
- **Filters** — category chips (sports, music, education, business, cultural, religious, food, family, travel & outdoors, **movies**, international), date presets (today / tomorrow / this weekend / this week), free-only, and **Near me** with a 2–25 km radius (uses browser geolocation, falls back to the city centre if denied).
- **Map view** — toggle the same filtered result set onto a dark Leaflet/CARTO map.
- **Search** — full-text over titles, descriptions, venues, and organizers (debounced).
- **Event detail** — full description, mini-map, directions link, share, and outbound **Book / RSVP** link to the source ticketing page (v1 links out; no in-app ticketing).
- **Submit event** (`/submit`) — organizer submissions enter the moderation queue as `pending`.
- **Admin** (`/admin`) — enter the admin key (`ADMIN_API_KEY`, default `change-me`) to review, approve, or reject pending submissions.

## API reference

| Endpoint | Description |
|---|---|
| `GET /api/events` | Filterable feed. Params: `q`, `category`, `city`, `date_filter` (today/tomorrow/weekend/week/custom), `start`, `end`, `lat`+`lng`+`radius_km`, `free_only`, `sort` (date/distance), `page`, `page_size` |
| `GET /api/events/{id}` | Event detail |
| `GET /api/categories` · `GET /api/cities` | Filter vocabularies |
| `GET /api/stats` | Totals by category/source, pending count, last ingest time |
| `POST /api/submissions` | Organizer submission → moderation queue |
| `GET /api/admin/pending` | Moderation queue *(X-Admin-Key header)* |
| `POST /api/admin/events/{id}/approve` / `…/reject` | Moderate a submission *(X-Admin-Key)* |
| `POST /api/admin/ingest` | Trigger an ingest cycle now *(X-Admin-Key)* |

Distance is computed with a bounding-box SQL pre-filter + haversine, and each geo result includes `distance_km`.

## Configuration (`backend/.env`)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | local SQLite file | Point at `postgresql+psycopg://…` for Postgres/PostGIS |
| `TICKETMASTER_API_KEY` | empty | Optional API connector, activates when set |
| `META_ACCESS_TOKEN`, `META_PAGE_IDS` | empty | Facebook/Instagram page events via the official Graph API |
| `DEFAULT_CITY` | `Islamabad` | City scraped/polled by all sources |
| `INGEST_INTERVAL_MINUTES` | `20` | Feed refresh cycle |
| `ADMIN_API_KEY` | `change-me` | Moderation auth — change it |

## Deploying to Vercel

The repo is Vercel-ready: the React app builds to static assets and the FastAPI backend runs as a Python serverless function ([api/index.py](api/index.py), wired up in [vercel.json](vercel.json)).

1. **Import the repo** at https://vercel.com/new (framework preset: *Other* — `vercel.json` drives the build).
2. **Add a database** — serverless instances don't share a filesystem, so SQLite won't persist. Create a free Postgres (Vercel Postgres / Neon) and set the env var:
   `DATABASE_URL = postgresql+psycopg://…` (also set `ADMIN_API_KEY` to something secret).
3. **Populate + keep fresh** — the serverless build skips the in-process scheduler, so the 20-minute refresh comes from the included GitHub Actions workflow ([.github/workflows/refresh-feed.yml](.github/workflows/refresh-feed.yml)). Add two repository secrets on GitHub: `CITYPULSE_URL` (your Vercel URL) and `ADMIN_API_KEY` (same value as on Vercel), then run the workflow once manually to do the first ingest.

## Scaling path (built-in seams)

- **SQLite → PostgreSQL + PostGIS**: swap `DATABASE_URL`; replace the haversine filter in `routers/events.py` with `ST_DWithin` for index-backed proximity queries.
- **Keyword categorizer → ML classifier**: `pipeline/categorize.py` is a single pure function.
- **difflib dedup → embedding similarity**: `pipeline/dedupe.py` isolates the scorer.
- **More sources**: add a class implementing `fetch()` + `map_raw()` in `pipeline/sources/` and register it in `ALL_SOURCES`; use Playwright inside `fetch()` for JS-heavy sites.
- **LIKE search → Meilisearch/Elasticsearch** behind the same `q` param.
- **v2**: user accounts, saved events, push notifications, personalized ranking, organizer dashboard — the `User`/`SavedEvent`/`Subscription` entities and the pending/approved status machinery are the extension points.
