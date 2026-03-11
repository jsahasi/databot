# DataBot Tasks

## Phase 1: Foundation — COMPLETE (commit 009b156)
- [x] Project scaffolding (Docker Compose, pyproject.toml, Dockerfiles, .gitlab-ci.yml)
- [x] PostgreSQL schema + Alembic setup (11 models with JSONB, TimestampMixin, SyncedMixin)
- [x] ON24 API client with rate limiting (token bucket, 6 tiers, auto-pagination)
- [x] ETL sync service (events, attendees, registrants upsert with sync log tracking)
- [x] FastAPI REST endpoints (events CRUD, analytics dashboard/trends/top, sync trigger/status)
- [x] Backend tests (42 tests: ON24 client, rate limiter, health endpoint)

## Phase 2: Frontend Shell — NEXT
- [ ] Dashboard layout with sidebar, top nav, responsive grid
- [ ] Events list page with filtering, sorting, pagination
- [ ] Event detail page with sub-entity tabs (attendees, polls, surveys, etc.)
- [ ] Recharts integration: attendance bar charts, engagement line charts, KPI cards
- [ ] Connect frontend to backend API via TanStack Query hooks

## Phase 3: Agent System
- [ ] Claude Agent SDK integration + orchestrator agent
- [ ] Data Agent with query tools (DB queries, KPI computation, chart generation)
- [ ] WebSocket /ws/chat endpoint with streaming responses
- [ ] Frontend chat panel component with agent routing indicator
- [ ] Agent system prompts (orchestrator.md, data_agent.md)

## Phase 4: Full Data + Content Agent — COMPLETE (commit 8cd467a)
- [x] ETL for remaining entities (polls, surveys, CTAs, resources, PEP, viewing sessions)
- [x] Content Agent with topic analysis + performance comparison tools
- [x] Advanced visualizations (Plotly heatmaps, Audiences page, ContentInsights page)
- [x] Audience cross-event analysis page

## Phase 5: Admin Agent + Polish — COMPLETE (commit 10952ca)
- [x] Admin Agent with ON24 write tools (create_event, update_event, add/remove registrant)
- [x] PreToolUse confirmation pattern: requires_confirmation flow in AdminAgent + WebSocket
- [x] AgentAuditLog model + fire-and-forget logging in Data/Content agents
- [x] Settings page (credentials info, sync interval, sync status)
- [x] Alembic 0001_initial_schema.py — full 12-table migration
- [x] Docker health checks for all 3 services
- [x] Plotly code-split via React.lazy (fixes chunk size warning)
