# DataBot Tasks

## Phase 1: Foundation — COMPLETE (commit 009b156)
- [x] Project scaffolding (Docker Compose, pyproject.toml, Dockerfiles, .gitlab-ci.yml)
- [x] PostgreSQL schema + Alembic setup (11 models with JSONB, TimestampMixin, SyncedMixin)
- [x] ON24 API client with rate limiting (token bucket, 6 tiers, auto-pagination)
- [x] ETL sync service (events, attendees, registrants upsert with sync log tracking)
- [x] FastAPI REST endpoints (events CRUD, analytics dashboard/trends/top, sync trigger/status)
- [x] Backend tests (42 tests: ON24 client, rate limiter, health endpoint)

## Phase 2: Frontend Shell — COMPLETE (commit 2a8634a)
- [x] Dashboard layout with sidebar, top nav, responsive grid
- [x] Events list page with filtering, sorting, pagination
- [x] Event detail page with sub-entity tabs (attendees, polls, surveys, etc.)
- [x] Recharts integration: attendance bar charts, engagement line charts, KPI cards
- [x] Connect frontend to backend API via TanStack Query hooks

## Phase 3: Agent System — COMPLETE (commit 06b46b4)
- [x] Anthropic SDK tool_use pattern (orchestrator, data agent)
- [x] Data Agent with 6 query tools (DB queries, KPI computation, chart generation)
- [x] WebSocket /ws/chat endpoint with streaming responses
- [x] Frontend chat panel component with agent routing indicator
- [x] Agent system prompts (orchestrator.md, data_agent.md, content_agent.md, admin_agent.md)

## Phase 4: Full Data + Content Agent — COMPLETE (commit 8cd467a)
- [x] ETL for remaining entities (polls, surveys, CTAs, resources, PEP, viewing sessions)
- [x] Content Agent with topic analysis + performance comparison tools
- [x] Advanced visualizations (Plotly engagement heatmap, Audiences page, ContentInsights page)
- [x] New analytics endpoints: /audiences, /content-performance, /engagement-heatmap

## Phase 5: Admin Agent + Polish — COMPLETE (commit 10952ca)
- [x] Admin Agent with ON24 write tools (create_event, update_event, add/remove registrant)
- [x] PreToolUse confirmation pattern: requires_confirmation flow in AdminAgent + WebSocket
- [x] AgentAuditLog model + fire-and-forget logging in Data/Content/Admin agents
- [x] Settings page (credentials info, sync interval selector, sync status display)
- [x] Alembic 0001_initial_schema.py — full 12-table migration (upgrade + downgrade)
- [x] Docker health checks for all 3 services (postgres, backend, frontend)
- [x] Plotly code-split via React.lazy + Suspense (fixes ~3MB chunk size warning)

## Backlog / Next Steps
- [ ] Verify ON24 API credentials (Client ID 10710 returning 401 — check portal activation / IP allowlist)
- [ ] Add ANTHROPIC_API_KEY to .env.local to enable agent chat
- [ ] Run `docker compose up --build` end-to-end smoke test
- [ ] Run `alembic upgrade head` to apply DB migration
- [ ] Add backend tests for agent tool handlers (data, content, admin)
- [ ] Add frontend Vitest component tests
- [ ] Playwright E2E: dashboard loads, chat sends message, sync triggers
- [ ] Consider Redis + Celery if scheduled sync needs to survive app restarts
- [ ] Materialized view `event_analytics_summary` for dashboard KPI caching
