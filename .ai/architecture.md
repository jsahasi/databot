# DataBot Architecture

## Data Access — Three Sources

| Source | Used for | Location |
|--------|----------|----------|
| ON24 master DB (on24master) | All analytics reads | `backend/app/db/on24_db.py` + `on24_query_tools.py` |
| ON24 REST API (apiqa.on24.com) | Write ops, full API client (71 endpoints) | `backend/app/services/on24_client.py` |
| MCP Server (on24-mcp) | External tool access via MCP | `on24-mcp/server.py` (67 tools) |

Prefer direct DB for reads. REST API for writes only.

## Agent System

4 agents, each a Python class with multi-round Anthropic tool_use loop (max 5 rounds):

| Agent | File | Purpose |
|-------|------|---------|
| Orchestrator | `orchestrator.py` | Classifies intent, delegates, synthesizes |
| Data Agent | `data_agent.py` | DB queries + KPI computation + charts (20 tools) |
| Content Agent | `content_agent.py` | Content insights + creation with brand voice |
| Admin Agent | `admin_agent.py` | ON24 write operations (5 tools) |

- Admin confirmation flow: `requires_confirmation=True` → frontend dialog → resend with `{"confirmed": true}`
- Audit logging: fire-and-forget to `agent_audit_logs` via `asyncio.create_task`
- Orchestrator history safety: on exception after tool_use, pop dangling entries to prevent corrupt history

## Key ON24 Tables

| Table | Notes |
|-------|-------|
| `event` | Filter by client_id; `goodafter` = start, `goodtill` = end; title in `description` column |
| `dw_event_session` | Pre-aggregated per-event: registrant_count, attendee_count, engagement_score_avg |
| `dw_attendee` | Per-attendee: engagement_score, live_minutes, archive_minutes |
| `dw_lead` | Leads with direct client_id; 105M rows |
| `event_user` | 585M rows — avoid for aggregates |
| `event_user_x_answer` | 334M rows — use event-first CTE pattern |
| `question` | Poll/Q&A/Survey; text in `description` column |

## Tenant Isolation (Critical)

- `get_client_id()` → root from config or per-request contextvar (never from agents/users)
- `get_tenant_client_ids()` → root + sub-clients via recursive CTE (cached)
- All queries: `WHERE client_id = ANY($N::bigint[])` — never single-ID filter
- Root client 10710 → 9 sub-clients: 22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909

## WebSocket Protocol (`/ws/chat`)

Client sends: `{"type": "message", "content": "...", "confirmed": false}`
Server message types: `agent_start`, `agent_routing`, `text`, `chart_data`, `confirmation_required`, `message_complete`, `error`, `reset`, `event_cards`, `content_articles`, `proposed_events`

## ON24 Platform Analytics URLs

See orchestrator prompt or CLAUDE.md `ON24 Analytics Platform — Existing Reporting Sections` table for full URL list.
Built-in reporting at `wcc.on24.com/webcast/` — agent redirects users there when appropriate.
