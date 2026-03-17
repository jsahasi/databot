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

## 2026-03-13: Concierge Agent Identity + Self-Contained Answers
**Decision:** Rename the KB-answering agent from "knowledge_base" to "concierge" in all attribution, chip logic, and code.
**Rationale:** "knowledge_base" describes an implementation detail (what tool it uses), not the agent's role. "Concierge" conveys the intent: a knowledgeable guide who answers questions directly.
**Answer format:** Concierge must give complete self-contained answers from KB article content — never link to Help Center as the primary answer. Links only if user explicitly asks. Max 200 words. No preamble.

## 2026-03-13: Brand Voice Service
**Decision:** Analyze client's AI-generated content (video_library AUTOGEN_ rows) with LLM to produce a per-type brand voice JSON document (`data/brand_voice.json`). Optionally enrich monthly from company website blog.
**Rationale:** Content agent needs client-specific voice guidelines to produce on-brand content. Using the client's own AI-ACE output as ground truth is more accurate than generic B2B style guides. Web scraping enriches with public-facing brand signals.
**Key rules:** TRANSCRIPT type excluded (too verbose, low signal); sample 8 articles per type for LLM analysis; refresh if >30 days old; COMPANY_WEBSITE_URL env var controls web enrichment; recent articles injected silently (never shown to user).

## 2026-03-13: Content Creation Context Injection
**Decision:** Content agent silently loads brand voice + last 5 same-type articles into system prompt when a content-creation request is detected (regex on "write/draft/create/generate" + content type keywords).
**Rationale:** Avoids requiring users to specify style — the agent automatically matches established voice. Examples provide concrete quality anchors. No tool call needed — injected directly into system prompt addendum.
**Detection defaults:** email → FOLLOWUPEMAI; social/linkedin → SOCIALMEDIAP; faq → FAQ; ebook → EBOOK; takeaway/summary → KEYTAKEAWAYS; blog/article → BLOG (default fallback).

## 2026-03-13: OWASP Security Hardening
**Decision:** Applied OWASP Top 10 mitigations across backend and frontend.
**Changes:**
- A05 Security Misconfiguration → HTTP security headers middleware in `main.py` (X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy)
- A03 Injection → strip null bytes + ASCII control chars from user input in `chat.py` before agent processing
- A02 Cryptographic Failures → SSL cert private keys written to temp dir and deleted immediately after loading into SSLContext (`shutil.rmtree` in `finally` blocks in `on24_db.py` and `on24_hierarchy.py`)
- A01 Broken Access Control → `/api/hierarchy/children/{client_id}` validates client_id is within deployment hierarchy before returning; `ClientContext.tsx` fetches root_client_id from API (no longer hardcoded in frontend bundle)
- A07 XSS → DOMPurify 3.3.3 sanitizes `media_content` HTML before `dangerouslySetInnerHTML` in `ContentArticlesInline`

## 2026-03-13: Content Articles Display Pipeline
**Decision:** `get_ai_content` results are streamed to the frontend as a dedicated `content_articles` WS message type; rendered as `ContentArticlesInline` collapsible cards with DOMPurify sanitization.
**Rationale:** Keeps LLM response text clean (agent outputs just the event identifier line) while frontend renders rich structured content. Same pattern as poll cards, event cards, and chart data — LLM produces minimal text, frontend does heavy lifting.
**Field mapping:** Backend returns `content`/`event_id`/`created_at`; frontend reads these exact keys (prior mismatch with `media_content`/`source_event_id`/`creation_timestamp` caused blank renders).

## 2026-03-13: query_ai_content Source Filter (AUTO% vs AUTOGEN_%)
**Decision:** Widened `video_library` source filter from `LIKE 'AUTOGEN_%'` to `LIKE 'AUTO%'` and removed `media_content IS NOT NULL AND LENGTH > 50` filter.
**Rationale:** `calendar.py`'s working reference implementation uses `AUTO%` with no content filter. The stricter filter was missing content and causing empty results. Also removed `client_id` from SELECT (leaked tenant ID to frontend).

