# Architecture Decisions

## 2026-03-11: Agent Framework
**Decision:** Claude Agent SDK (Python), not Claude Code Skills
**Rationale:** Skills are CLI-only markdown instructions, not deployable services. Agent SDK provides programmatic Python API, custom MCP tools, concurrent multi-user support, and runs inside FastAPI process.

## 2026-03-11: Tech Stack
**Decision:** Python/FastAPI + React/TypeScript + PostgreSQL
**Rationale:** Claude Agent SDK is Python-native. FastAPI async-first aligns with async SDK. React for dashboard-heavy UI. PostgreSQL JSONB for flexible ON24 API response storage.

## 2026-03-11: No Redis/Celery
**Decision:** Background tasks via asyncio within FastAPI, not separate worker
**Rationale:** At current scale, async background tasks suffice. PostgreSQL materialized views handle caching. Avoids infrastructure complexity.
