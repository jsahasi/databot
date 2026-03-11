# Architecture Decisions

## 2026-03-11: Agent Framework
**Decision:** Claude Agent SDK (Python), not Claude Code Skills
**Rationale:** Skills are CLI-only markdown instructions, not deployable services. Agent SDK provides programmatic Python API, custom MCP tools, concurrent multi-user support, and runs inside FastAPI process. Skills have no state management, no programmatic API, and are single-user/single-session.

## 2026-03-11: Tech Stack
**Decision:** Python 3.12/FastAPI + React 18/TypeScript/Vite + PostgreSQL 16
**Rationale:** Claude Agent SDK is Python-native. FastAPI async-first aligns with async SDK and httpx. React for dashboard-heavy UI with TanStack Query for server-state. PostgreSQL JSONB for flexible ON24 API response storage + materialized views for KPIs.

## 2026-03-11: No Redis/Celery
**Decision:** Background tasks via asyncio within FastAPI, not separate worker
**Rationale:** At current scale, async background tasks suffice. PostgreSQL materialized views handle caching. Avoids infrastructure complexity. Can add Redis later if real-time pub/sub needed.

## 2026-03-11: ON24 API Rate Limiting Strategy
**Decision:** Token bucket per endpoint category (6 tiers: 10-1000 req/min)
**Rationale:** ON24 has varying rate limits per endpoint type. A single global limiter would be too conservative for high-limit endpoints and too aggressive for low-limit ones. Category detection via URL path keywords.

## 2026-03-11: JSONB Raw Storage Pattern
**Decision:** Store full ON24 API responses in `raw_json` JSONB column alongside extracted typed columns
**Rationale:** ON24 API evolves (currently on v65.0.0). Typed columns serve queries and indexes; JSONB preserves data we haven't modeled yet, enabling future feature additions without re-syncing historical data.

## 2026-03-11: Upsert Strategy
**Decision:** PostgreSQL INSERT...ON CONFLICT DO UPDATE for all sync operations
**Rationale:** Idempotent syncs — re-running a sync safely updates existing records without duplicates. Uses composite unique constraints (e.g., on24_attendee_id + on24_event_id) for correctness.

## 2026-03-11: Docker Architecture
**Decision:** 3 containers only (postgres, backend, frontend). No nginx reverse proxy in dev.
**Rationale:** Minimal complexity. Frontend Dockerfile uses multi-stage build (node build + nginx serve) for production. Vite dev server proxies /api and /ws to backend. Backend serves FastAPI directly.

## 2026-03-11: Visualization Libraries
**Decision:** Recharts (primary) + Plotly (complex analytics)
**Rationale:** Recharts is React-native and composable, covers 80% of dashboard charting. Plotly fills gaps for heatmaps, sankey diagrams, 3D scatter. Avoiding raw D3 — too low-level for production timeline.
