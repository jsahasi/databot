# ON24 Data Agent

A multi-agent AI application for exploring ON24 webinar analytics — events, audiences, engagement, and content performance — through a conversational chat interface backed by direct database access.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- `.env.local` file at the project root with all required secrets (see [Environment Variables](#environment-variables) below)
- VPN or ON24 internal network access for ON24 database queries

## Quick Start

```bash
docker compose up --build
```

Then open: **http://localhost:3001**

> First run takes ~2 minutes (builds images, runs DB migrations, starts all services).

## Key URLs

| Service | URL |
|---------|-----|
| App (React frontend) | http://localhost:3001 |
| API docs (Swagger) | http://localhost:8000/docs |
| WebSocket chat | ws://localhost:8000/ws/chat |
| Postgres (host) | localhost:5433 |

> **Note:** Postgres is exposed on host port **5433** (not 5432) to avoid conflict with other local containers.

## Architecture

- **Backend**: FastAPI (Python 3.12) with async SQLAlchemy + Alembic, running on port 8000
- **Frontend**: React 18 + TypeScript + Vite, served on port 3001
- **Databases**: PostgreSQL 16 (app data, port 5433 on host) + ON24 master DB (read-only, direct asyncpg connection for analytics)
- **Agents**: 4-agent system (Orchestrator, Data, Content, Admin) using Anthropic SDK `messages.create()` with tool_use

The Data Agent queries ON24's PostgreSQL database (`on24master`) directly via a read-only connection — no ETL sync needed for analytics. The Admin Agent uses the ON24 REST API for write operations only.

> **ON24 DB requires VPN**: `ON24_DB_URL` points to `10.3.7.233` (ON24 internal network). Analytics queries will fail if you are not connected to VPN or the ON24 corporate network.

## Environment Variables

Copy `.env.example` to `.env.local` and fill in secrets. Docker Compose loads `.env.local` via `env_file`.

Key variables:

```
ON24_DB_URL          # PostgreSQL URL for ON24 master DB (PROD: 10.3.7.233:5458/on24master)
ON24_CLIENT_ID       # Root client ID (10710 for ON24)
ON24_ACCESS_TOKEN_KEY / ON24_ACCESS_TOKEN_SECRET  # ON24 REST API credentials
ANTHROPIC_API_KEY    # Anthropic API key for agent LLM calls
POSTGRES_PASSWORD    # Password for the local app database
```

See `.env.example` for the full list with descriptions.

## Agents

| Agent | Role | Tools |
|-------|------|-------|
| Orchestrator | Routes queries to the right agent | route_to_data/content/admin_agent |
| Data Agent | Queries ON24 DB, returns analytics + charts | list_events, get_event_kpis, get_top_events, get_attendance_trends, get_audience_companies, get_polls, get_top_events_by_polls, get_poll_overview, get_resources, generate_chart_data |
| Content Agent | Topic analysis, scheduling patterns, suggestions | analyze_topic_performance, compare_event_performance, suggest_topics |
| Admin Agent | ON24 API write operations (with confirmation) | create_event, update_event, add_registrant, remove_registrant |

All Data Agent queries are tenant-scoped to client 10710 + 9 sub-clients via `client_id = ANY(get_tenant_client_ids())`.

## Feedback Loop

Each bot response shows a thumbs up / thumbs down on hover.

- **Thumbs down** opens an inline popup: "Tell me what I got wrong"
- Feedback is saved to `data/improvement-inbox-MM-DD-YYYY.txt` as a structured LLM-ready improvement prompt including timestamp, agent used, user question, and bot response
- The `data/` folder is mounted as a Docker volume and persists outside the container

## Regression Tests

```bash
python -m pytest tests/test_chat_prompts.py -q
```

26 prompt tests — 22 pass, 4 skipped (known data gaps: no poll responses or resource clicks for client 10710 since 2023).

## Development

```bash
# Backend (without Docker)
cd backend && pip install -e ".[dev]"
pytest tests/ -q
ruff check app/

# Frontend (without Docker)
cd frontend && npm install
npm run dev        # Dev server at localhost:5173 (proxies /api and /ws to backend)
npm run typecheck
npm run lint
```

> **Frontend note**: The deployed frontend is a nginx production build — run `docker compose up --build -d frontend` after any frontend change. No hot-reload in Docker.
