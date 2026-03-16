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

## Poll Schema Findings (2026-03-12, REVISED)
- question_type_cd values: singleoption/multioption (polls — active, running regularly), singletext (Q&A)
- question_subtype_cd: userquestion / useranswer (Q&A self-join: answer_id → question_id)
- event_user_x_answer.answer contains answer text directly (question_x_answer not needed for responses)
- Client 10710 has active poll data — polls happen regularly across events
- dw_event_session.answered_polls is a Y/N flag, not a count; answered_surveys and asked_questions same pattern
- CRITICAL: Cross-table poll queries MUST use event-first CTE pattern (find events by goodafter first, then join to poll data) — starting from event_user_x_answer (334M rows) causes 8s timeout

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

## Phase 8 Addendum 8: How Do I Sub-menu + Feedback Footer — COMPLETE (2026-03-11)
- [x] "How do I...?" suggestion tile on home page → shows 8 platform how-to options as sub-menu
- [x] Sub-menu replaces main suggestion grid when clicked; back button returns to main view
- [x] Options: set up webinar, polls, registration page, integrations, analytics, Engagement Hub, presenter prep, Connect integrations
- [x] Replaced "speakers" and "email notifications" options (poor KB coverage) with "prepare as presenter" and "Connect integrations" (strong coverage)
- [x] Removed "Content performance insights" from main suggestions (not calculable); replaced with "Poll results overview"
- [x] Thumbs-down feedback form: added footer text — "Your suggestion will inform LLM refinement. Saved to improvement-inbox.txt"
- [x] Knowledge base coverage verified: 6/8 options have strong ChromaDB article coverage

## Phase 8 Addendum 9: Help Mode Suggestions + Empty Poll Handling — COMPLETE (2026-03-11)
- [x] Help mode suggestions: when agent_used="knowledge_base", generate help-center-focused follow-up chips (how-to questions) instead of data/analytics suggestions
- [x] Data escape chip: always append "Explore my event data" as the last suggestion chip in help mode to let users switch back to data mode
- [x] Empty poll handling: data agent responds "No poll results for [event title]." instead of generic "None found." when get_polls returns empty for a specific event
- [x] Guaranteed poll chip: when response contains "no poll results for", inject "Show polls for the most recent event that had polls" as first suggestion

## Phase 8 Addendum 10: Q&A, Company Query, Calendar KPIs — COMPLETE (2026-03-12)
- [x] get_audience_companies: event_id param for per-event scoping; email domain fallback when company blank; exclude param for filtering internal orgs
- [x] Calendar KPI aggregation: dw_event_session JOIN now uses SUM(registrant_count)/SUM(attendee_count) grouped by event — was returning NULL for multi-session events
- [x] Calendar: always show Registrants/Attendees KPIs for past events (even if 0) — removed truthy-only guard
- [x] Calendar: filter out events with <6 registrants (same rule as agent queries); future events always shown regardless
- [x] Event card on get_event_detail: triggers event_card rendering in chat (was only on compute_event_kpis)
- [x] Rename TopNav to "ON24 Nexus"
- [x] Poll chart suppresses poll cards (chart takes precedence over card rendering)

## Phase 8 Addendum 11: Multi-Event Card Grid — COMPLETE (2026-03-11)
- [x] list_events returning 2–4 results now captured as `event_cards` in data_agent.py
- [x] event_cards discarded if agent called tools other than list_events/generate_chart_data after (intermediate lookup, not final answer)
- [x] orchestrator.py passes event_cards through to chat.py
- [x] chat.py sends `event_cards` WS message type when present
- [x] useChat.ts: added `eventCards?: any[] | null` field to ChatMessage interface; handles `event_cards` WS message
- [x] ChatMessage.tsx: EventCardsGrid component — 2-col grid with 20px gap for 2–4 events (title, event_id, date, event_type)
- [x] data_agent.md: prompt rule — when list_events returns 2–4, output count line only; cards render automatically
- [x] Explored smart_tips_benchmark: not found as table or materialized view via ON24_RO user (likely in a restricted schema or different DB)

