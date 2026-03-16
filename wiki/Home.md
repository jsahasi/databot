# ON24 Nexus / DataBot — Wiki Home

**ON24 Nexus** (internal codename: DataBot) is a multi-agent AI chat application for ON24 webinar analytics. It lets ON24 users ask natural-language questions about their event data, generate content (blogs, emails, social posts, content calendars), and manage events — all from a single conversational interface backed by four specialized AI agents.

- **Live app**: http://localhost:3001
- **API docs**: http://localhost:8000/docs
- **GitHub** (private): https://github.com/jsahasi/databot
- **GitLab**: https://gitlab.com/on24/data/pocs/data-agent

---

## Quick Start

```bash
# Prerequisites: Docker Desktop, .env.local with secrets (see Key Configuration)
docker compose up --build
# App:      http://localhost:3001
# API docs: http://localhost:8000/docs
```

The first boot pre-warms the cache (Trends, Explore Content, How-do-I chips). Subsequent responses for those prompts are served in under 1 second.

---

## Recent Fixes — 2026-03-16

The following bugs were identified and resolved on 2026-03-16:

1. **Blog post routing** — The orchestrator now always routes write/draft/create requests to the Content Agent, regardless of whether existing content might exist in Media Manager. The Content Agent has its own `get_ai_content` tool and handles both finding existing content and writing new drafts. Previously, some "based on my most recent event" phrasings incorrectly routed to the Data Agent.

2. **Admin agent defaults** — The Admin Agent no longer asks for timezone or event type on every event creation. It defaults to timezone=ET and event type=Webcast, and asks only one clarifying question at a time when genuinely required information is missing.

3. **Funnel chip: approximate TOFU/MOFU/BOFU classification** — The "Analyze funnel stages anyway" chip now sends a full instructional prompt with TOFU/MOFU/BOFU classification logic (approximated from event titles when no tags exist), rather than a bare label that hit a stale cached response.

4. **Chip labels: markdown bold markers stripped** — Suggestion chip labels no longer display raw `**bold**` markers. A display label map and a markdown-strip pass ensure users see clean short labels while the full instructional payload is sent to the LLM.

5. **Chip pre-warm expansion: all Trends chips** — The Trends sub-menu now has all 8 chips pre-warmed at startup (previously only 4 were covered). Added: Show funnel, Show campaigns, Performance by tags, Poll trends.

6. **Chip pre-warm expansion: all Explore Content types** — The Explore Content sub-menu now has all 6 types pre-warmed (previously only 4). Added: eBooks and FAQs. All Explore Content chips now respond in under 1 second after startup.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), Alembic, asyncpg |
| Frontend | React 18, TypeScript, Vite, TanStack Query, Recharts, Plotly |
| App Database | PostgreSQL 16 (Docker) |
| ON24 Database | ON24 production DB (read-only asyncpg pool, SSL, Google Cloud SQL) |
| Agent SDK | Anthropic Python SDK `messages.create()` with `tools` — NOT Claude Agent SDK |
| Cache | Redis 7 (response cache 5-min TTL, prefetch cache 15-min TTL) |
| Deployment | Docker Compose — 4 services: `backend`, `frontend` (nginx), `postgres`, `on24-mcp` |

---

## Architecture

### Agent System

Four agents are orchestrated via a single WebSocket connection (`/ws/chat`). The Orchestrator classifies intent and delegates to the appropriate specialist.

```
User Message
    │
    ▼
Orchestrator (claude-sonnet-4-6)
    ├── Data Agent      → DB queries, analytics, chart generation
    ├── Content Agent   → Blog / email / social / content calendar writing
    ├── Admin Agent     → Event creation/editing (requires confirmation)
    └── Concierge       → ON24 how-to answers from KB (637 articles)
```

| Agent | Model | Role | Max Tool Rounds |
|---|---|---|---|
| Orchestrator | claude-sonnet-4-6 | Intent classification, routing, KB search | — |
| Data Agent | claude-sonnet-4-6 | Analytics queries, charts, engagement data | 10 |
| Content Agent | claude-sonnet-4-6 | Content strategy, writing, calendar proposals | 8 |
| Admin Agent | claude-sonnet-4-6 | Event CRUD via ON24 REST API | 5 |
| Concierge | claude-haiku-4-5 (KB synthesis) | How-to answers from Zendesk/API knowledge base | — |