## 2026-03-13: Content Agent Creation-First Pattern
**Decision:** Content agent must call `get_ai_content` FIRST for any content creation request — before `analyze_topic_performance`, `suggest_topics`, or any other tool.
**Rationale:** The analytics tools (`analyze_topic_performance`, `compare_event_performance`, etc.) query the local DataBot PostgreSQL DB via SQLAlchemy ORM, which depends on the ETL sync being run. If sync hasn't run, these tools return "no data" and the agent refuses to write. `get_ai_content` queries ON24 master DB directly — it always has data. Starting with source material is also better content strategy.

## 2026-03-14: Documentation Suite as HTML Docs
**Decision:** Create 5 HTML docs (test-plan, scalability, security-review, accessibility-vpat, api-vs-db-benchmark) in `frontend/public/docs/` with matching styling, CSS variable theming, and `?theme=dark|light` URL param support.
**Rationale:** Living documentation accessible from the app sidebar. Theme param ensures docs match app appearance. All docs use same hero/card/table styling pattern as MRD/PRD/tech-spec.

## 2026-03-14: Sidebar Documents Dropdown
**Decision:** Replaced individual sidebar doc links with a collapsible "Documents" dropdown containing 8 entries.
**Rationale:** 8+ links consumed too much sidebar space. Dropdown with outside-click close keeps sidebar clean. DOMPurify sanitizes recent-changes HTML (loaded via fetch).

## 2026-03-14: WCAG 2.1 AA Accessibility Fixes
**Decision:** Applied 15+ WCAG fixes: skip-to-content link, focus-visible outlines, aria-live regions, aria-expanded on collapsible sections, dark mode contrast (#94a0b8 for text-secondary), chat input labels, chart role="img", DOMPurify on calendar HTML.
**Rationale:** VPAT audit revealed multiple Partially Supports criteria. Fixes bring 9 criteria to full Supports status. 4 items remain open (calendar keyboard nav, chart axes contrast, calendar responsive 320px, chart data tables).

## 2026-03-15: SEC-01/02/03 Security Remediation
**Decision:** Implemented API key auth (HTTP middleware + WebSocket upgrade), per-IP rate limiting (slowapi + custom WS limiter), and tightened CORS (restricted methods/headers).
**Rationale:** All 3 HIGH findings from the security review. API_KEY env var — empty disables auth (dev mode). Rate limit: 20 WS msg/min, 100 REST/min per IP. CORS: only localhost:3000/3001 origins, explicit methods/headers.

## 2026-03-15: Content Sharing & Approval Workflow
**Decision:** Implemented a complete content review/approval system with HMAC-SHA256 signed links, 7-day expiry, per-recipient tokens, comment threads, 5-star ratings, and thumbs up/down approval. "Approved" badge when all recipients approve.
**Rationale:** Content agent generates blog posts, social media, emails — stakeholders need to review and approve before publishing. Link-based access means recipients don't need app accounts. Tokens are tied to specific email addresses (can't be shared). Server-side HTML sanitization via nh3.
**Tech:** 3 new DB tables (content_shares, share_recipients, share_comments), 4 API endpoints, standalone React review page (/share/:shareId), SendGrid/Gmail email delivery.

## 2026-03-15: nh3 for HTML Sanitization (replaces regex)
**Decision:** Replaced regex-based `_sanitize_html` with nh3 (Rust-based allowlist HTML sanitizer).
**Rationale:** Security audit found regex approach bypassable via nested tags, HTML entities, split tags. nh3 uses a proper HTML parser with an allowlist model — only explicitly permitted tags/attributes survive. Handles all edge cases that regex cannot.

## 2026-03-15: html-docs Skill — Standalone Documentation Generator
**Decision:** Created a reusable Claude Code skill (`html-docs`) that generates professional, responsive, themed HTML documentation with auto-discovery. Self-contained — no awareness of the parent application.
**Rationale:** Docs rot because updating them is manual. This skill auto-discovers project state (pytest results, security patterns, infrastructure config) and generates polished HTML docs. Supports document registration (external docs wired into nav), nav exclusion (docs excluded from dropdown), custom theming, dark mode, and scheduled regeneration via cron or shell script.
**Location:** `~/.claude/plugins/local/user-skills/skills/html-docs/SKILL.md`

