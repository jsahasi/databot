# Architecture Decisions

## 2026-03-11: Chart-first data display + alternative view suggestions
- Data agent defaults to bar/line charts for 3+ event comparisons and all trend data
- Suggestion chips include alternative view options (show as table, show as bar chart) based on response type
- generate_suggestions() detects has_chart / has_table from response and adjusts chip generation prompt

## 2026-03-11: Agent Framework
**Decision:** Anthropic Python SDK `messages.create()` with `tools` parameter, NOT the `claude-agent-sdk` package and NOT Claude Code Skills
**Rationale:** Skills are CLI-only markdown instructions — not deployable services. Using `anthropic.AsyncAnthropic().messages.create()` directly gives full control, runs inside FastAPI, supports concurrent multi-user, and is stable. Each agent is a plain Python class with a multi-round tool_use loop (max 5 rounds).

## 2026-03-11: Tech Stack
**Decision:** Python 3.12/FastAPI + React 18/TypeScript/Vite + PostgreSQL 16
**Rationale:** Anthropic SDK is Python-native. FastAPI async-first. React for dashboard-heavy UI with TanStack Query for server-state. PostgreSQL JSONB for app data; ON24 DB queried directly.

## 2026-03-11: No Redis/Celery
**Decision:** Background tasks via asyncio within FastAPI, not a separate worker
**Rationale:** At current scale, async background tasks suffice. Can add Redis later if needed.

## 2026-03-11: ON24 API Rate Limiting Strategy
**Decision:** Token bucket per endpoint category (6 tiers: 10-1000 req/min)
**Rationale:** ON24 has varying rate limits per endpoint type. Categories auto-detected from URL path. Only needed for write operations now (reads go direct to DB).

## 2026-03-11: JSONB Raw Storage Pattern
**Decision:** Store full ON24 API responses in `raw_json` JSONB column alongside extracted typed columns (for our own app tables)
**Rationale:** ON24 API evolves. Typed columns serve queries; JSONB preserves future data.

## 2026-03-11: Upsert Strategy
**Decision:** PostgreSQL INSERT...ON CONFLICT DO UPDATE for all sync operations
**Rationale:** Idempotent syncs. Uses composite unique constraints.

## 2026-03-11: Docker Architecture
**Decision:** 3 containers only (postgres, backend, frontend). No nginx reverse proxy in dev.
**Rationale:** Minimal complexity. Frontend Dockerfile uses multi-stage build for production.

## 2026-03-11: Visualization Libraries
**Decision:** Recharts (primary) + Plotly (complex analytics, lazy-loaded)
**Rationale:** Recharts is React-native and composable. Plotly fills gaps for heatmaps. Lazy-loaded to avoid ~3MB chunk at initial load.

## 2026-03-11: Direct DB Reads (no ETL sync)
**Decision:** Data Agent queries ON24's PostgreSQL database (on24master) directly via asyncpg read-only connection. No ETL sync needed for reads.
**Rationale:** Direct DB is orders of magnitude faster than REST API for analytics:
- Single SQL query replaces 100+ paginated API calls
- No rate limits, no sync lag, always live data
- Full SQL aggregation power (GROUP BY, window functions, CTEs)
- ETL sync only needed if ON24 DB access is revoked
REST API retained for write operations only (Admin Agent: create event, manage registrations).

## 2026-03-11: dw_* Tables for Aggregates
**Decision:** Use `dw_attendee`, `dw_lead`, `dw_event_session` etc. as primary sources for aggregate analytics rather than raw tables (event_user, media_metric_session).
**Rationale:** dw_ = data warehouse pre-processed summaries. Raw tables are enormous (event_user: 585M rows, 404GB). dw_attendee already has engagement_score, live_minutes, archive_minutes per attendee. Use raw tables only when DW doesn't have the needed detail.

