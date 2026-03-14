# DataBot — ON24 Analytics Platform

## What Is This
Multi-agent application for exploring ON24 client webinar data (events, audiences, engagement) with data visualizations and AI-powered conversational analytics. All 6 development phases are complete.

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
# First-time setup — .env.local is the source of truth for secrets (gitignored)
# docker compose reads it via env_file; config.py loads both .env and .env.local

# Docker (recommended)
docker compose up --build   # Starts all services; runs alembic upgrade head before uvicorn
# App:      http://localhost:3001
# API docs: http://localhost:8000/docs
# WebSocket: ws://localhost:8000/ws/chat
#
# NOTE: postgres host port is 5433 (not 5432) — host 5432 is taken by agentic-video-db-1.
#   Internal container port is still 5432; backend connects via Docker network (unaffected).
#   Local psql/pgAdmin: use port 5433.
#
# NOTE: ON24_DB_URL points to 10.3.7.233 (ON24 internal network).
#   Queries to on24master will fail if not on VPN or the ON24 corporate network.

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
```


## Key Conventions
- **Models**: All use `TimestampMixin` (created_at, updated_at) + optional `SyncedMixin` (synced_at). Each has `to_dict()`. All synced models have `raw_json JSONB`.
- **Upserts**: `sqlalchemy.dialects.postgresql.insert` with `on_conflict_do_update` — idempotent syncs.
- **Rate Limiting**: Token bucket per ON24 endpoint category (6 tiers, 10-1000 req/min). Auto-detected from URL path.
- **Schemas**: Pydantic with `ConfigDict(from_attributes=True)`. Paginated endpoints return `PaginatedResponse[T]`.
- **Config**: All settings via env vars, Pydantic Settings in `app/config.py`. Never hardcode secrets.
- **Frontend State**: TanStack Query for server-state. No Redux/Zustand.
- **Frontend Paths**: `@/` alias resolves to `src/` (vite.config.ts + tsconfig paths).

## ON24 Analytics Platform — Existing Reporting Sections
The ON24 platform has these built-in analytics sections. Use these URLs when redirecting users to more appropriate tools:

| Section | Sub-section | URL |
|---------|-------------|-----|
| Dashboard | — | https://wcc.on24.com/webcast/dashboard |
| Smart Tips | — | https://wcc.on24.com/webcast/keyinsightssummary |
| **Products** | Webcast Elite | https://wcc.on24.com/webcast/reportsdashboard |
| | Engagement Hub | https://wcc.on24.com/webcast/portalsummaryreports |
| | Target | https://wcc.on24.com/webcast/targetAnalytics |
| | Go Live | https://wcc.on24.com/webcast/virtualeventsummary |
| **Leads** | Power Leads | https://wcc.on24.com/webcast/leadsreports |
| | Segments | https://wcc.on24.com/webcast/segmentationsummary |
| | Funnel | https://wcc.on24.com/webcast/funnelaudience |
| | Accounts | https://wcc.on24.com/webcast/accountengagement |
| **Content** | Documents | https://wcc.on24.com/webcast/documentsanalytics |
| | Videos | https://wcc.on24.com/webcast/videolibraryanalytics |
| | Webpages | https://wcc.on24.com/webcast/webpagessummary |
| **Interactions** | Polls & Surveys | https://wcc.on24.com/webcast/pollsreport |
| | Buying Signals | https://wcc.on24.com/webcast/buyingsignals |
| | Presenters | https://wcc.on24.com/webcast/funnelpresenters |
| **Benchmarking** | — | https://wcc.on24.com/webcast/benchmarking |

## ON24 Data Access
**Two data sources — always prefer direct DB for reads:**

| Source | Used for | Location |
|--------|----------|----------|
| ON24 master DB (on24master) | All analytics reads | `backend/app/db/on24_db.py` + `on24_query_tools.py` |
| ON24 REST API (apiqa.on24.com) | Write ops only (create event, registrations) | `backend/app/services/on24_client.py` |

**Tenant isolation (critical):**
- `get_client_id()` reads root from `settings.on24_client_id` (config only, never from agents/users)
- `get_tenant_client_ids()` returns root + all sub-clients via cycle-safe recursive CTE (cached)
- All 10 query functions use `WHERE client_id = ANY($N::bigint[])` — never a single-ID filter
- Root client 10710 has 9 sub-clients: 22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909

**Key on24master tables:**
- `dw_attendee` — preferred for engagement aggregates (engagement_score, live/archive minutes)
- `dw_lead` — lead/prospect data with direct client_id
- `event` — join point for tenant scoping on event_user (which has no client_id)
- `event_info.epid` — internal config flags only; not useful for analytics

## Agent Architecture
4 agents, each a Python class with multi-round Anthropic tool_use loop (max 5 rounds):

| Agent | File | Tools | Purpose |
|-------|------|-------|---------|
| Orchestrator | `orchestrator.py` | route_to_* | Classifies intent, delegates, synthesizes |
| Data Agent | `data_agent.py` | list_events, get_event_kpis, get_top_events, get_attendance_trends, get_audience_companies, get_audience_sources, get_polls, get_top_events_by_polls, get_poll_overview, get_resources, generate_chart_data | DB queries + KPI computation + charts |
| Content Agent | `content_agent.py` | analyze_topic_performance, compare_event_performance, analyze_scheduling_patterns, suggest_topics | Content insights |
| Admin Agent | `admin_agent.py` | create_event, update_event, add_registrant, remove_registrant, get_event_summary | ON24 write operations |

**Admin confirmation flow**: Admin agent returns `requires_confirmation=True` with summary. Frontend shows confirmation dialog. User resends with `{"confirmed": true}`.

**Audit logging**: Every tool call in every agent is fire-and-forget written to `agent_audit_logs` table via `asyncio.create_task`.

**Orchestrator history safety**: On agent exception after tool_use is appended, the dangling messages are popped before re-raising to prevent corrupt conversation history.

## API Endpoints
- `POST /api/chat` — HTTP fallback for agent conversations
- `WS /ws/chat` — WebSocket streaming chat
- `POST /api/feedback` — Save thumbs-down feedback to `data/improvement-inbox-MM-DD-YYYY.txt`
- `GET /api/calendar?year=&month=` — Events for a month (KPIs for past events)
- `GET /api/calendar/event/{id}` — Single event summary with poll/survey/resource counts

## Charts
- **Bar / Line**: Recharts `BarChart`/`LineChart`; `generate_chart_data` returns `{type, data, title, x_key, y_keys}`
- **Pie**: Recharts `PieChart/Pie/Cell`; `generate_chart_data` with `chart_type="pie"` returns `{type: "pie", data: [{name, value}]}`
- Suggestion chips are context-aware: never suggest the currently displayed view type

## Event Calendar
- Outlook-style modal at `frontend/src/components/calendar/EventCalendar.tsx`
- Month view (6×7 grid) + Week view (hourly 7am–9pm timeline)
- Click any event → side panel with full summary (title, abstract, KPIs, poll/survey/resource counts)
- Past events show performance KPIs; future events show "Performance data available after the event concludes."
- Opened from: TopNav calendar icon, "Show event calendar" suggestion tile, or chat
- `event.goodafter` = start time, `event.goodtill` = end time (no starttime/endtime columns on ON24 event table)

## WebSocket Protocol (`/ws/chat`)
Client sends: `{"type": "message", "content": "...", "confirmed": false}`
Server sends message types: `agent_start`, `agent_routing`, `text`, `chart_data`, `confirmation_required`, `message_complete`, `error`, `reset`

## Environment Variables
```
# .env.local (gitignored — single source of truth for all secrets)
# Docker compose loads via env_file: .env.local; environment: block overrides DATABASE_URL

DATABASE_URL=postgresql+asyncpg://databot:<password>@postgres:5432/databot  # overridden in compose
ON24_DB_URL=postgresql+asyncpg://ON24_RO:<pass>@10.3.7.233:5458/on24master  # ON24 PROD master (read-only); requires VPN/internal network
DB_PG_SSL_ROOT_CERT_CONTENT=<ca pem content>
DB_PG_SSL_CERT_CONTENT=<client cert content>
DB_PG_SSL_KEY_CONTENT=<client key content>

ON24_CLIENT_ID=10710
ON24_BASE_URL=https://apiqa.on24.com
ON24_ACCESS_TOKEN_KEY=<key>
ON24_ACCESS_TOKEN_SECRET=<secret>

ANTHROPIC_API_KEY=<key>
POSTGRES_PASSWORD=databot_dev
DEBUG=true

# MCP server (optional — defaults to direct on24_client.py when USE_MCP=N)
USE_MCP=N                            # Y to route admin writes through on24-mcp container
USE_MCP_BLOCKLIST=                   # comma-separated tool names to block even if USE_MCP=Y
MCP_SERVER_URL=http://on24-mcp:8001  # override only if running MCP server elsewhere
```
