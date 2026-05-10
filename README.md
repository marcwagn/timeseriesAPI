# TimeSeries API

A FastAPI service for managing time series data backed by [TimescaleDB](https://www.timescale.com/). Supports multi-user isolation via JWT authentication and PostgreSQL Row-Level Security, with a hypertable optimised for high-throughput time series ingestion and querying.

## Architecture

```
┌────────────────────────────────────────────────────┐
│  Client                                            │
│  POST /auth/token → Bearer <JWT>                   │
└──────────────────────┬─────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼─────────────────────────────┐
│  FastAPI (Uvicorn, async)                          │
│  ┌──────────┐  ┌─────────────────────────────────┐ │
│  │ /auth    │  │ /timeseries  (JWT required)      │ │
│  └──────────┘  └─────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────┐ │
│  │ Service layer  (business logic)               │ │
│  └───────────────────────────────────────────────┘ │
└──────────────────────┬─────────────────────────────┘
                       │ asyncpg (async SQLAlchemy)
┌──────────────────────▼─────────────────────────────┐
│  TimescaleDB (PostgreSQL 15)                       │
│  ┌──────────┐  ┌───────────────────────────────┐  │
│  │ users    │  │ timeseries_data  (hypertable)  │  │
│  └──────────┘  │  partitioned by day + series   │  │
│  ┌──────────┐  └───────────────────────────────┘  │
│  │timeseries│  Row-Level Security: owner_id = me   │
│  └──────────┘                                      │
└────────────────────────────────────────────────────┘
```

Two database roles are used:

| Role | Privileges | Used for |
|---|---|---|
| `postgres` | Superuser | Schema migrations on startup |
| `app_user` | DML only (SELECT/INSERT/UPDATE/DELETE) | All application queries |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- **For local development only:** Python 3.13+ and [uv](https://docs.astral.sh/uv/)

## Quick Start (Docker)

```bash
# 1. Generate a secret key and write it to the root .env
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env

# 2. Start services
docker compose up --build

# API is available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

> Docker Compose reads `.env` from the project root automatically.
> See [.env.example](.env.example) for the expected format.

## Local Development

```bash
# 1. Create backend/src/.env from the root example, then set DSN to localhost
cp .env.example backend/src/.env
# Edit backend/src/.env: set TIMESCALE_DSN=localhost:5432/timeseries_db and SECRET_KEY

# 2. Install dependencies
cd backend
uv sync

# 3. Start TimescaleDB only
docker compose up postgres -d

# 4. Run the API with hot-reload
uv run uvicorn src.main:app --reload
```

## Running Tests

```bash
cd backend

# Start a test database (or point .env.test at an existing instance)
docker compose up postgres -d

# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing
```

Tests use a dedicated database (`timeseries_test`) and truncate tables between each test function.

## API Reference

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/token` | Obtain a JWT access token |
| `GET` | `/health` | Liveness check |

**Register:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "secret"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/token \
  -F "username=alice" -F "password=secret"
# → {"access_token": "<JWT>", "token_type": "bearer"}
```

All `/timeseries` endpoints require the header:
```
Authorization: Bearer <access_token>
```

### Time Series

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/timeseries/` | List all series owned by the authenticated user |
| `POST` | `/timeseries/` | Create a series (optionally with initial data) |
| `GET` | `/timeseries/{id}` | Fetch series data with optional time-range filtering |
| `POST` | `/timeseries/{id}/data` | Append data points to an existing series |
| `DELETE` | `/timeseries/{id}` | Delete a series and all its data |

**Create a series with initial data:**
```bash
curl -X POST http://localhost:8000/timeseries/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "temperature",
    "data": [
      {"timestamp": "2024-01-01T00:00:00Z", "value": 21.5, "status": "W"},
      {"timestamp": "2024-01-01T00:15:00Z", "value": 21.8, "status": "V"}
    ]
  }'
```

**Data point status codes:**

| Code | Meaning |
|------|---------|
| `W` | Wahr — verified/final value |
| `V` | Vorläufig — preliminary value |
| `E` | Ersatz — substitute/estimated value |

**Fetch with time-range filtering and pagination:**
```bash
# First page
curl "http://localhost:8000/timeseries/1?after=2024-01-01T00:00:00Z&before=2024-02-01T00:00:00Z&limit=1000" \
  -H "Authorization: Bearer <token>"

# Next page — use next_cursor from the response as the 'after' value
curl "http://localhost:8000/timeseries/1?after=<next_cursor>&limit=1000" \
  -H "Authorization: Bearer <token>"
```

The response includes a `next_cursor` field (the timestamp of the last returned point). When `next_cursor` is `null`, all data has been fetched.

**List series (paginated):**
```bash
curl "http://localhost:8000/timeseries/?offset=0&limit=50" \
  -H "Authorization: Bearer <token>"
```

## Environment Variables

Create `backend/src/.env` for local development:

```dotenv
APP_NAME=TimescaleAPIProject

# Application database credentials (DML only)
TIMESCALE_USER=app_user
TIMESCALE_PASSWORD=app_password
TIMESCALE_DSN=localhost:5432/timeseries_db

# Migration credentials (superuser, used only on startup)
MIGRATION_USER=postgres
MIGRATION_PASSWORD=postgres

# JWT
SECRET_KEY=<output of: openssl rand -hex 32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

LOG_LEVEL=DEBUG
```

| Variable | Required | Description |
|----------|----------|-------------|
| `TIMESCALE_USER` | Yes | App DB role (DML only) |
| `TIMESCALE_PASSWORD` | Yes | Password for `TIMESCALE_USER` |
| `TIMESCALE_DSN` | Yes | `host:port/database` |
| `MIGRATION_USER` | Yes | Superuser role for schema changes |
| `MIGRATION_PASSWORD` | Yes | Password for `MIGRATION_USER` |
| `SECRET_KEY` | Yes | Random hex string for JWT signing |
| `ALGORITHM` | No | JWT algorithm, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token lifetime, default `30` |
| `LOG_LEVEL` | No | Python log level, default `INFO` |

## Database Schema

```
users
  id            INTEGER PK
  username      VARCHAR(50) UNIQUE
  email         VARCHAR(100) UNIQUE
  hashed_password VARCHAR(255)
  is_active     BOOLEAN DEFAULT true
  created_at    TIMESTAMPTZ

timeseries
  id            INTEGER PK
  name          VARCHAR(50) UNIQUE
  description   VARCHAR(100)
  owner_id      INTEGER FK → users.id
  [RLS: only rows where owner_id = current session user]

timeseries_data  ← TimescaleDB hypertable
  id            INTEGER
  timeseries_id INTEGER FK → timeseries.id
  timestamp     TIMESTAMPTZ  (partition key, 1-day chunks)
  value         FLOAT
  status        CHAR(1)  W | V | E
  created_at    TIMESTAMPTZ
  PK (id, timestamp)
  Partitioned by: timeseries_id
```

Row-Level Security is enforced at the database level on the `timeseries` table. The application sets `app.current_user_id` on each session, and the RLS policy ensures users can only read and write their own series.

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate_timeseries.py` | Generate synthetic time series CSV/JSON at 15-min intervals |
| `scripts/api_client.py` | Lightweight HTTP client for manual API testing |
| `scripts/init-db.sql` | Initialises `app_user` role and grants (run automatically by Docker) |

```bash
# Generate 1000 data points for a series named "sensor_01"
python scripts/generate_timeseries.py 1000 --name sensor_01 --out sensor_01.json
```

## Performance Notes

- `timeseries_data` is a TimescaleDB hypertable with 1-day chunks, partitioned by `timeseries_id`. This keeps per-series scans within a small number of chunks.
- The connection pool is sized at 50 connections with 50 overflow (configured in `backend/src/db/schema.py`).
- `synchronous_commit=off` is set in `docker-compose.yml` for throughput. This means a crash within the last ~200 ms of a write could lose that write — acceptable for most time series workloads but worth knowing.
- The `GET /timeseries/{id}` endpoint deduplicates data points at the same timestamp, keeping the row with the latest `created_at`. This supports an upsert-via-append pattern.
- List pagination uses SQL `OFFSET`, which degrades at high offsets. For very large catalogues, consider switching to keyset pagination on the list endpoint.