## Phase 9: AI-ACE Content + KB Migration + Agent Scope — COMPLETE (2026-03-13)
- [x] ChromaDB → Postgres + OpenAI embeddings: knowledge_base_articles table (REAL[] embedding), text-embedding-3-small, numpy cosine similarity; migration 0002
- [x] Removed chromadb dependency; added openai + numpy to pyproject.toml
- [x] OPENAI_API_KEY added to Settings config; 637 articles / 2729 chunks ingested
- [x] AI-ACE content (video_library WHERE source LIKE 'AUTO%') shown in calendar event detail and chat event card
- [x] Calendar AI-ACE tile: article type dropdown (Blog/eBook/FAQ/Key Takeaways/etc.), Key Takeaways → 4 section tabs (Summary/Takeaways/Quote/Other), Media Manager deep link per type
- [x] Backend parses keytakeaways HTML into sections using BeautifulSoup (server-side, reliable)
- [x] Calendar: avg_engagement_score KPI tile (dw_attendee AVG); scrollbar only inside key takeaways content
- [x] Home page tile "Event data exploration" → sends "What is the event ID?" to chat
- [x] Scope enforcement added to all 4 agent system prompts (politely refuse off-topic)
- [x] Home page: 8 color-coded tiles by agent (data=indigo, concierge=amber, config=emerald)
- [x] "Experiences" tile: chip sub-menu with ON24 experience deep links (Elite, Hub, Target, GoLive)
- [x] "Configure environment" tile: chip sub-menu (Media Manager, Segment Builder, Connect, Branding, Users)
- [x] data_agent.md: event card rule — output only identifier line when card renders (no text narration)
- [x] Orchestrator routing: route_to_config + route_to_concierge stubs added
- [x] ON24_Grounding.docx added to repo (data/)

## Phase 9 Addendum: Concierge Agent + Chip Navigation — COMPLETE (2026-03-13)
- [x] Renamed agent attribution from "knowledge_base" → "concierge" (orchestrator.py, chat.py)
- [x] Concierge prompt overhaul: self-contained answers from KB content, no links by default, conversational tone
- [x] Links banned from concierge responses unless user explicitly asks; max 200 words
- [x] Chip structure changed: 2 LLM context chips + 2 agent-switch chips (per other agent) + "Home" = 5 total
- [x] Agent-switch chips by agent: concierge→["Explore my event data","Content performance insights"]; data→["How do I...?","Content performance insights"]; content→["Explore my event data","How do I...?"]
- [x] "Home" chip → calls resetChat() (clears chat, returns to welcome screen)
- [x] "How do I...?" chip → opens how-to sub-menu (no message sent)
- [x] Audience companies: `months` param exposed in tool schema; cross-event default = 1 month (30 days); agent instructed to state time period in title line
- [x] Auto-restart backend after every backend commit (new workflow rule)

## Phase 9 Addendum 2: Brand Voice + Docs + Bug Fixes — COMPLETE (2026-03-13)
- [x] brand_voice.py service: analyze AUTOGEN_ video_library content per type → LLM → data/brand_voice.json
- [x] Monthly web scraping: COMPANY_WEBSITE_URL env var; discover blog/news pages; merge voice signals
- [x] get_recent_articles(): returns last N articles of a given type (TRANSCRIPT excluded)
- [x] config.py: COMPANY_WEBSITE_URL setting added
- [x] main.py: refresh_brand_voice() background task on startup (non-blocking, stale check 30 days)
- [x] content_agent.py: detect content-creation requests; silently inject brand voice + last 5 examples into system prompt
- [x] content_agent.md: brand voice usage rules — follow silently, do not mention to user
- [x] MRD, PRD, Tech Spec HTML docs: light/dark mode via ?theme=light URL param + toggle button
- [x] ChatSidebar: removed "Recent Chats" section
- [x] BUG FIX: chips never sent for concierge responses — NameError (bot_response → response_text) silently swallowed by except block
- [x] Chip safety: fallback to switch_chips + Home even when LLM returns malformed JSON
- [x] COMPANY_WEBSITE_URL: add to .env.local to enable monthly web brand voice updates