### Data Flow

```
Frontend (React/WebSocket)
    │  JSON frames
    ▼
FastAPI WebSocket handler  (backend/app/api/chat.py)
    │
    ├── Redis response cache (SHA256 key: prompt + client_id, 5-min TTL)
    │
    ▼
Orchestrator Agent
    │  tool calls
    ▼
Data Agent ──► asyncpg pool ──► ON24 production DB (read-only, SSL)
                              └─► App DB (audit logs, KB embeddings)
```

Charts are generated server-side via `generate_chart_data` and rendered client-side with Recharts (bar, line, pie, radar, funnel, gauge, treemap, scatter, heatmap, waterfall). HTML content previews open in a modal and are sanitized with **nh3** (Rust-based allowlist).

Share links use HMAC-SHA256 tokens with a 7-day expiry; review pages are served at `/share/:shareId`.

---

## Navigation Map

### Tier 1 — Home Chips

| Chip | Description |
|---|---|
| Recent Events | List of the client's most recent webinars |
| How do I...? | ON24 platform how-to (Concierge) |
| Experiences | Links to Elite / Engagement Hub / Target / GoLive |
| Configure Environment | Links to Media Manager, Segment Builder, Connect, Branding, etc. |
| Trends | Attendance, registrations, engagement, funnel, campaigns |
| Insights | AI-generated performance summaries |
| Create Content | Generate blog posts, emails, social posts, content calendars |
| Explore Content | Browse AI-generated content by type |

### Tier 2 — Sub-menus

| Tier 1 | Tier 2 Options |
|---|---|
| Trends | Attendance over time / Registrations / Engagement / Show funnel / Show campaigns / Performance by tags / Top events / Poll trends |
| Experiences | Elite / Engagement Hub / Target / GoLive (external links) |
| Configure | Media Manager / Segment Builder / Connect / Branding / Manage Users / Brand Templates |
| Create Content | Propose event calendar / Blog post / Social media / eBook / Webinar script / Follow-up email / For a specific event... |
| Explore Content | Key Takeaways / Blog Posts / eBooks / FAQs / Follow-up Emails / Social Media |
| How do I...? | 8 curated ON24 platform how-to questions |

### Tier 3 — Agent Responses

Agent responses, charts, HTML preview modals, and external ON24 platform links (e.g., `wcc.on24.com/webcast/` dashboards).

---

## Performance & Caching

| Mechanism | Detail |
|---|---|
| Response cache | Redis, SHA256(prompt + client_id), 5-min TTL |
| Prefetch cache | Redis, 15-min TTL — analytics for content calendar reduce 3 LLM calls to 2 |
| Startup pre-warm | Trends x4, Explore Content x4, How-do-I x8 → all served in <1s after boot |
| Concierge cache | Cold: ~3–5s; cached: <1s (Haiku model for KB synthesis) |
| DB pool | 5 gunicorn workers × 3 asyncpg connections = 15 total ON24 DB connections |
| Query timeout | 8s per asyncpg fetch; 60s pool command timeout |

**Default date window for all queries**: 1 month. Maximum: 24 months. Unbounded queries are never issued.

---

## Key Configuration / Environment Variables

Secrets live in `.env.local` (gitignored). See `.env.example` for the full template.

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Required for all agent chat |
| `OPENAI_API_KEY` | KB embeddings (text-embedding-3-small) |
| `ON24_DB_URL` | asyncpg DSN for ON24 production DB (SSL) |
| `DB_PG_SSL_CERT` / `DB_PG_SSL_KEY` / `DB_PG_SSL_ROOT` | SSL certs for ON24 DB connection |
| `DATABASE_URL` | App DB (overridden to local postgres in docker-compose) |
| `ON24_CLIENT_ID` | Root client: `10710` |
| `ON24_API_KEY` / `ON24_TOKEN_KEY` | ON24 REST API credentials (writes only) |
| `REDIS_URL` | Redis connection string |

> **VPN required** to reach the ON24 production DB at `10.3.7.233:5458`.

---

