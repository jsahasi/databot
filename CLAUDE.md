# DataBot — ON24 Analytics Platform

## What Is This
Multi-agent application for exploring ON24 client webinar data (events, audiences, engagement) with data visualizations and AI-powered conversational analytics.

## Tech Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic, httpx
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Recharts, Plotly
- **Database**: PostgreSQL 16 (external, JSONB for raw API data)
- **Agents**: Claude Agent SDK (Python) — NOT Claude Code Skills
- **Deployment**: Docker Compose, GitLab CI/CD

## Project Structure
```
backend/
  app/
    api/          # FastAPI route handlers (events, analytics, sync, chat)
    models/       # SQLAlchemy ORM (11 models, all have to_dict())
    schemas/      # Pydantic request/response schemas
    services/     # Business logic (on24_client, sync_service, rate_limiter)
    agents/       # Claude Agent SDK agents (orchestrator, data, content, admin)
      tools/      # MCP tool definitions for agents
      prompts/    # System prompts per agent (.md files)
    db/           # Session factory, repositories
  tests/          # pytest-asyncio, httpx MockTransport
  alembic/        # Database migrations
frontend/
  src/
    pages/        # Route-level page components
    components/   # Reusable UI (charts/, chat/, layout/, common/)
    hooks/        # Custom React hooks
    services/     # API client (axios)
    types/        # TypeScript interfaces
```

## Commands
```bash
# Backend
cd backend && pip install -e ".[dev]"     # Install with dev deps
pytest tests/ -v                           # Run tests
ruff check app/                            # Lint
ruff format app/                           # Format
alembic upgrade head                       # Run migrations

# Frontend
cd frontend && npm install                 # Install deps
npm run dev                                # Dev server (port 3000)
npm run build                              # Production build
npm run lint                               # Lint
npm run typecheck                          # Type check

# Docker
docker-compose up                          # Start all services
docker-compose up postgres                 # Just database
```

## Key Conventions
- **Models**: All SQLAlchemy models use `TimestampMixin` (created_at, updated_at) and `SyncedMixin` (synced_at). Each has a `to_dict()` method.
- **JSONB**: Every synced model has a `raw_json` JSONB column storing the full ON24 API response.
- **Upserts**: Use `sqlalchemy.dialects.postgresql.insert` with `on_conflict_do_update` for idempotent syncs.
- **Rate Limiting**: Token bucket per ON24 endpoint category (6 tiers, 10-1000 req/min). Categories auto-detected from URL path.
- **API Responses**: Use Pydantic schemas from `app/schemas/`. Paginated endpoints return `PaginatedResponse[T]`.
- **Config**: All settings via environment variables, loaded by Pydantic Settings in `app/config.py`. Never hardcode secrets.
- **Frontend State**: TanStack Query for server-state, no Redux/Zustand.

## ON24 API
- Base: `https://api.on24.com/v2/client/{clientId}`
- Auth headers: `accessTokenKey`, `accessTokenSecret`
- Client wrapper: `backend/app/services/on24_client.py`
- All dates from ON24 are parsed through `_parse_datetime()` and normalized to UTC

## Agent Architecture (Phase 3+)
4 agents using Claude Agent SDK:
1. **Orchestrator** — classifies intent, routes to sub-agents
2. **Data Agent** — DB queries, KPI computation, chart generation
3. **Content Agent** — topic analysis, content recommendations
4. **Admin Agent** — ON24 write operations (with PreToolUse confirmation hooks)

Agents communicate via WebSocket `/ws/chat` with streaming responses.

## Environment Variables
See `.env.example` for all required variables:
- `POSTGRES_PASSWORD`, `DATABASE_URL`
- `ON24_CLIENT_ID`, `ON24_ACCESS_TOKEN_KEY`, `ON24_ACCESS_TOKEN_SECRET`
- `ANTHROPIC_API_KEY`
