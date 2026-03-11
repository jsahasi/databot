# DataBot — ON24 Analytics Platform

## What Is This
Multi-agent application for exploring ON24 client webinar data (events, audiences, engagement) with data visualizations and AI-powered conversational analytics. All 5 development phases are complete.

## Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic, httpx
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Recharts, Plotly (lazy-loaded)
- **Database**: PostgreSQL 16 (external, JSONB for raw API data)
- **Agents**: Anthropic Python SDK `messages.create()` with `tools` — NOT Claude Agent SDK package
- **Deployment**: Docker Compose (3 services with health checks), GitLab CI/CD

## Project Structure
```
backend/
  app/
    api/          # FastAPI route handlers (events, analytics, sync, chat)
    models/       # SQLAlchemy ORM (12 models, all have to_dict(), TimestampMixin)
    schemas/      # Pydantic request/response schemas (PaginatedResponse[T])
    services/     # Business logic (on24_client, sync_service, rate_limiter)
    agents/       # AI agents (orchestrator, data, content, admin)
      tools/      # Tool schemas + handlers (__init__.py, query_tools, content_tools, admin_tools)
      prompts/    # System prompts per agent (.md files)
    db/           # Session factory, repositories
  tests/          # 42 tests: pytest-asyncio, httpx MockTransport
  alembic/
    versions/     # 0001_initial_schema.py — full 12-table migration
frontend/
  src/
    pages/        # Dashboard, Events, EventDetail, Audiences, ContentInsights, Settings
    components/   # charts/ (Recharts + Plotly), chat/, layout/, common/
    hooks/        # useChat, useAnalytics, useEvents
    services/     # api.ts — typed API client
    types/        # TypeScript interfaces + react-plotly.d.ts declaration
```

## Commands
```bash
# First-time setup
cp .env.local .env          # or copy .env.example and fill in values

# Docker (recommended)
docker compose up --build   # Start all services
docker compose exec backend alembic upgrade head  # Apply DB migration

# Backend (local dev)
cd backend && pip install -e ".[dev]"
pytest tests/ -v
ruff check app/ && ruff format app/
alembic upgrade head

# Frontend (local dev)
cd frontend && npm install
npm run dev          # Dev server (port 5173, proxies /api and /ws to backend)
npm run build
npm run typecheck    # npx tsc --noEmit
npm run lint

# Services
# App:      http://localhost:5173
# API docs: http://localhost:8000/docs
# Backend:  http://localhost:8000
```

## Key Conventions
- **Models**: All use `TimestampMixin` (created_at, updated_at) + optional `SyncedMixin` (synced_at). Each has `to_dict()`. All synced models have `raw_json JSONB`.
- **Upserts**: `sqlalchemy.dialects.postgresql.insert` with `on_conflict_do_update` — idempotent syncs.
- **Rate Limiting**: Token bucket per ON24 endpoint category (6 tiers, 10-1000 req/min). Auto-detected from URL path.
- **Schemas**: Pydantic with `ConfigDict(from_attributes=True)`. Paginated endpoints return `PaginatedResponse[T]`.
- **Config**: All settings via env vars, Pydantic Settings in `app/config.py`. Never hardcode secrets.
- **Frontend State**: TanStack Query for server-state. No Redux/Zustand.
- **Frontend Paths**: `@/` alias resolves to `src/` (vite.config.ts + tsconfig paths).

## ON24 API
- Base: `https://api.on24.com/v2/client/{clientId}`
- Auth headers: `accessTokenKey`, `accessTokenSecret`
- Client wrapper: `backend/app/services/on24_client.py` (async httpx, all endpoints + write ops)
- All ON24 dates parsed through `_parse_datetime()` → normalized UTC

## Agent Architecture
4 agents, each a Python class with multi-round Anthropic tool_use loop (max 5 rounds):

| Agent | File | Tools | Purpose |
|-------|------|-------|---------|
| Orchestrator | `orchestrator.py` | route_to_* | Classifies intent, delegates, synthesizes |
| Data Agent | `data_agent.py` | query_events, query_attendees, compute_kpis, generate_chart_data, run_analytics_query | DB queries + KPI computation |
| Content Agent | `content_agent.py` | analyze_topic_performance, compare_event_performance, analyze_scheduling_patterns, suggest_topics | Content insights |
| Admin Agent | `admin_agent.py` | create_event, update_event, add_registrant, remove_registrant, get_event_summary | ON24 write operations |

**Admin confirmation flow**: Admin agent returns `requires_confirmation=True` with summary. Frontend shows confirmation dialog. User resends with `{"confirmed": true}`.

**Audit logging**: Every tool call in every agent is fire-and-forget written to `agent_audit_logs` table via `asyncio.create_task`.

## WebSocket Protocol (`/ws/chat`)
Client sends: `{"type": "message", "content": "...", "confirmed": false}`
Server sends message types: `agent_start`, `agent_routing`, `text`, `chart_data`, `confirmation_required`, `message_complete`, `error`, `reset`

## Environment Variables
```
# .env.local / .env
ON24_CLIENT_ID=10710
ON24_ACCESS_TOKEN_KEY=<key>
ON24_ACCESS_TOKEN_SECRET=<secret>
ANTHROPIC_API_KEY=<key>
POSTGRES_PASSWORD=databot_dev
DATABASE_URL=postgresql+asyncpg://databot:<password>@postgres:5432/databot
DEBUG=true
```
