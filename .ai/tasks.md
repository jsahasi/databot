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
- [x] ON24 DB connected — initially QA (10.3.7.233:5459), now switched to **PROD (10.3.7.233:5458)**/on24master, Google Cloud SQL SSL
- [x] on24_db.py: asyncpg pool with SSL, get_tenant_client_ids() hierarchy resolver
- [x] on24_query_tools.py: 10 tenant-safe query functions (client_id = ANY hierarchy)
- [x] All queries scope to full sub-client hierarchy (client 10710 + 9 sub-clients)
- [x] Multi-client architecture documented and planned (contextvars swap path)

## Phase 7: Stabilization + UI Redesign — COMPLETE (commit 8576f67)
- [x] Fix all Docker issues (alpine → Debian images, platform flags, env loading)
- [x] Fix model ID: claude-sonnet-4-20250514 → claude-sonnet-4-6
- [x] Fix SSL: removed ON24 SSL certs from local postgres session.py
- [x] Fix query timeouts: dw_event_session for aggregates, 8s per-query timeout, 1-month default
- [x] Fix ON24 DB column names (discovered via information_schema):
  - dw_event_session: registrant_count, attendee_count, engagement_score_avg (event-level, no event_user_id)
  - question: description (not question_text)
  - resource_hit_track: event_id, event_user_id, resource_id, timestamp, partnerref only
- [x] UI redesign to match mockup: top nav + left chat sidebar + main chat area
- [x] ChatContext: shared useChat state across sidebar + panel via React context
- [x] Markdown table rendering in ChatMessage (pipe tables → HTML tables)
- [x] Agent prompt: concise responses, event_id+date+title format, ban key-value tables
- [x] list_events: past_only param to exclude future-dated events for "last event" queries
- [x] data_agent max_tool_rounds: 5 → 10; graceful fallback with tool_choice=none
- [x] generate_suggestions: 5 anticipatory chips (up from 3), context-aware, 8s timeout
- [x] Chat input autofocus on page load
- [x] Git remote: GitHub only (https://github.com/jsahasi/databot, private)

## Phase 8: UI Polish + Markdown — COMPLETE (2026-03-11)
- [x] TopNav renamed: "DataBot" → "ON24 Data Agent", logo "DB" → "ON24"
- [x] Light/dark mode toggle (pill switch) in TopNav, persisted via localStorage
- [x] Dark mode via `[data-theme="dark"]` CSS attribute on `<html>`; variables in global.css
- [x] ChatPanel + ChatMessage: all hardcoded colors replaced with CSS variables
- [x] react-markdown + remark-gfm for proper markdown rendering in chat
- [x] Agent prompts: no-emoji rule, no markdown headers, use bold sparingly (content_agent.md + data_agent.md)
- [x] Port conflict fix: postgres host port 5432 → 5433 (conflict with agentic-video-db-1 container)

## Phase 8 Addendum: Chart-first UX + Sidebar Dark Mode — COMPLETE (2026-03-11)
- [x] Dark mode sidebar fix — ChatSidebar.tsx hardcoded colors replaced with CSS variables
- [x] Data agent defaults to bar/line charts for 3+ event comparisons and all trend data
- [x] Alternative view suggestion chips ("Show as bar chart", "Show as table") based on response type
- [x] generate_suggestions() updated to accept has_chart and has_table params

## Phase 8 Addendum 2: Poll Fix + Typing UX + Polls Ranking Tool — COMPLETE (2026-03-11)
- [x] Poll query fix: qa.answer_text → qa.answer (correct column name in question_x_answer)
- [x] Poll query fix: Python dict maps a["answer"] → "answer_text" key (API compat)
- [x] New tool: get_top_events_by_polls — ranks events by poll question count via question table
- [x] Chat input: removed disabled={isProcessing} so user can type while agent is processing
- [x] OWASP security hardening: message length limit (4000), session ID sanitization, generic error messages
- [x] Data quality filters: _EXCL_TEST (no "test" in name) + _MIN_REGS_SUBQ (>5 registrants); single-event queries use _EXCL_TEST only to avoid correlated subquery timeout

## Phase 8 Addendum 3: Dark Mode Color Tuning — COMPLETE (2026-03-11)
- [x] --color-text: #e2e8f0 → #c9cfe0 (softer off-white, less glare)
- [x] --color-primary: #6366f1 → #a5b4fc (lighter indigo, legible on dark cards)
- [x] --color-primary-hover: #818cf8 → #c7d2fe
- [x] --color-sidebar-active: #ffffff → #c9cfe0 (matches body text)
- [x] --color-text-secondary: #94a3b8 → #7b8599 (maintains hierarchy without washing out)

## Local Setup Notes
- **App URL**: http://localhost:3001 (via `docker compose up --build`)
- **Postgres host port**: 5433 (internal container port remains 5432; only host mapping changed)
- **ON24 DB**: requires VPN or ON24 internal network (10.3.7.233 not reachable externally)
- **Active ON24 DB**: PROD — 10.3.7.233:5458/on24master (not QA port 5459)

## Backlog / Next Steps
- [ ] Add query tools for dw_lead (lead/prospect analytics)
- [ ] Explore question_x_answer + event_user_x_answer for poll response counts
- [ ] Add backend tests for on24_query_tools (mock asyncpg pool)
- [ ] Frontend Vitest component tests + Playwright E2E
- [ ] Multi-client: implement per-request context var for tenant ID
- [ ] Recent Chats: persist chat history in localStorage

## Verified ON24 Schema (on24master)

> **Active connection: PROD — 10.3.7.233:5458** (switched from QA port 5459 on 2026-03-11)
> Env var: `ON24_DB_URL` in `.env.local`. The `_QA` suffixed entries are not used by the app.

### Key Tables
| Table | Rows | Notes |
|-------|------|-------|
| event | ~7.4M | Filter by client_id; goodafter = event date; title is in `description` column (not event_name) |
| event_user | 585M / 404GB | Registrants — avoid for aggregates; join through event |
| dw_attendee | 262M | Per-attendee: event_user_id, engagement_score, live_minutes, archive_minutes |
| dw_event_session | — | Per-event aggregate: registrant_count, attendee_count, engagement_score_avg, live_attendee_mins, conversion_percent |
| question | 47M | Poll/Q&A/Survey; text in `description` column (not question_text) |
| question_x_answer | — | Poll answer options |
| event_user_x_answer | 334M | Individual responses |
| resource_hit_track | 55M | Columns: event_id, event_user_id, resource_id, timestamp, partnerref |
| dw_lead | 105M | Leads; has client_id directly |
| client_hierarchy | — | Parent/child with self-refs; use cycle-safe recursive CTE |

### Sub-client hierarchy for 10710
[22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909]
Total events: ~13,293 (10710: 11,517 + sub-clients: 1,776)
