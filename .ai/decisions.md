# Architecture Decisions

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

## 2026-03-11: ON24 Client Hierarchy
**Decision:** Queries must scope to full sub-client tree, not just root client_id.
**Finding:** client 10710 has 9 sub-clients (22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909). Using only client_id=10710 misses ~13% of events (1,776 of 13,293 total).
**Implementation:** `client_hierarchy` table, recursive CTE with DISTINCT to handle cycles (table has self-referential rows).