## Phase 9 Addendum 3: Security Hardening + Content Articles + Calendar Polish — COMPLETE (2026-03-13)
- [x] OWASP security hardening:
  - Security headers middleware (X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy) in main.py
  - Prompt injection: strip null bytes + ASCII control chars (0x00–0x08, 0x0e–0x1f) before processing in chat.py
  - SSL cert temp files: `shutil.rmtree` in `finally` blocks in on24_db.py + on24_hierarchy.py
  - Hierarchy auth: /api/hierarchy/children/{client_id} validates against deployment hierarchy before returning
  - ClientContext.tsx: removed hardcoded DEFAULT_CLIENT_ID=10710; fetches root from /api/hierarchy on mount
  - pool.fetch → async with pool.acquire() pattern in query_ai_content
- [x] Content articles display pipeline:
  - data_agent.py: captures `get_ai_content` result as `content_articles`
  - orchestrator.py: passes content_articles through to chat.py
  - chat.py: sends `content_articles` WS message type
  - useChat.ts: handles content_articles WS message; adds to ChatMessage interface
  - ChatMessage.tsx: ContentArticlesInline component with DOMPurify sanitization, type badges, collapsible content, Media Manager link
  - DOMPurify 3.3.3 + @types/dompurify added to frontend/package.json
- [x] Content agent article writing:
  - content_agent.md: call `get_ai_content` FIRST for all creation requests (not analytics tools)
  - Attribution sentence required; competitor references OK (factual)
  - Content guardrails: no inflammatory, no code, max 800/150/300 words by type
  - "Media Manager" terminology enforced (not "video library")
- [x] `query_ai_content` source filter fix: `LIKE 'AUTOGEN_%'` → `LIKE 'AUTO%'` (aligns with calendar.py); removed overly strict `media_content IS NOT NULL AND LENGTH > 50` filter; client_id removed from SELECT; pool.acquire pattern; return keys: `content`/`event_id`/`created_at`
- [x] Calendar PerformanceSection: collapsed by default when AI-ACE content is present; click to expand; chevron rotates
- [x] "Propose content calendar" chip: added to showExploreContent panel at same level as Create/Explore; sends calendar generation request to content agent
- [x] Content agent calendar rules: 3-month default, max 12 months (never exceed); analyze_topic_performance + analyze_scheduling_patterns; TOFU/MOFU/BOFU balance (40/35/25); normalized engagement = avg_engagement/60×scale; 5 refinement options after presenting
- [x] Tech Ops document: background agent creating frontend/public/docs/tech-ops.html + ChatSidebar link (in progress)
- [x] Security/accessibility test suite: background agent creating backend/tests/test_security.py + backend/tests/test_accessibility.py (in progress)

## Phase 9 Addendum 4: Proposed Calendar Mode + MCP Server Plan — COMPLETE (2026-03-13)
- [x] Proposed calendar mode: openProposedCalendar() in ChatContext (separate from openCalendar)
- [x] EventCalendar proposedMode prop: back navigation disabled at current period; resets to today on open
- [x] "Show existing events" toggle (default off): shows real future ON24 events when on, hides all when off
- [x] "Proposed Calendar" badge in toolbar; past events always hidden in proposed mode
- [x] "View proposed calendar" chip uses openProposedCalendar(); "Recent events" unchanged
- [x] Orchestrator two-step flow: propose_content_calendar tool → data agent gathers analytics → content agent synthesizes calendar
- [x] "View proposed calendar" chip auto-injected on content calendar responses
- [x] sendMessage(content, displayText?) — display text in chat differs from LLM payload
- [x] ON24 MCP server plan written: docs/superpowers/plans/2026-03-13-on24-mcp-server.md
- [x] MCP server scaffold under way (background agent building on24-mcp/)
- [x] API vs DB benchmark report under way (background agent)

