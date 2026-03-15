# ON24 Nexus — AI-Powered Analytics Platform

Multi-agent application for exploring ON24 client webinar data (events, audiences, engagement) with data visualizations and conversational analytics. 11 development phases complete.

## Quick Start

```bash
cp .env.example .env.local   # Fill in secrets
docker compose up --build     # App: http://localhost:3001 | API: http://localhost:8000/docs
```

> Postgres host port: **5433** (not 5432). ON24 DB requires VPN (10.3.7.233:5458).

## Architecture

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async) | 5 gunicorn workers, Anthropic prompt caching |
| Frontend | React 18, TypeScript, Vite, Recharts | TanStack Query, Vitest + Playwright |
| Database | PostgreSQL 16 | Local (metadata/KB) + ON24 master DB (analytics, read-only) |
| AI Agents | Anthropic Claude Sonnet 4 | 4-agent system with multi-round tool_use loops |
| Cache | Redis 7 | Response cache (2-min TTL) for repeated queries |
| MCP Server | FastMCP (streamable-HTTP) | 67 ON24 REST API tools on port 8001 |

## Agent System

| Agent | Purpose | Tools |
|-------|---------|------:|
| Orchestrator | Routes intent, synthesizes responses, KB search | 6 |
| Data Agent | DB queries, KPIs, charts, leads, polls, tags | 20 |
| Content Agent | Topic suggestions, brand-voice content creation | 7 |
| Admin Agent | ON24 write operations (with confirmation flow) | 5 |

All queries are tenant-scoped: client 10710 + 9 sub-clients via `WHERE client_id = ANY(get_tenant_client_ids())`.

## Codebase

| Component | Lines |
|-----------|------:|
| Backend Python (`app/`) | 9,953 |
| Frontend TypeScript (`src/`) | 6,619 |
| MCP Server | 1,151 |
| Agent Prompts (`.md`) | 514 |
| HTML Documentation | 2,744 |
| **Total application** | **~21,000** |

## Test Suite

| Suite | Tests | Lines | Status |
|-------|------:|------:|--------|
| Backend unit (pytest) | 305 | 5,200 | All pass |
| Frontend Vitest (components) | 23 | 145 | All pass |
| Frontend Playwright (E2E) | 8 | 93 | All pass |
| Regression prompts (core) | 26 | 554 | All pass |
| Persona prompts (marketer + director) | 300 | 501 | Runner ready |
| **Total** | **662** | **5,409** | |

### Backend Coverage

| Area | Coverage | Notes |
|------|---------|-------|
| **Overall** | **39%** | Dragged down by unused ETL + REST client |
| Query tools (20 functions) | ~85% | 53 tests, mocked asyncpg pool |
| Models / schemas | 94-100% | Full ORM coverage |
| Rate limiter | 98% | Token bucket algorithm |
| Chart generation | ~95% | All 10 chart types tested |
| Security (OWASP) | ~80% | Input validation, tenant isolation, headers |
| ON24 REST client | 35% | 71 endpoints, write ops mostly untested |
| Sync service | 0% | ETL not in use (direct DB reads) |

## Key Features

- **Conversational analytics** — natural language to charts and data
- **10 chart types** — bar, line, pie, radar, funnel, gauge, treemap, scatter, heatmap, waterfall
- **Event calendar** — month/week/day views with KPIs and AI-ACE content tiles
- **Content creation** — brand-voice-aware blog posts, scripts, social media, eBooks
- **Proposed content calendar** — AI-suggested 3-month plans with TOFU/MOFU/BOFU balance
- **Knowledge base** — 637 articles + 71 API endpoints, vector search (OpenAI embeddings)
- **Lead analytics** — filterable lead search + aggregate stats from dw_lead (105M rows)
- **Permission-based UI** — simulated admin dropdown filters products by ON24 permissions
- **Agent permission awareness** — restricted products suppressed in agent responses, upsell with admin contacts
- **Prompt caching** — 90% input token discount via Anthropic ephemeral cache
- **Redis response cache** — 2-min TTL eliminates redundant LLM calls
- **Multi-tenant** — per-request client_id via contextvars, full sub-client hierarchy
- **Dark/light mode** — CSS variable theming, persisted to localStorage
- **WCAG 2.1 AA** — skip links, focus-visible, aria-live, contrast compliance
- **Feedback loop** — thumbs up/down saves LLM-ready improvement prompts to `data/improvement-inbox-*.txt`

## Documentation

9 HTML docs in [`frontend/public/docs/`](frontend/public/docs/) — accessible from the app sidebar and at these paths when running locally:

| Document | Path | Content |
|----------|------|---------|
| [MRD](http://localhost:3001/docs/mrd.html) | `/docs/mrd.html` | Market Requirements Document |
| [PRD](http://localhost:3001/docs/prd.html) | `/docs/prd.html` | Product Requirements Document |
| [Tech Spec](http://localhost:3001/docs/tech-spec.html) | `/docs/tech-spec.html` | Architecture, data access, MCP server |
| [Test Plan](http://localhost:3001/docs/test-plan.html) | `/docs/test-plan.html` | 336 tests, pass rates, coverage |
| [Scalability](http://localhost:3001/docs/scalability.html) | `/docs/scalability.html` | 2K-6K concurrent user analysis |
| [Security Review](http://localhost:3001/docs/security-review.html) | `/docs/security-review.html` | OWASP Top 10, 15 findings |
| [Accessibility VPAT](http://localhost:3001/docs/accessibility-vpat.html) | `/docs/accessibility-vpat.html` | WCAG 2.1 AA compliance |
| [API vs DB Benchmark](http://localhost:3001/docs/api-vs-db-benchmark.html) | `/docs/api-vs-db-benchmark.html` | REST vs MCP vs DB comparison |
| [Recent Changes](http://localhost:3001/docs/recent-changes.html) | `/docs/recent-changes.html` | Latest capabilities |

All docs support dark/light theme via `?theme=dark` URL parameter. Generated and maintained via the [`html-docs` Claude Code skill](~/.claude/plugins/local/user-skills/skills/html-docs/) — auto-discovers project state (test results, security patterns, infrastructure) and produces themed, responsive HTML.

## Commands

```bash
# Backend
cd backend && pip install -e ".[dev]"
pytest tests/ -v                              # 305 tests
pytest tests/ --cov=app --cov-report=term     # With coverage
ruff check app/ && ruff format app/

# Frontend
cd frontend && npm install
npx vitest run                                # 23 component tests
npx playwright test                           # 8 E2E tests
npm run typecheck && npm run lint

# Regression (requires running backend)
python -m pytest tests/test_chat_prompts.py -v        # 26 core prompts
python -m pytest tests/test_persona_prompts.py -v     # 300 persona prompts
python -m pytest tests/test_persona_prompts.py --max-prompts 10  # Quick smoke test
```

## Environment Variables

See `.env.example` for the full template. Key groups:

| Group | Variables |
|-------|----------|
| ON24 DB | `ON24_DB_URL`, `DB_PG_SSL_*` (3 cert vars) |
| ON24 API | `ON24_BASE_URL`, `ON24_ACCESS_TOKEN_KEY/SECRET`, `ON24_CLIENT_ID` |
| AI | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` |
| App DB | `DATABASE_URL`, `POSTGRES_PASSWORD` |
| Cache | `REDIS_URL`, `RESPONSE_CACHE_TTL` |
| MCP | `USE_MCP`, `USE_MCP_BLOCKLIST`, `MCP_SERVER_URL` |
