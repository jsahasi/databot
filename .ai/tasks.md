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

## Phase 8 Addendum 3: Dark Mode + Charts + Polish — COMPLETE (2026-03-12)
- [x] Dark mode color tuning: softer white (#c9cfe0), lighter primary (#a5b4fc)
- [x] Dark mode table fix: ChatMessage.tsx all hardcoded colors → CSS variables (th/td/hr/blockquote/code)
- [x] Chip text brightness: #a5b4fc → #c7d2fe in dark mode
- [x] generate_chart_data tool: registered in DATA_AGENT_TOOLS, made async (was sync → await fail)
- [x] data_agent.md: explicit chart instructions per tool with x_key/y_keys/title
- [x] data_agent.md: stronger no-thinking-out-loud rule; count ≤20 may offer "Would you like me to list them?"
- [x] Suggestion chips: exclude region/geography (data not available)
- [x] Poll tenant isolation: event_user_x_answer → question → event → client_id chain
- [x] Decimal/datetime serialization: _serialize() on all query return values
- [x] query_attendance_trends default: 1 month → 12 months
- [x] Message queue: type+send while agent processes; auto-sends on completion
- [x] Frontend rebuild required after every change (nginx production build, no hot-reload)
- [x] Regression test suite: tests/test_chat_prompts.py (26 prompts, 22/26 passing — 4 skipped as known data gaps)
- [x] Known data gaps (auto-skipped): poll_overview, poll_overview_performance, polls_last_event (no poll responses since 2023), resources_last_event (zero resource_hit_track rows)

## Phase 8 Addendum 4: Regression Tests All Green — COMPLETE (2026-03-12)
- [x] chart_attendance_trends_line: generate_chart_data made async (was sync → await fail)
- [x] chart_top_events_bar: chart generation confirmed working end-to-end
- [x] content_topics_next: content agent topic suggestions passing
- [x] resources_last_event: moved to KNOWN_DATA_GAPS (zero rows in resource_hit_track for client 10710)
- [x] Ralph loop complete: 22 passed, 4 skipped (all non-data-gap tests pass)

## Poll Schema Findings (2026-03-12)
- question_type_cd values: singleoption/multioption (polls, stopped 2023), singletext (Q&A, active)
- question_subtype_cd: userquestion / useranswer (Q&A self-join: answer_id → question_id)
- event_user_x_answer.answer contains answer text directly (question_x_answer not needed for responses)
- Client 10710 has 86 poll questions (2021-2023) with zero responses in event_user_x_answer
- dw_event_session.answered_polls is a Y/N flag, not a count; answered_surveys and asked_questions same pattern
- Full dw_event_session columns documented in schema section above

## Local Setup Notes
- **App URL**: http://localhost:3001 (via `docker compose up --build`)
- **Postgres host port**: 5433 (internal container port remains 5432; only host mapping changed)
- **ON24 DB**: requires VPN or ON24 internal network (10.3.7.233 not reachable externally)
- **Active ON24 DB**: PROD — 10.3.7.233:5458/on24master (not QA port 5459)

## Phase 8 Addendum 5: Feedback Loop + Company Dedup — COMPLETE (2026-03-12)
- [x] Thumbs up/down hover buttons on each bot assistant message
- [x] Thumbs-down opens inline popup: "Tell me what I got wrong"
- [x] POST /api/feedback — backend/app/api/feedback.py
- [x] Negative feedback written to data/improvement-inbox-MM-DD-YYYY.txt
      as structured LLM-ready prompt with timestamp, agent, user question, bot response
- [x] data/ folder mounted as Docker volume (persists outside container)
- [x] Company dedup in get_audience_companies: GROUP BY LOWER(TRIM(company)),
      display most common casing via MODE()

## Phase 8 Addendum 6: Calendar + Pie Charts + Poll Fix — COMPLETE (2026-03-11)
- [x] Pie chart support: backend `generate_chart_data` with chart_type="pie" → {name, value} pairs; frontend Recharts PieChart/Pie/Cell renderer
- [x] Audience sources: `query_audience_sources` tool using `event_user.partnerref`; pie chart; empty list → "None found."
- [x] Context-aware suggestion chips: never suggest current view (bar/line/pie/table); haiku prompt told explicit view type
- [x] Feedback enhancements: client_id in each report; diagnostic questions about data discovery; appends same day, new file on date change
- [x] Event Calendar: Outlook-style modal (EventCalendar.tsx); month/week view toggle; prev/next navigation; event detail side panel
- [x] Calendar API: GET /api/calendar?year=&month=, GET /api/calendar/event/{id}; goodafter/goodtill as start/end; KPIs for past events only
- [x] Calendar event detail: event_id, title, abstract, date/time, registrants, attendees, conversion rate, poll responses, survey responses, resource downloads (nonzero only); card layout
- [x] Poll response dedup: COUNT DISTINCT event_user_id (users may re-submit same poll)
- [x] "Show event calendar" suggestion tile on home page → opens modal (not chat)
- [x] Calendar icon in TopNav → opens calendar modal
- [x] Poll query rewrite: proper join chain event_x_media_url → media_url → media_url_x_question → question → question_x_answer → event_user_x_answer; EXMU.SESSION_ID=1; excludes test/survey URLs; supports open-text questions with sample answers
- [x] Orchestrator history rollback: if agent call fails after tool_use is appended, pop dangling entries to prevent corrupt history on subsequent calls
- [x] Per-test session IDs in regression tests: each test uses `test-{prompt_id}` to isolate conversation history
- [x] Resource downloads fix: switched from `resource_hit_track` (zero rows) to `content_hit_track_details` (action='TotalHits') with display_profile/display_element filter for resource-list widgets; also updates calendar event detail
- [x] `resources_last_event` removed from KNOWN_DATA_GAPS (now expected to have data)

## ON24 Platform Analytics Links (Reference)
Built-in ON24 reporting — agent directs users to these as jumping-off points:
- **Dashboard**: wcc.on24.com/webcast/dashboard
- **Smart Tips**: wcc.on24.com/webcast/keyinsightssummary
- **Webcast Elite**: wcc.on24.com/webcast/reportsdashboard
- **Engagement Hub**: wcc.on24.com/webcast/portalsummaryreports
- **Target**: wcc.on24.com/webcast/targetAnalytics
- **Go Live**: wcc.on24.com/webcast/virtualeventsummary
- **Power Leads**: wcc.on24.com/webcast/leadsreports
- **Segments**: wcc.on24.com/webcast/segmentationsummary
- **Funnel**: wcc.on24.com/webcast/funnelaudience
- **Accounts**: wcc.on24.com/webcast/accountengagement
- **Documents**: wcc.on24.com/webcast/documentsanalytics
- **Videos**: wcc.on24.com/webcast/videolibraryanalytics
- **Webpages**: wcc.on24.com/webcast/webpagessummary
- **Polls & Surveys**: wcc.on24.com/webcast/pollsreport
- **Buying Signals**: wcc.on24.com/webcast/buyingsignals
- **Presenters**: wcc.on24.com/webcast/funnelpresenters
- **Benchmarking**: wcc.on24.com/webcast/benchmarking

## Phase 8 Addendum 7: Poll Fix + Event Cards + Knowledge Base + Calendar Day View — COMPLETE (2026-03-12)
- [x] Poll query fix: removed broken event_x_media_url + SESSION_ID=1 join chain; simplified to event_user_x_answer → event_user → media_url (matches working calendar.py pattern)
- [x] query_top_events_by_polls: now ranks by actual poll respondents (not just questions)
- [x] query_poll_overview: uses response-based join (not question table alone)
- [x] All poll tests removed from KNOWN_DATA_GAPS (data exists with fixed queries)
- [x] Poll display cards: PollCardsInline component — horizontal bars for multiple-choice (% + count), sample answer tags for freetext
- [x] Event card in chat: EventCardInline component — inline KPI card when data agent queries single event via compute_event_kpis
- [x] Calendar double-click to chat: double-click event → sends "Tell me about event {id}" to chat + closes calendar
- [x] Calendar Day view: single-column timeline with full event detail, zoom +/- icons (Month ↔ Week ↔ Day)
- [x] Custom tooltips: fixed-position Tooltip component (z-index 9999, never clipped by overflow:hidden)
- [x] Calendar modal enlarged: 96vw x 95vh, maxWidth 1600
- [x] Knowledge base tool: orchestrator's search_knowledge_base queries ChromaDB for "how do I" questions
- [x] No-hallucination rule: orchestrator MUST only cite knowledge base articles; if none found, redirect to ON24 Help Center
- [x] ON24 speakers: documented — added as card on registration page + Speaker Bio tool on Audience Console via Console Builder

## Backlog / Next Steps
- [ ] Add query tools for dw_lead (lead/prospect analytics)
- [ ] Add backend tests for on24_query_tools (mock asyncpg pool)
- [ ] Frontend Vitest component tests + Playwright E2E
- [ ] Multi-client: implement per-request context var for tenant ID
- [ ] Recent Chats: persist chat history in localStorage
- [ ] Marketer + director regression test prompts (300 total in marketer_prompts.json + director_prompts.json)

## Verified ON24 Schema (on24master)

> **Active connection: PROD — 10.3.7.233:5458** (switched from QA port 5459 on 2026-03-11)
> Env var: `ON24_DB_URL` in `.env.local`. The `_QA` suffixed entries are not used by the app.

### Key Tables
| Table | Rows | Notes |
|-------|------|-------|
| event | ~7.4M | Filter by client_id; goodafter = event date; title is in `description` column (not event_name) |
| event_user | 585M / 404GB | Registrants — avoid for aggregates; join through event |
| dw_attendee | 262M | Per-attendee: event_user_id, engagement_score, live_minutes, archive_minutes |
| dw_event_session | — | Per-event aggregate. Key columns: registrant_count, attendee_count, engagement_score_avg, conversion_percent, live_attendee_count, od_attendee_count, live_attendee_mins, od_attendee_mins, answered_polls (Y/N flag), answered_surveys (Y/N), asked_questions (Y/N), reminder/noshow/attendee email open rates |
| question | 47M | Poll/Q&A/Survey; text in `description` column (not question_text) |
| question_x_answer | — | Poll answer options |
| event_user_x_answer | 334M | Individual responses |
| resource_hit_track | 55M | Columns: event_id, event_user_id, resource_id, timestamp, partnerref |
| dw_lead | 105M | Leads; has client_id directly |
| client_hierarchy | — | Parent/child with self-refs; use cycle-safe recursive CTE |

### Sub-client hierarchy for 10710
[22355, 28516, 42835, 44220, 45077, 46851, 48673, 51429, 52909]
Total events: ~13,293 (10710: 11,517 + sub-clients: 1,776)
