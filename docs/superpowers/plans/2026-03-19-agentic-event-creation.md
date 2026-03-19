# Agentic Event Creation — Full Decision Tree Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mirror ON24 Elite's agentic event creation decision tree in Nexus chat — conversational wizard with chips that narrows to a template, selects a theme, and creates the event via the ON24 API.

**Architecture:** The admin agent prompt is updated with the full decision tree (Use Case → Event Type → Slides/Screenshare → Nav Layout → Lock/Editable). A new `create_event_from_template` tool calls the Elite API endpoint `POST /webcast/webapi/eventCreate/eventFromTemplate`. The frontend renders the agent's chip options as clickable suggestion buttons, and shows a template preview card with the result.

**Tech Stack:** Python/FastAPI backend, Anthropic Claude Sonnet 4.6, ON24 Elite REST API, React/TypeScript frontend

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/agents/prompts/admin_agent.md` | Modify | Decision tree questions, chip format, template flow instructions |
| `backend/app/agents/tools/admin_tools.py` | Modify | Add `create_event_from_template()` and `get_agentic_templates()` |
| `backend/app/agents/tools/__init__.py` | Modify | Add tool schemas for new tools |
| `backend/app/services/on24_client.py` | Modify | Add `get_agentic_questions()`, `get_agentic_result()`, `create_from_template()` |
| `backend/app/agents/admin_agent.py` | Modify | Handle multi-turn decision tree state |
| `backend/app/api/chat.py` | Modify | Pass agentic suggestions as chips |

---

### Task 1: Add Elite Agentic API Methods to ON24Client

**Files:**
- Modify: `backend/app/services/on24_client.py`

- [ ] **Step 1: Add `get_agentic_questions()` method**

Fetches the decision tree from Elite. This is optional — we can hardcode the tree if the API requires Elite auth we don't have. For now, hardcode the tree since we already know it from the research.

```python
# Not calling Elite API — decision tree is deterministic and known.
# Hardcoded in admin_agent.md prompt instead.
```

Skip this — the decision tree will live in the admin agent prompt.

- [ ] **Step 2: Add `create_from_template()` method to ON24Client**

```python
async def create_from_template(
    self,
    template_id: int,
    event_type: str,
    theme_type: str = "on24-matcha",
    title: str | None = None,
    live_start: str | None = None,
    time_zone: str = "America/New_York",
) -> dict[str, Any]:
    """Create event from an agentic template via Elite's eventFromTemplate endpoint."""
    params = {
        "clientId": self.client_id,
        "templateId": template_id,
        "eventType": event_type,
        "themeType": theme_type,
        "isAgenticTemplate": "true",
    }
    form: dict[str, Any] = {}
    if title:
        form["title"] = title
    if live_start:
        form["liveStart"] = live_start
    if time_zone:
        form["timeZone"] = time_zone
    # This uses the WCC endpoint, not REST v2
    url = f"{self.wcc_base_url}/webcast/webapi/eventCreate/eventFromTemplate"
    async with self._session.post(url, params=params, data=form) as resp:
        return await resp.json()
```

Note: This requires WCC session auth, not REST API token. If WCC auth isn't available, fall back to `create_webinar()` with the event_type derived from the decision tree.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/on24_client.py
git commit -m "feat: add create_from_template method to ON24Client"
```

---

### Task 2: Update Admin Agent Prompt with Decision Tree

**Files:**
- Modify: `backend/app/agents/prompts/admin_agent.md`

- [ ] **Step 1: Add the full decision tree to the prompt**

Add after the "Default Values" section:

```markdown
## Agentic Event Creation — Decision Tree (MANDATORY for "create event")

When the user wants to create a new event, guide them through this decision tree ONE QUESTION AT A TIME. Present each question with numbered options. The user selects by number or name.

### Question 1: Use Case
"What is the use case for your event?"

Options:
1. Demand Generation
2. Partner Enablement
3. Member Enrollment
4. Product Feedback
5. Health Care Provider Engagement
6. Key Opinion Leader Engagement
7. Certification / Training
8. Asset Management / Financial Services
9. Insurance

### Question 2: Event Type
"What type of event are you creating?"

Options:
1. Live Video
2. Simulive
3. On Demand
4. Broadcast
5. Sim-2-Live
6. Forums

Map to API eventType: Live Video→fav, Simulive→simulive, On Demand→ondemand, Broadcast→encodeonsite, Sim-2-Live→sim2live, Forums→meetups

### Question 3: Presentation Mode (ONLY if Live Video selected)
"How will you present your slides?"

Options:
1. Slides
2. Screen Share (recommended)

If NOT Live Video → skip to collecting event details.

### Question 4: Navigation Layout (ONLY if Slides selected in Q3)
"Do you prefer top navigation or bottom tool dock?"

Options:
1. Top Navigation (recommended)
2. Bottom Tools Dock

If Screen Share was selected in Q3 → skip to Question 5.

### Question 5: Layout Lock (ONLY if Live Video AND (Screen Share OR Top Navigation))
"Do you prefer automated or manually editable layout?"

Options:
1. Intelligent Layout (recommended) — automated, locked
2. Manually Editable Layout

### After Decision Tree Complete

Summarize the selections, then ask for event details:
- Event title (required)
- Start date and time (required, default to next business day 9:00 AM ET)
- Duration (optional, default 60 min)

Then create the event using `create_event` with the derived event_type.

### Event Type Mapping from Decision Tree

| Q2 Answer | eventType |
|-----------|-----------|
| Live Video | fav |
| Simulive | simulive |
| On Demand | ondemand |
| Broadcast | encodeonsite |
| Sim-2-Live | sim2live |
| Forums | meetups |

### IMPORTANT
- Ask ONE question at a time
- Number the options clearly
- State "(recommended)" next to the recommended option
- If user says "just create a quick webinar" or similar, skip the tree — use defaults: Demand Gen, Live Video, Screen Share, Intelligent Layout
- After the tree, collect title + date/time, then proceed to confirmation
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agents/prompts/admin_agent.md
git commit -m "feat: add full decision tree to admin agent prompt"
```

---

### Task 3: Update Suggestion Chip Generation for Decision Tree

**Files:**
- Modify: `backend/app/api/chat.py`

The decision tree options need to render as clickable chips in the frontend. Currently the suggestion generator uses Haiku to create follow-up chips. For the admin agent's decision tree questions, the numbered options should become the chips directly.

- [ ] **Step 1: Add admin agent chip detection in suggestion generation**

In `chat.py`, after getting the admin agent response, check if the text contains numbered options (the decision tree pattern). If so, extract them as chips instead of calling Haiku.

```python
# In the suggestion generation section, add for admin_agent:
if agent == "admin_agent":
    # Extract numbered options from decision tree responses
    import re
    options = re.findall(r'^\d+\.\s+(.+?)(?:\s+\(recommended\))?$', text, re.MULTILINE)
    if options:
        # Use extracted options as chips directly (no Haiku call)
        suggestions = options[:6] + ["Home"]
        await ws.send_json({"type": "suggestions", "suggestions": suggestions})
        return
```

- [ ] **Step 2: Run test to verify extraction**

Test with sample text: `"1. Demand Generation\n2. Partner Enablement\n3. Member Enrollment"`
Expected: chips = `["Demand Generation", "Partner Enablement", "Member Enrollment", "Home"]`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: extract decision tree options as chips for admin agent"
```

---

### Task 4: Test End-to-End Flow

- [ ] **Step 1: Rebuild backend**

```bash
docker compose up -d --build backend
```

- [ ] **Step 2: Test the flow**

In chat, click "Create Event" from Experiences menu. Verify:
1. Agent asks "What is the use case for your event?" with 9 chip options
2. Select "Demand Generation" → asks "What type of event?" with 6 options
3. Select "Live Video" → asks "How will you present slides?" with 2 options
4. Select "Screen Share" → asks "Layout preference?" with 2 options
5. Select "Intelligent Layout" → asks for title + date/time
6. Provide title + date → confirmation dialog
7. Confirm → event created

- [ ] **Step 3: Test shortcut**

Send "create a quick webinar" → should skip tree, use defaults, go straight to title + date.

- [ ] **Step 4: Commit all working changes**

```bash
git add -A
git commit -m "feat: agentic event creation with full decision tree"
```

---

### Task 5: Push and Deploy

- [ ] **Step 1: Push to both remotes**

```bash
git push origin main
git push gitlab main:dev
```

- [ ] **Step 2: Rebuild containers**

```bash
docker compose up -d --build backend frontend
```

- [ ] **Step 3: Update docs**

Update `.ai/tasks.md`, `.ai/decisions.md`, and `frontend/public/docs/recent-changes.html`.