## Phase 10: Documentation + Accessibility + Security — COMPLETE (2026-03-14)
- [x] Test plan doc (test-plan.html): dashboard metrics, pass rate by subsection, failure details, 10 test file sections
- [x] Scalability doc (scalability.html): 2K–6K concurrent user analysis, bottlenecks, recommended architecture, k6/Locust load test plan
- [x] Security review doc (security-review.html): 15 findings (0 critical, 3 high, 5 medium), OWASP Top 10 matrix, AI-specific security, remediation plan
- [x] Accessibility VPAT doc (accessibility-vpat.html): WCAG 2.1 Level A+AA criteria tables, remediation tracking (9 fixed, 4 open)
- [x] API vs DB benchmark doc (api-vs-db-benchmark.html): placeholder for 3-way comparison results
- [x] ChatSidebar: separate doc links → Documents dropdown (8 entries, chevron toggle, outside-click close)
- [x] ChatSidebar: theme param always passed (?theme=light or ?theme=dark) to all doc links
- [x] ChatPanel: "Poll results overview" → "Poll trends" moved to Trends sub-menu; "Create Content" replaces on home grid
- [x] Tech spec: added MCP Section 5 (architecture, data access strategy), MCP+REST API boxes in SVG diagram
- [x] WCAG 2.1 AA fixes: skip link, focus-visible outlines, aria-live regions, aria-expanded, contrast fix (#94a0b8), chat labels, chart roles, DOMPurify on calendar HTML
- [x] VPAT regenerated: 9 criteria upgraded from Partially Supports to Supports

## Phase 11: Infrastructure + Admin Simulation — COMPLETE (2026-03-14)
- [x] Backend tests for on24_query_tools — 53 tests with mocked asyncpg pool
- [x] Frontend Vitest component tests — 23 tests (KPICard, ErrorState, LoadingState, AgentIndicator)
- [x] Frontend Playwright E2E tests — 8 tests (app load, chat, calendar, docs, a11y)
- [x] dw_lead query tools — query_leads + query_lead_stats with tool schemas
- [x] Persona regression test runner — 300 prompts (200 marketer + 100 director)
- [x] CLAUDE.md compacted 198→47 lines; .ai/architecture.md created
- [x] Gunicorn 5 workers × 3 DB conns (capacity ~25-50 concurrent users)
- [x] Anthropic prompt caching — cache_control ephemeral on all 6 messages.create calls
- [x] Redis response cache — 2-min TTL, SHA256 key, data/concierge agents only
- [x] Simulated Admin dropdown — TopNav select with permissions from admin_property_info
- [x] Permission-based UI filtering — sessionStorage, home tiles + config + experiences filtered
- [x] Content agent topic suggestions — MANDATORY when no topic given, no clarifying questions
- [x] Orchestrator routing — content before data, numbered selection support
- [x] Calendar print fix — visibility-based CSS (was blank page due to child selector)
- [x] Dark mode fixes — input text, cursor, status indicator colors
- [x] CSP fix for docs — inline scripts for theme detection
- [x] 7 pre-existing test failures fixed (auth headers, security tests)

## html-docs Skill Creation — COMPLETE (2026-03-15)
- [x] SKILL.md: full template (~300 lines), auto-discovery per doc type, responsive CSS, dark mode
- [x] README.md: marketing/adoption page alongside SKILL.md
- [x] Document registration: doc-manifest.json for external docs wired into nav
- [x] Nav exclusion: `"nav": false` hides docs from dropdown while keeping them accessible
- [x] Regenerated test-plan.html with fresh pytest data (260 tests, 11 files, 5.0s)
- [x] Updated recent-changes.html with latest capabilities
- [x] Created doc-manifest.json for existing project docs

## HTML Content Modal + Email Service — COMPLETE (2026-03-15)
- [x] Content agent: _extract_html() from fenced ```html blocks + density fallback
- [x] Content agent: _sanitize_html() strips script/iframe/form/on*/javascript: URLs
- [x] Orchestrator: propagates content_html through content agent routing paths
- [x] chat.py: content_html WS message type + server-side HTML/JS input rejection
- [x] Frontend: ContentHtmlPreview chip + sandboxed iframe modal (copy/print/share icons)
- [x] Frontend: DOMPurify sanitization, img support, responsive image CSS
- [x] Frontend: client-side input validation (strip HTML tags, reject script injection)
- [x] Modal a11y: role="dialog", aria-modal, aria-labelledby, Escape to close
- [x] Email service: SendGrid (preferred) or Gmail SMTP fallback
- [x] Daily improvement digest: 11:59 PM email with improvement-inbox-*.txt attached
- [x] Fix: event card Decimal serialization, get_ai_content media_name column error

## Brand Templates + Social Media — COMPLETE (2026-03-15)
- [x] Brand templates: CRUD API with JSON file storage, 25 Google Fonts, default fallback
- [x] BrandTemplateManager modal: color pickers, font dropdown, logo URL, default toggle
- [x] "Brand Templates" tile in Configure environment sub-menu
- [x] ContentHtmlPreview: template dropdown applies selected template to iframe content
- [x] Social media prompt: emojis, hashtags, platform-specific lengths (LinkedIn/X/FB/IG)
- [x] Post links: compose/share URLs for LinkedIn, X, Facebook

## Content Sharing & Approval Workflow — COMPLETE (2026-03-15)
- [x] Backend: 3 new tables (content_shares, share_recipients, share_comments), migration 0003
- [x] Backend: 4 API endpoints (POST /shares, GET /shares/{id}, POST respond, POST comments)
- [x] Backend: HMAC-SHA256 token generation (salt+share_id+email+admin_id+created_at), 7-day expiry
- [x] Backend: Email to recipients via SendGrid/Gmail with styled review link
- [x] Frontend: Share icon → email input form in modal → POST /api/shares
- [x] Frontend: Standalone /share/:shareId review page (outside DashboardLayout)
- [x] Frontend: 5-star rating, thumbs up/down approval, comment thread, recipients status
- [x] Frontend: "Approved" badge when all recipients approve

## Security Remediation (Mar 15 audit) — COMPLETE (2026-03-15)
- [x] SEC: Replace regex HTML sanitizer with nh3 (Rust-based allowlist)
- [x] SEC: Email address validation — strict regex, CRLF rejection
- [x] SEC: Attachment path traversal guard — /app/data only
- [x] SEC: Control-char stripping in HTTP fallback validator
- [x] SEC: Gmail SMTP runs in asyncio.to_thread (non-blocking)
- [x] A11y: Modal role="dialog", aria-modal, aria-labelledby
- [x] Image support: DOMPurify allows img tags, responsive CSS, sandbox allow-same-origin
- [x] 287 tests total (25 new: 12 content_html + 8 email + 4 security input + 1 sanitizer)

## Data Prefetch + Performance — COMPLETE (2026-03-15)
- [x] Data prefetch service: warm Redis cache on startup (15-min TTL)
- [x] Prefetched: recent 10 events (details + KPIs), Key Takeaways, AI content (6 types), attendance trends
- [x] All prefetch queries run in parallel via asyncio.gather()
- [x] /api/prefetch/* endpoints: instant cached data, no LLM roundtrip
- [x] Response time profiling test suite (8 prompts, severity tracking)

## Performance + Bug Fixes — COMPLETE (2026-03-15)
- [x] PERF: Switch all 4 agents from claude-opus-4-6 to claude-sonnet-4-6 (40-60% latency reduction)
- [x] PERF: Increase response cache TTL from 120s to 300s (5 min)
- [x] FIX: Route AI-generated content requests to Data Agent (was rejected as out-of-scope)
- [x] FIX: Deduplicate AI content — keep longest article per (event_id, content_type)
- [x] FIX: Suppress AI content text narration — cards render automatically (no duplicate)
- [x] FIX: Social media content lookup — add 10+ type aliases + normalize input
- [x] FIX: Key Takeaways tabs — prefer longest KEYTAKEAWAYS article per event
- [x] "Suggest something" chip + follow-up email added to Create Content menu

## Welcome Admin UX — COMPLETE (2026-03-15)
- [x] Welcome admin by first name on home page greeting
- [x] "Login as:" label added to admin dropdown in TopNav

## Backlog / Next Steps
- [x] Documents dropdown nav on each HTML doc — doc-nav.js shared script, commit c3f764a
- [x] Agent permission awareness — restriction context injected into all agents, commit 2f616c8
- [x] Reload admin dropdown when client_id changes via breadcrumb — watches selectedClientId, commit edaf511
- [x] Populate api-vs-db-benchmark.html — added Section 7 listing all actively used REST endpoints with reasons
- [x] Technical contact lookup on home page — GET /api/technicalrep, shows first 3 names, commit f0829b9
- [x] Fix concierge no-response for "what helper endpoints in REST?" — removed tools from KB followup call, commit d8a4d58
- [x] manage-forums-lite — no UI link to filter (Forums not in EXPERIENCE_LINKS/CONFIG_LINKS); permission tag shows correctly
- [x] Enhance test coverage — 13 response_cache tests (cache key, get, set, close, Redis unavailable)

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