## 2026-03-14: Permission-Based UI Filtering (Simulated Admin)
**Decision:** Admin permissions from `admin_property_info` (prop_code where value='Yes') stored in sessionStorage. UI elements filtered based on permission presence. No admin selected = show everything.
**Permission mapping:** view-webcasts→Elite, manage-engagement-hub→Hub, manage-target-experiences→Target, manage-virtual-events→GoLive, manage-brand-settings→Branding, manage-integrations→Connect, manage-users→Users, view-analytics→data agent tiles.

## 2026-03-14: Anthropic Prompt Caching
**Decision:** Added `cache_control: {"type": "ephemeral"}` to all 6 `messages.create` calls (system prompt parameter changed from string to list of content blocks).
**Rationale:** 90% input token discount on cached system prompts (5-min TTL). No behavioral change. Estimated $150K–$450K/yr savings at scale.

## 2026-03-14: Redis Response Cache
**Decision:** Added Redis 7 container + `response_cache.py`. SHA256(prompt.lower()) + client_id as cache key. 2-minute TTL. Only caches data_agent and concierge responses (not admin/content). Graceful degradation if Redis unavailable.
**Rationale:** Eliminates redundant LLM calls for repeated questions within 2 minutes. Skip for confirmed actions and short messages (<6 chars).

## 2026-03-14: Gunicorn Multi-Worker Backend (5 workers × 3 DB conns)
**Decision:** Switched from single uvicorn to gunicorn with 5 UvicornWorker processes, each with a 3-connection asyncpg pool (15 total ON24 DB connections).
**Rationale:** Single worker supported ~5-10 concurrent users. 5 workers scales to ~25-50. WebSocket connections are inherently sticky to one worker (TCP), so in-memory conversation history works without shared state or Redis. DB pool reduced from 10 to 3 per worker to stay under connection limits (5×3=15 vs 1×10=10). UVICORN_WORKERS env var allows tuning without rebuilding.

## 2026-03-14: Lead Query Tools (dw_lead)
**Decision:** Added `query_leads` and `query_lead_stats` to on24_query_tools.py, registered as data agent tools `get_leads` and `get_lead_stats`.
**Rationale:** dw_lead (105M rows) has direct client_id — no event join needed. Enables lead analytics: contact search by company/job title, aggregate stats with monthly trends, top companies, acquisition sources.

## 2026-03-14: CLAUDE.md Compaction + .ai/architecture.md
**Decision:** Reduced CLAUDE.md from 198 to 47 lines. Extracted data access, agent system, tables, WS protocol to `.ai/architecture.md`. Removed project structure tree, detailed chart/calendar/MCP sections (derivable from code).
**Rationale:** CLAUDE.md was consuming excessive context window. Key conventions and safety rules stay; implementation details belong in code or .ai/ files.

## 2026-03-14: Content Agent Topic Suggestions Mode
**Decision:** Added "Topic Suggestions" section to content agent prompt. When user asks "what topic" or "what should I write about", agent proposes 3-5 creative numbered topics without showing raw data. Create Content chips simplified to "Help me write a [type]".
**Rationale:** Previous behavior dumped raw analytics tables before topic suggestions. Users want concise creative proposals informed by data, not data dumps.

## 2026-03-14: Orchestrator Routing Priority (Content Before Data)
**Decision:** Content agent routing (rule 4) now comes before data agent routing (rule 6) in orchestrator. Explicit triggers: "suggest topics", "what topic", "create a script".
**Rationale:** "Create a script" and "suggest topics" requests were being routed to data agent (which showed raw tables) instead of content agent (which provides creative recommendations). Fixed duplicate rule numbering.