## 2026-03-11: Tenant Isolation Architecture
**Decision:** Strict multi-tenant isolation with client_id injected from config — never from agents/users. Scope includes full sub-client hierarchy.
**Rationale:** on24master is a multi-tenant database with all ON24 customers' data. A single misscoped query could expose other clients' data.
Implementation:
- `get_client_id()` → root from config only
- `get_tenant_client_ids()` → root + all sub-clients via recursive CTE (cycle-safe)
- All queries use `WHERE client_id = ANY($N::bigint[])` with the hierarchy array
- No query function accepts client_id as a parameter

## 2026-03-11: Multi-Client Support Plan
**Decision:** Hardcode single client (10710) now; design for multi-client without re-architecting queries later.
**Current state:** `ON24_CLIENT_ID=10710` in env, `get_tenant_client_ids()` cached per process.
**Future path:**
1. Add `tenants` table in our app DB: `session_id → root_client_id`
2. Replace `get_client_id()` with per-request context var (Python contextvars)
3. Invalidate `_tenant_ids_cache` per-request or use per-tenant cache dict
4. No changes needed to query functions — they already call `get_tenant_client_ids()` abstractly

## 2026-03-11: Admin Agent Confirmation Pattern
**Decision:** AdminAgent returns `requires_confirmation=True` before executing any destructive tool. Client must resend with `{"confirmed": true}`.
**Rationale:** ON24 write operations are not easily reversible. Explicit confirmation prevents accidents.

## 2026-03-11: Agent Audit Logging
**Decision:** Fire-and-forget `asyncio.create_task` writes to `agent_audit_logs` after each tool call.
**Rationale:** Logging must not block the agent response. Errors in audit writes are swallowed.

## 2026-03-11: Postgres Host Port 5433
**Decision:** Changed the Docker Compose host port mapping for the postgres container from `5432:5432` to `5433:5432`.
**Rationale:** The host machine had another project's postgres container (agentic-video-db-1) already bound to host port 5432, causing a bind conflict on `docker compose up`. The internal container port remains 5432; backend connects via Docker network using the service name `postgres:5432` — unaffected by this change. Connection tools and local psql clients must use port 5433.

## 2026-03-11: Poll Query Column Name Corrections
**Decision:** `question_x_answer` uses `answer` (not `answer_text`) and `answer_cd` (not `answer_id`). `event_user_x_answer` uses `answer_cd` (not `answer_id`). Poll type codes are `singleoption`/`multioption` (not `POLL`).
**Rationale:** Schema discovered via information_schema query — ON24 column names differ from intuitive names.

