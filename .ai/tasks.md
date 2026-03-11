# DataBot Tasks

## Phase 1: Foundation — COMPLETE (commit 009b156)
- [x] Project scaffolding (Docker Compose, pyproject.toml, Dockerfiles, .gitlab-ci.yml)
- [x] PostgreSQL schema + Alembic setup (12 models with JSONB, TimestampMixin, AgentAuditLog)
- [x] ON24 API client with rate limiting (token bucket, 6 tiers, auto-pagination)
- [x] ETL sync service (events, attendees, registrants, polls, surveys, resources, CTAs, PEP)
- [x] FastAPI REST endpoints (events CRUD, analytics dashboard/trends/top, sync trigger/status)
- [x] Backend tests (42 tests: ON24 client, rate limiter, health endpoint)

## Phase 2: Frontend Shell — COMPLETE (commit 2a8634a)
- [x] Dashboard layout with sidebar, top nav, responsive grid
- [x] Events list page with filtering, sorting, pagination
- [x] Event detail page with sub-entity tabs
- [x] Recharts integration: attendance bar charts, engagement line charts, KPI cards
- [x] Connect frontend to backend API via TanStack Query hooks

## Phase 3: Agent System — COMPLETE (commit 06b46b4)
- [x] Anthropic SDK tool_use pattern (orchestrator, data agent)
- [x] Data Agent with 6 query tools
- [x] WebSocket /ws/chat endpoint with streaming responses
- [x] Frontend chat panel + agent routing indicator + suggestion chips

## Phase 4: Full Data + Content Agent — COMPLETE (commit 8cd467a)
- [x] Content Agent with topic analysis + performance comparison tools
- [x] Advanced analytics endpoints: /audiences, /content-performance, /engagement-heatmap
- [x] Audiences page, ContentInsights page, Plotly EngagementHeatmap

## Phase 5: Admin Agent + Polish — COMPLETE (commit 10952ca)
- [x] Admin Agent with ON24 write tools + PreToolUse confirmation pattern
- [x] AgentAuditLog model + fire-and-forget audit logging
- [x] Settings page, Alembic migration, Docker health checks
- [x] Plotly code-split via React.lazy

## Phase 6: Direct DB + Tenant Safety — COMPLETE (commit 5cd295f)
- [x] ON24 QA DB connected (10.3.7.233:5459/on24master, Google Cloud SQL SSL)
- [x] on24_db.py: asyncpg pool with SSL, get_tenant_client_ids() hierarchy resolver
- [x] on24_query_tools.py: 10 tenant-safe query functions (client_id = ANY hierarchy)
- [x] All queries scope to full sub-client hierarchy (client 10710 + 9 sub-clients)
- [x] Multi-client architecture documented and planned (contextvars swap path)
- [x] Chat speed: routing → haiku, synthesis call removed (3 LLM calls → 2)
- [x] Follow-up suggestion chips after every bot response

## Phase 7: Smoke Test + Stabilization — IN PROGRESS (commit 616963f)
- [x] Add ANTHROPIC_API_KEY to .env.local
- [x] Fix ON24_DB_URL (was reusing DATABASE_URL — now separate setting)
- [x] Fix env loading: config.py loads both .env and .env.local; compose uses env_file
- [x] Fix CORS: cors_origins includes localhost:3001
- [x] Fix Dockerfile: alembic upgrade head runs before uvicorn
- [ ] Run end-to-end smoke test: docker compose up --build (awaiting Docker Desktop)
- [ ] Verify ON24 REST API credentials (may need IP allowlist on apiqa.on24.com)

## Backlog / Next Steps
- [ ] Explore dw_event_attendee, dw_event_session tables (more DW aggregates)
- [ ] Explore property table — look up epid labels for event_info
- [ ] Add query tools for dw_lead (lead/prospect analytics)
- [ ] Verify query tool performance on real data with EXPLAIN ANALYZE
- [ ] Add backend tests for on24_query_tools (mock asyncpg pool)
- [ ] Frontend Vitest component tests + Playwright E2E
- [ ] Multi-client: implement per-request context var for tenant ID
- [ ] Redis + async job queue if scheduled sync needs to survive restarts

## Schema Notes (on24master)
Key tables for analytics:
- `event` (6.8GB, ~7.4M rows) — events, filter by client_id
- `event_user` (404GB, ~586M rows) — registrants/attendees; join through event for tenant scope
- `dw_attendee` (110GB, ~262M rows) — **use this** for engagement/duration aggregates
- `dw_lead` (53GB, ~105M rows) — lead/prospect data, has client_id directly
- `dw_lead_user` (57GB, ~302M rows) — lead↔event_user mapping
- `question` (9.6GB, ~47M rows) — polls, Q&A, surveys (question_type_cd)
- `event_user_x_answer` (123GB, ~334M rows) — individual poll/survey responses
- `resource_hit_track` (6.9GB, ~55M rows) — resource download tracking
- `content_hit_track_summary` (30GB, ~109M rows) — content interaction aggregates
- `client_property_info` — client settings (timezone, domain, etc.)
- `event_info` — event config key-value (epid = property ID, mostly internal flags)

Sub-client hierarchy for 10710: [22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909]
Total events across hierarchy: ~13,293 (10710: 11,517 + sub-clients: 1,776)
