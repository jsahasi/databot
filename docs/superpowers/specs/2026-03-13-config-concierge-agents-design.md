# Design: Config Agent + Concierge Agent

**Date:** 2026-03-13
**Status:** Approved
**Scope:** Add two new agents to the DataBot 4-agent architecture

---

## 1. Overview

Expand the existing Orchestrator → {Data, Content, Admin} system to a 6-agent architecture:

| Agent | Purpose | DB Access | Max Rounds |
|-------|---------|-----------|-----------|
| Orchestrator | Intent classification + routing | — | 1 |
| Data | Analytics queries + charts | ON24 master (read-only) | 10 |
| Content | Content strategy + insights | ON24 master (read-only) | 5 |
| Admin | ON24 write operations | ON24 REST API | 5 |
| **Config** *(new)* | Deep-link launcher for ON24 products; future Oracle write ops | Oracle (stub) | 3 |
| **Concierge** *(new)* | Platform how-to knowledge — Zendesk KB + ON24 product grounding | None | 5 |

---

## 2. Config Agent

### Purpose
Surfaces deep links to ON24 product creation and configuration UIs. Stubbed now; will gain Oracle DB write access when credentials are available.

### Backend: `backend/app/agents/config_agent.py`
- Follows identical multi-round tool-use pattern as existing agents
- Accepts optional `conversation_history` parameter (unused today; required for Oracle write phase)
- **Tools** (defined in `backend/app/agents/tools/config_tools.py`, registered in `tools/__init__.py` as `CONFIG_AGENT_TOOLS`):
  - `get_experience_links` — returns `[{name, description, url}]` for the 4 ON24 experience products (hardcoded)
  - `get_config_links` — returns `[{name, description, url}]` for platform configuration surfaces (hardcoded)
- No DB calls in this iteration
- Oracle stub: `backend/app/db/oracle_stub.py` — `get_pool()` raises `NotImplementedError("Oracle credentials not yet configured")`. Must be a **deferred import** inside config agent (never imported at module top-level); guard with `if settings.oracle_db_url:` to avoid startup errors when driver not installed.
- System prompt: `backend/app/agents/prompts/config_agent.md`

### Experience links (`get_experience_links`)
| Label | URL |
|-------|-----|
| Elite — Webinars | https://wcc.on24.com/webcast/webcasts |
| Engagement Hub | https://wccv.on24.com/webcast/managemychannel |
| Target — Landing Pages | https://wccv.on24.com/webcast/gatewayexperience |
| GoLive — Virtual Events | https://wccgl.on24.com/webcast/events |

### Config links (`get_config_links`)
| Label | URL |
|-------|-----|
| Media Manager | https://wccv.on24.com/webcast/mediamanager |
| Segment Builder | https://segment.on24.com/segments/segments |
| Connect / Integrations | https://wcc.on24.com/webcast/integrations |
| Branding | https://wcc.on24.com/webcast/accountdashboard?tab=branding&clientId=10710 |
| Manage Users | https://wcc.on24.com/webcast/manageusers |

### Frontend: `frontend/src/components/chat/ChatPanel.tsx`
Two new tiles added to `SUGGESTIONS`: `"Experiences"` and `"Configure environment"`.

These tiles **bypass the chat/agent pipeline** — same pattern as the existing "How do I...?" sub-menu:
- Clicking "Experiences" → sets `showExperiences(true)`, renders inline chip sub-menu (replaces tile grid, has Back button). Each chip is a direct deep link (`<a target="_blank">`) to the respective ON24 experience.
- Clicking "Configure environment" → sets `showConfigureEnv(true)`, renders inline chip sub-menu (replaces tile grid, has Back button). Each chip is a direct deep link to the respective ON24 configuration surface.
- Each sub-menu uses the same chip button styles as the "How do I...?" sub-menu

**Experiences chips** (from ON24_Grounding.docx):
| Label | URL |
|-------|-----|
| Elite — Webinars | https://wcc.on24.com/webcast/webcasts |
| Engagement Hub | https://wccv.on24.com/webcast/managemychannel |
| Target — Landing Pages | https://wccv.on24.com/webcast/gatewayexperience |
| GoLive — Virtual Events | https://wccgl.on24.com/webcast/events |

**Configure environment chips**:
| Label | URL |
|-------|-----|
| Media Manager | https://wccv.on24.com/webcast/mediamanager |
| Segment Builder | https://segment.on24.com/segments/segments |
| Connect / Integrations | https://wcc.on24.com/webcast/integrations |
| Branding | https://wcc.on24.com/webcast/accountdashboard?tab=branding&clientId=10710 |
| Manage Users | https://wcc.on24.com/webcast/manageusers |

Note: `clientId=10710` is the root client ID, hardcoded from `settings.on24_client_id`. The frontend uses this constant directly — no API call needed.

### Orchestrator changes
- New `route_to_config` tool added to `ROUTING_TOOLS`
- Routing prompt updated: config-related intent ("I want to create a webinar", "where do I set up an integration?") → config agent. Rule: if user wants to **navigate to or open** an ON24 UI, route to config; if user wants to **understand how** a feature works, route to concierge.
- Exception rollback in `route_to_config` dispatch: **2-pop** (assistant tool_use + user message), matching `route_to_data_agent`. Do NOT copy the 3-pop pattern from the `search_knowledge_base` block.

