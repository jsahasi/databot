# DataBot — ON24 Analytics Platform

Multi-agent app for exploring ON24 webinar data (events, audiences, engagement) with AI-powered conversational analytics. 10 development phases complete.

## Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic, httpx
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Recharts, Plotly (lazy-loaded)
- **Database**: PostgreSQL 16 (external, JSONB for raw API data)
- **Agents**: Anthropic Python SDK `messages.create()` with `tools` — NOT Claude Agent SDK
- **Deployment**: Docker Compose (4 services: backend, frontend, postgres, on24-mcp)

## Commands
```bash
# Docker (recommended) — .env.local is source of truth for secrets (gitignored)
docker compose up --build   # App: http://localhost:3001 | API: http://localhost:8000/docs
# Postgres host port: 5433 (not 5432). ON24 DB requires VPN (10.3.7.233).

# Backend dev
cd backend && pip install -e ".[dev]"
pytest tests/ -v              # 53+ tests (query tools, charts, security, a11y)
ruff check app/ && ruff format app/

# Frontend dev
cd frontend && npm install
npm run dev                    # Port 5173, proxies /api and /ws to backend
npx vitest run                 # 23+ component tests
npm run typecheck && npm run lint
```

## Key Conventions
- **Models**: `TimestampMixin` + `to_dict()` + `raw_json JSONB` on synced models
- **Upserts**: `INSERT...ON CONFLICT DO UPDATE` for idempotent syncs
- **Config**: env vars via Pydantic Settings (`app/config.py`). Never hardcode secrets.
- **Frontend**: TanStack Query for server-state. `@/` alias → `src/`. No Redux.
- **Schemas**: Pydantic `ConfigDict(from_attributes=True)`. `PaginatedResponse[T]`.

## Tenant Isolation (Critical)
- `get_client_id()` → root from config only (never from agents/users)
- `get_tenant_client_ids()` → root + sub-clients via recursive CTE (cached)
- All queries: `WHERE client_id = ANY($N::bigint[])` — never single-ID
- Root 10710 → 9 sub-clients: 22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909

## Environment Variables
See `.env.example` for full template. Key groups: MCP, ON24 API, ON24 DB (SSL certs), DataBot DB, AI keys (Anthropic + OpenAI), App config.

## Architecture
See `.ai/architecture.md` for: data access sources, agent system details, key ON24 tables, WebSocket protocol, ON24 platform URLs.

## ON24 Analytics Platform URLs
Agent redirects users to built-in ON24 reporting at `wcc.on24.com/webcast/`:
dashboard, keyinsightssummary, reportsdashboard, portalsummaryreports, targetAnalytics, virtualeventsummary, leadsreports, segmentationsummary, funnelaudience, accountengagement, documentsanalytics, videolibraryanalytics, webpagessummary, pollsreport, buyingsignals, funnelpresenters, benchmarking

## Key Implementation Details
- `event.goodafter` = start time, `event.goodtill` = end time (no starttime/endtime columns)
- Event title is in `description` column (not event_name)
- `generate_chart_data` formats data for frontend: bar, line, pie, radar, funnel, gauge, treemap, scatter, heatmap, waterfall
- Admin confirmation: `requires_confirmation=True` → frontend dialog → `{"confirmed": true}`
- Knowledge base: Postgres REAL[] + OpenAI text-embedding-3-small + numpy cosine similarity
- Brand voice: `data/brand_voice.json` auto-generated from AUTOGEN_ content; content agent injects silently