## Tenant Security Model

Tenant isolation is enforced at the data layer and never delegated to agents or users.

- `get_client_id()` returns the root client ID from `settings.on24_client_id` only — never from request context.
- `get_tenant_client_ids()` returns root + all sub-clients via a cycle-safe recursive CTE, cached in-process.
- All DB queries use `WHERE client_id = ANY($N::bigint[])` — never a single client ID.

**Root client 10710** has 9 sub-clients: `22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909`.

---

## Development Guide

### Running Tests

```bash
# Backend — 336 tests
cd backend && pytest tests/ -v

# Frontend unit/component — 23 tests
cd frontend && npx vitest run

# Frontend E2E (Playwright) — 8 tests
cd frontend && npx playwright test

# Linting
cd backend && ruff check app/ && ruff format app/
cd frontend && npm run typecheck && npm run lint
```

### Key Files

| File | Purpose |
|---|---|
| `backend/app/agents/orchestrator.py` | Intent routing, Concierge logic |
| `backend/app/agents/data_agent.py` | Analytics queries, chart tool calls |
| `backend/app/agents/content_agent.py` | Content generation, calendar proposals |
| `backend/app/api/chat.py` | WebSocket handler, suggestion chip generation |
| `backend/app/services/data_prefetch.py` | Startup pre-warm logic |
| `backend/app/services/response_cache.py` | Redis response cache |
| `frontend/src/components/chat/ChatPanel.tsx` | Main chat UI |
| `frontend/src/context/ChatContext.tsx` | Shared WebSocket state (React context) |

### Conventions

- **Models**: `TimestampMixin` + `to_dict()` + `raw_json JSONB` on all synced models
- **Upserts**: `INSERT...ON CONFLICT DO UPDATE` for idempotent sync operations
- **Config**: env vars via Pydantic Settings (`app/config.py`). Never hardcode secrets.
- **Frontend state**: TanStack Query for server state. `@/` alias maps to `src/`. No Redux.
- **Schemas**: Pydantic `ConfigDict(from_attributes=True)`. `PaginatedResponse[T]` for lists.
- **Admin actions**: Set `requires_confirmation=True` — the frontend shows a dialog before proceeding.

---

## Known Constraints & Data Notes

| Constraint | Detail |
|---|---|
| Event title | Stored in `description` column — not `event_name` |
| Event times | `goodafter` = start time, `goodtill` = end time — no `starttime`/`endtime` columns |
| Event aggregates | Use `dw_event_session` (registrant_count, attendee_count, engagement_score_avg) |
| Per-attendee data | Use `dw_attendee` — has `event_user_id`, engagement_score, live/archive minutes |
| Poll/survey text | `question.description` column; `question_type_cd` = `singleoption` / `multioption` |
| AI-ACE content | `video_library WHERE source LIKE 'AUTO%'` |
| `event_user` table | 585M rows / 404GB — **never join for aggregates**; always scope through event |
| Registrant count | No `num_registered` on `event` — use `dw_event_session.registrant_count` |
| Date window | Default 1 month, max 24 months — enforce in all new tool implementations |

---

## Development Phases

| Phase | Description |
|---|---|
| 1 | Foundation (FastAPI, DB, basic agent) |
| 2 | Frontend shell |
| 3 | Agent system (orchestrator + data agent) |
| 4 | Content agent |
| 5 | Admin agent, audit log |
| 6 | Direct ON24 DB access, tenant safety |
| 7 | dw_event_session queries, layout redesign |
| 8 | Knowledge base / Concierge |
| 9 | Redis caching, performance |
| 10 | Navigation tiers, chip pre-warm |
| 11 | Infrastructure, Admin Simulation, Content Calendar, T1/T2/T3 test plan |

---

## Related Documentation

- [Test Plan](test-plan) — Tier 1/2/3 coverage, 336 backend + 23 frontend + 8 E2E tests
- [Security Review](security-review) — Tenant isolation, HMAC share links, content sanitization
- [Scalability Notes](scalability) — DB pool sizing, Redis TTLs, query timeout strategy
- [Accessibility](accessibility) — WCAG 2.1 AA compliance, keyboard navigation, ARIA

---

*Last updated: 2026-03-16*