## 2026-03-15: Data Prefetch on Startup
**Decision:** Warm Redis cache with commonly requested data (recent events, KPIs, AI content, trends) on app startup. Serve via /api/prefetch/* endpoints for instant chip responses.
**Rationale:** First-click latency was 8-30s because every query required orchestrator LLM routing + agent LLM + DB query. Prefetching eliminates the LLM roundtrip for the most common queries. 15-min TTL ensures freshness. All queries parallelized via asyncio.gather().
**Consequences:** 3s startup delay while cache warms. Redis required (graceful degradation if unavailable). Frontend can optionally use /api/prefetch/* for chip data instead of chat.

## 2026-03-15: Switch All Agents to Sonnet (Performance)
**Decision:** Switched all 4 agents (orchestrator, data, content, admin) from `claude-opus-4-6` to `claude-sonnet-4-6`.
**Rationale:** Opus was 2-3x slower than Sonnet for first-token latency. CLAUDE.md specifies Sonnet as the main model. Near-identical quality with 40-60% latency reduction. Response cache TTL also increased from 2 to 5 minutes.

## 2026-03-15: Brand Templates Per-Client Isolation
**Decision:** Store brand templates in per-client JSON files (`data/brand_templates_{client_id}.json`) rather than a single shared file or database table.
**Rationale:** Strict tenant isolation — each client's brand templates are completely independent with no risk of cross-client data leakage. File-based storage avoids a migration and keeps templates simple to inspect/debug. The `{client_id}` suffix ensures templates from one client can never be read or modified by another, even if a bug bypasses the API-level client scoping. Default template fallback is also per-client.
**Consequences:** Templates do not survive container rebuilds unless `data/` is mounted as a Docker volume (already the case). No cross-client template sharing or "global" templates — acceptable for current requirements.

## 2026-03-17: Design System Overhaul (UI/UX Pro Max Audit)
**Decision:** Adopted Data-Dense Dashboard design system. Changed primary from indigo #4f46e5 to blue #2563EB. Added Fira Sans (body) + Fira Code (mono) via Google Fonts. New CTA color #F97316 (orange). Slate-based dark mode palette. All emoji structural icons replaced with lucide-react SVG. All touch targets minimum 44px. Mobile responsive with collapsible sidebar.
**Rationale:** UI/UX Pro Max audit identified 77 issues. Recommended style: Data-Dense Dashboard (blue data + amber highlights). Blue primary provides better data visualization contrast. Fira Sans/Code are optimized for dashboard/analytics readability. lucide-react provides consistent, accessible SVG icons across platforms (emoji renders inconsistently). 44px touch targets meet WCAG AAA and Apple HIG guidelines.
**Consequences:** Google Fonts dependency (CDN). Visual appearance changed significantly — users will notice different colors and typography. All CSS variables centralized; no hardcoded hex remaining in components. Chart hex values updated to match (Nivo/SVG requires raw hex, not CSS vars).

## 2026-03-16: Content Calendar Pre-Cache Strategy
**Decision:** Lazy-load content calendar analytics data (attendance trends + top events) into Redis on first data agent interaction. propose_content_calendar checks cache before invoking data agent.
**Rationale:** Current two-step flow (orchestrator → data agent → content agent) requires 3 sequential Anthropic API calls. `httpx.ConnectTimeout` on any call kills the entire flow with a generic error. Pre-caching eliminates the data agent step for the content calendar, reducing the chain to 2 calls and halving timeout exposure. Same Redis + 15-min TTL pattern as existing prefetch service.
**Consequences:** Content calendar uses slightly stale data (up to 15 min) — acceptable for "best-performing events" analysis. Fallback to real-time if cache miss.

## 2026-03-13: Suggestion Chip Structure (2+2+1)
**Decision:** Every response generates exactly 5 chips: 2 LLM-generated context chips + 2 fixed agent-switch chips + 1 "Home" chip.
**Rationale:** Users need a clear path back to home and to switch agents without hunting through menus. Fixed slots ensure navigation is always predictable regardless of what the agent said.
**Agent-switch mapping:** concierge→[data, content]; data→[concierge, content]; content→[data, concierge]. "Home" calls `resetChat()`. "How do I...?" opens the sub-menu without sending a message.
