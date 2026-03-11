# Architecture Decisions

## 2026-03-11: Agent Framework
**Decision:** Anthropic Python SDK `messages.create()` with `tools` parameter, NOT the `claude-agent-sdk` package and NOT Claude Code Skills
**Rationale:** Skills are CLI-only markdown instructions — not deployable services. The `claude-agent-sdk` package API was still in flux. Using `anthropic.AsyncAnthropic().messages.create()` directly gives full control, runs inside FastAPI, supports concurrent multi-user, and is stable. Each agent is a plain Python class with a multi-round tool_use loop (max 5 rounds).

## 2026-03-11: Tech Stack
**Decision:** Python 3.12/FastAPI + React 18/TypeScript/Vite + PostgreSQL 16
**Rationale:** Anthropic SDK is Python-native. FastAPI async-first aligns with async SDK and httpx. React for dashboard-heavy UI with TanStack Query for server-state. PostgreSQL JSONB for flexible ON24 API response storage + materialized views for KPIs.

## 2026-03-11: No Redis/Celery
**Decision:** Background tasks via asyncio within FastAPI, not a separate worker
**Rationale:** At current scale, async background tasks suffice. PostgreSQL handles caching. Avoids infrastructure complexity. Can add Redis later if real-time pub/sub or persistent job queues are needed.

## 2026-03-11: ON24 API Rate Limiting Strategy
**Decision:** Token bucket per endpoint category (6 tiers: 10-1000 req/min)
**Rationale:** ON24 has varying rate limits per endpoint type. A single global limiter would be too conservative for high-limit endpoints. Category auto-detected from URL path keywords in `rate_limiter.py`.

## 2026-03-11: JSONB Raw Storage Pattern
**Decision:** Store full ON24 API responses in `raw_json` JSONB column alongside extracted typed columns
**Rationale:** ON24 API evolves. Typed columns serve queries and indexes; JSONB preserves data we haven't modeled yet, enabling future features without re-syncing historical data.

## 2026-03-11: Upsert Strategy
**Decision:** PostgreSQL INSERT...ON CONFLICT DO UPDATE for all sync operations
**Rationale:** Idempotent syncs — re-running a sync safely updates existing records. Uses composite unique constraints (e.g., on24_attendee_id + on24_event_id).

## 2026-03-11: Docker Architecture
**Decision:** 3 containers only (postgres, backend, frontend). No nginx reverse proxy in dev.
**Rationale:** Minimal complexity. Frontend Dockerfile uses multi-stage build (node build + nginx serve) for production. Vite dev server proxies /api and /ws to backend in development.

## 2026-03-11: Visualization Libraries
**Decision:** Recharts (primary) + Plotly (complex analytics)
**Rationale:** Recharts is React-native and composable, covers 80% of dashboard charting. Plotly fills gaps for heatmaps. Plotly lazy-loaded via React.lazy to avoid ~3MB chunk size at initial load.

## 2026-03-11: Admin Agent Confirmation Pattern
**Decision:** AdminAgent returns `requires_confirmation=True` with a `confirmation_summary` before executing any destructive tool. Client must resend message with `{"confirmed": true}`.
**Rationale:** ON24 write operations (create event, manage registrations) are not easily reversible. Explicit confirmation prevents accidental mutations. WebSocket protocol handles confirmation_required message type.

## 2026-03-11: Agent Audit Logging
**Decision:** Fire-and-forget `asyncio.create_task` writes to `agent_audit_logs` after each tool call
**Rationale:** Logging must not block the agent response. Errors in audit writes are swallowed to avoid degrading the primary chat experience. All agent names, tool names, inputs, results, and confirmation status are recorded.