## 2026-03-11: Poll Ranking via question Table
**Decision:** `get_top_events_by_polls` counts `DISTINCT question_id` from the `question` table filtered by `question_type_cd IN ('singleoption', 'multioption')`. Does NOT use `dw_event_session.answered_polls` (that's per-attendee in `dw_attendee`, not a per-event poll count).
**Rationale:** `dw_event_session` has no poll count column. Counting distinct questions per event from the `question` table is the correct approach.

## 2026-03-11: react-markdown for Chat Rendering
**Decision:** Use `react-markdown` + `remark-gfm` for rendering agent responses in ChatMessage, replacing the custom pipe-table regex parser.
**Rationale:** Custom parser only handled tables; agent responses now include bold text, lists, and inline code. react-markdown handles the full CommonMark + GFM spec (tables, strikethrough, task lists) with minimal bundle impact. All markdown elements are styled via CSS variables to support dark mode.

## 2026-03-11: Dark Mode via data-theme CSS Attribute
**Decision:** Dark mode is toggled by setting `data-theme="dark"` on the `<html>` element. CSS variables for both themes are declared in `global.css` under `:root` (light) and `[data-theme="dark"]` selectors. Preference is persisted to `localStorage`.
**Rationale:** Attribute-based theming is zero-JS at render time, works with SSR, and avoids flash-of-wrong-theme if applied before paint. Storing in localStorage ensures the toggle survives page reloads. All components use CSS variables (`var(--color-*)`) so no component-level JS is needed to respond to theme changes.

## 2026-03-11: Event Calendar API — goodafter/goodtill columns
**Decision:** Calendar API uses `event.goodafter` as start time and `event.goodtill` as end time.
**Rationale:** ON24 DB has no `starttime`/`endtime` columns on the `event` table. `goodafter` = earliest time event is accessible; `goodtill` = expiry. These are the correct start/end columns confirmed via information_schema.

## 2026-03-11: Resource Downloads Table — content_hit_track_details
**Decision:** Resource download queries use `content_hit_track_details` with `action='TotalHits'`, NOT `resource_hit_track`.
**Rationale:** `resource_hit_track` returned zero rows for client 10710. The correct table is `content_hit_track_details` which tracks content widget interactions. Must join to `display_profile_x_event` → `display_profile` → `display_element` (value_cd='resourcelist') to scope to only resource-list widget items (not other content hits). OR condition handles PDF portal resources via `video_library`.
**Key filters:** `action='TotalHits'`, `media_url_id != 0`, `media_category_cd NOT LIKE 'custom_icon%'`, `event_user_id != 305999` (system user exclusion), `persistenceStatus=PersistenceStatusSaveComplete` and NOT `PersistenceStateDelete`.

## 2026-03-11: Poll Query Join Chain
**Decision:** `query_polls` (per-event) uses simplified join: `event_user_x_answer → event_user → media_url (cd='poll') → question → question_x_answer`.
**Cross-event poll queries** (`query_poll_overview`, `query_top_events_by_polls`) MUST use event-first CTE pattern: find candidate events by `goodafter` date range first (indexed), then join to poll data. Starting from `event_user_x_answer` (334M rows) causes 8s timeout.
**Rationale:** The event table is indexed on `client_id + goodafter`. Narrowing to a small set of events first dramatically reduces the join scan on the massive answer table.

## 2026-03-11: Orchestrator History Rollback
**Decision:** Wrap agent calls in orchestrator try/except; on failure, pop the dangling tool_use assistant message and user message from conversation history before re-raising.
**Rationale:** If an agent throws after the tool_use block is appended to history but before the tool_result is appended, the history becomes corrupt (tool_use without matching tool_result). Subsequent API calls fail with "400 tool_use ids found without tool_result blocks". Rolling back prevents cascade failures.

## 2026-03-11: Pie Chart Support
**Decision:** Added `chart_type="pie"` support to `generate_chart_data`. Returns `{type: "pie", data: [{name, value}]}`. Frontend renders with Recharts `PieChart/Pie/Cell`.
**Rationale:** User requested pie charts for audience source distributions (partnerref). The existing bar/line renderer was extended rather than replaced.

## 2026-03-11: "How do I" Sub-menu Design
**Decision:** "How do I...?" tile on home page opens a sub-menu of 8 specific platform how-to questions, not a general chat message.
**Rationale:** Sending a vague "How do I...?" to the LLM produced a text blob listing all capabilities. Sub-menu approach: (1) gives clickable specific options, (2) each option triggers a targeted ChromaDB knowledge base search, (3) options curated to match available KB article coverage. Replaced "add speakers" and "email notifications" (poor coverage) with "prepare as presenter" and "Connect integrations" (strong coverage).

## 2026-03-11: Multi-Event Card Grid (2–4 events)
**Decision:** When `list_events` returns 2–4 events as a final answer, render a 2-column card grid (EventCardsGrid) instead of a pipe table.
**Rationale:** Small event sets (2–4) benefit from a richer visual layout. Each card shows title, event_id, event_type, and date. For 5+ events a table is more scannable. Cards are only shown when list_events is the final tool (not an intermediate lookup) — discarded if agent calls other tools after.
**Implementation:** data_agent.py captures event_cards; discard logic based on tool_calls_made; WS message type `event_cards`; EventCardsGrid in ChatMessage.tsx; data_agent.md prompt rule for count-only output.

## 2026-03-11: smart_tips_benchmark — Not Accessible
**Decision:** Deferred. The `smart_tips_benchmark` materialized view exists somewhere in the ON24 platform but is not visible via the `ON24_RO` read-only user (pg_matviews shows zero rows; information_schema tables search returns nothing). Related benchmark tables exist: `dw_benchmark` (benchmark_code, benchmark_value, benchmark_month, industry_id, application_id), `dw_benchmark_industry`, `benchmark_industry`, `benchmark_application`, `dw_benchmark_metadata`.
**Next step:** Determine which schema/DB hosts the view, or use `dw_benchmark` directly as a benchmark data source.

## 2026-03-11: ON24 Client Hierarchy
**Decision:** Queries must scope to full sub-client tree, not just root client_id.
**Finding:** client 10710 has 9 sub-clients (22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909). Using only client_id=10710 misses ~13% of events (1,776 of 13,293 total).
**Implementation:** `client_hierarchy` table, recursive CTE with DISTINCT to handle cycles (table has self-referential rows).

## 2026-03-13: ChromaDB → Postgres + OpenAI Embeddings
**Decision:** Replaced ChromaDB with PostgreSQL `REAL[]` column for embeddings + OpenAI `text-embedding-3-small` + numpy cosine similarity.
**Rationale:** ChromaDB downloaded a 79MB ONNX runtime on every container build. Postgres already deployed; storing embeddings there eliminates the extra dependency and cold-start delay. OpenAI embeddings are high quality and consistent. Numpy cosine similarity is sufficient at KB scale (637 articles / 2729 chunks).
**Implementation:** `knowledge_base_articles` table (migration 0002); `app/db/knowledge_base.py` ingest + query; `OPENAI_API_KEY` env var added to Settings.

## 2026-03-13: AI-ACE Content Tile in Calendar Event Detail
**Decision:** Show AI-ACE content tile only when `articles` dict is non-empty (i.e., content exists). Hidden entirely when no AI-generated content is available. Default selected type is `KEYTAKEAWAYS`.
**Rationale:** Showing an empty tile wastes space and confuses users. The KEYTAKEAWAYS default surfaces the highest-value content first.
**Key finding:** ON24 DB stores truncated type names: `AUTOGEN_FOLLOWUPEMAI` (not FOLLOWUPEMAIL) and `AUTOGEN_SOCIALMEDIAP` (not SOCIALMEDIAPOST). Labels map these truncated values.

## 2026-03-13: Key Takeaways Section Tabs (Server-Side Parsing)
**Decision:** Parse KEYTAKEAWAYS HTML into named sections (summary/takeaways/quote/other) server-side in Python (BeautifulSoup), not client-side via DOMParser.
**Rationale:** Browser DOMParser normalizes styles unpredictably. BeautifulSoup is deterministic. Sections identified by `font-size: 18px` spans with text length < 80 chars (length guard prevents Key Quote content from being misdetected as heading). Sections: Executive Summary → summary, Key Takeaways → takeaways, Key Quote → quote, anything else → other.
**Implementation:** `_parse_kt_sections()` in `calendar.py`; critical: `isinstance(el, Tag)` check (strings also have `.find()`); `find(True, style=lambda s: ...)` API.

## 2026-03-13: Calendar Event Detail — 4th KPI Tile (Avg Engagement)
**Decision:** Add `avg_engagement_score` as a 4th KPI tile in the calendar event detail side panel.
**Rationale:** Engagement score is a primary performance indicator. Adding it alongside registrants/attendees/conversion gives a complete performance picture.
**Implementation:** Added `LEFT JOIN dw_attendee a ON a.event_id = e.event_id` to the `get_calendar_event` SQL; `dw_attendee` has no `client_id` column — scoped by event_id only (no explicit client filter needed here as event_id already scoped by client check above).