### Config agent `agent_used` + suggestions
- Config agent returns `agent_used = "config"`
- `generate_suggestions` in `chat.py` gets a new `elif agent_used == "config":` branch that returns a fixed minimal set: `["Create experiences", "Configure environment"]`
- Config tiles that bypass chat never produce a chat response, so this branch only fires when a user types a config intent directly into the chat input

---

## 3. Concierge Agent

### Purpose
Single authoritative agent for all "how do I use ON24?" queries. Consolidates the existing `search_knowledge_base` flow out of the orchestrator plus ON24 product grounding from ON24_Grounding.docx.

### Backend: `backend/app/agents/concierge_agent.py`
- Multi-round tool-use loop, max 5 rounds
- **Tools** (defined in `backend/app/agents/tools/concierge_tools.py`, registered in `tools/__init__.py` as `CONCIERGE_AGENT_TOOLS`):
  - `search_knowledge_base` — moved from orchestrator to `concierge_tools.py`; searches ChromaDB Zendesk articles (logic extracted verbatim)
- Product knowledge (Elite, Engagement Hub, Target, GoLive, Segment Builder, AI Propel+, etc.) and all deep links from ON24_Grounding.docx are **baked into the system prompt** — no `get_product_overview` tool needed (static data belongs in the prompt, not a tool)
- System prompt: `backend/app/agents/prompts/concierge_agent.md`
  - Contains full product reference table from ON24_Grounding.docx
  - Strict no-hallucination rule: only cite what's in KB articles or the grounding reference table
  - Always include deep links when referencing a product
  - After answering, suggest related how-to topics; last chip always "Explore my event data"
- `agent_used` = `"concierge"` (replaces old `"knowledge_base"` label)

### Migration: `search_knowledge_base` out of orchestrator
Three explicit steps required:
1. **Extract**: Move handler logic from the inline `if tool_name == "search_knowledge_base":` dispatch block in `orchestrator.py` into `concierge_tools.py` as a standalone async function
2. **Gut**: Remove the `if tool_name == "search_knowledge_base":` dispatch branch from `orchestrator.py` entirely (not just the schema — the full dispatch block including the two-round follow-up call)
3. **Replace**: Add `route_to_concierge` dispatch branch in `orchestrator.py` that calls `ConciergeAgent.run()`

### Orchestrator changes
- `search_knowledge_base` removed from `ROUTING_TOOLS` schema list
- `search_knowledge_base` dispatch block removed from `process_message` loop entirely (including the two-round follow-up call)
- `route_to_concierge` tool added to `ROUTING_TOOLS`
- Routing prompt updated: "How do I...?", "what is X?", "how does X work?", "explain X" → concierge. Rule: if user wants to **understand how** a feature works, route to concierge; if user wants to **navigate to or open** an ON24 UI, route to config.
- Exception rollback in `route_to_concierge` dispatch: **2-pop** (assistant tool_use + user message), matching `route_to_data_agent`. Do NOT copy the 3-pop pattern from the `search_knowledge_base` block being removed.

### Frontend
- No UI changes needed — "How do I...?" tile and sub-menu already send chat messages; orchestrator routes transparently
- `agent_used = "concierge"` → update `generate_suggestions` in `chat.py`:
  - Replace `if agent_used == "knowledge_base":` branch with `if agent_used == "concierge":` (same help-mode chip behavior)
  - Update capability list in `generate_suggestions` to include: "Navigate to ON24 product creation UIs" and "Platform how-to questions (Zendesk KB + product grounding)"
- Frontend badge: displays "Concierge" (via existing `agentUsed` label rendering)

---

## 4. Files Changed / Created

### New files
```
backend/app/agents/config_agent.py
backend/app/agents/concierge_agent.py
backend/app/agents/prompts/config_agent.md
backend/app/agents/prompts/concierge_agent.md
backend/app/agents/tools/config_tools.py
backend/app/agents/tools/concierge_tools.py
backend/app/db/oracle_stub.py                ← Oracle placeholder (deferred import only)
```

### Modified files
```
backend/app/agents/orchestrator.py           ← add route_to_config, route_to_concierge; remove search_knowledge_base tool + dispatch block
backend/app/agents/tools/__init__.py         ← register CONFIG_AGENT_TOOLS, CONCIERGE_AGENT_TOOLS
backend/app/api/chat.py                      ← wire config/concierge into routing; update generate_suggestions (agent_used branch + capability list)
frontend/src/components/chat/ChatPanel.tsx   ← add 2 tiles + inline card panels (Create experiences, Configure environment)
```

---

## 5. Out of Scope (this iteration)

- Oracle DB driver installation or live connection
- Config agent writing to ON24 (admin agent handles event creation today)
- Concierge agent ingesting new KB sources beyond existing ChromaDB
- Any new API endpoints (all routed through existing `/api/chat` + `/ws/chat`)
