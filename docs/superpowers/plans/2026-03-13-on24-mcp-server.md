# ON24 MCP Server Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the ON24 REST API write operations in a FastMCP server deployed as a 4th Docker container, with `USE_MCP=Y/N` flag and `USE_MCP_BLOCKLIST` to gate adoption incrementally.

**Architecture:** FastMCP server in `on24-mcp/` exposes 4 tools (create_event, update_event, add_registrant, remove_registrant) via streamable-HTTP on port 8001. Backend admin_tools.py checks `USE_MCP` at call time — `Y` routes through the MCP server via the `mcp` Python SDK client, `N` calls `on24_client.py` directly (current behavior unchanged). Blocklist is enforced at two layers: MCP server never registers blocked tools; backend refuses to call them even if somehow requested.

**Tech Stack:** Python 3.12, `mcp>=1.9` (FastMCP + client), `httpx`, `pydantic-settings`, Docker Compose streamable-HTTP transport.

---

## Chunk 1: MCP Server + Docker

### Task 1: Scaffold on24-mcp package

**Files:**
- Create: `on24-mcp/pyproject.toml`
- Create: `on24-mcp/Dockerfile`
- Create: `on24-mcp/__init__.py` (empty)

- [ ] **Step 1: Create `on24-mcp/pyproject.toml`**

```toml
[project]
name = "on24-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp[cli]>=1.9.0",
    "httpx>=0.27.0",
    "pydantic-settings>=2.3.0",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"
```

- [ ] **Step 2: Create `on24-mcp/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY . .

EXPOSE 8001
CMD ["python", "server.py"]
```

- [ ] **Step 3: Create `on24-mcp/__init__.py`** (empty file)

- [ ] **Step 4: Verify directory structure**

```
on24-mcp/
  __init__.py
  pyproject.toml
  Dockerfile
```

---

### Task 2: Config and ON24 client for MCP server

**Files:**
- Create: `on24-mcp/config.py`
- Create: `on24-mcp/on24_client.py`

- [ ] **Step 1: Create `on24-mcp/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    on24_base_url: str = "https://apiqa.on24.com"
    on24_client_id: str = ""
    on24_access_token_key: str = ""
    on24_access_token_secret: str = ""
    # Comma-separated tool names to never expose, e.g. "create_event,remove_registrant"
    use_mcp_blocklist: str = ""

    @property
    def blocklist(self) -> set[str]:
        return {t.strip() for t in self.use_mcp_blocklist.split(",") if t.strip()}

    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
```

- [ ] **Step 2: Create `on24-mcp/on24_client.py`**

Self-contained copy of the ON24 client — no `app.*` imports:

```python
import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class ON24APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"ON24 API error {status_code}: {message}")


class ON24Client:
    def __init__(self, client_id: str, token_key: str, token_secret: str, base_url: str):
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "accessTokenKey": token_key,
            "accessTokenSecret": token_secret,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _path(self, endpoint: str) -> str:
        return f"/v2/client/{self.client_id}/{endpoint.lstrip('/')}"

    async def _request(self, method: str, endpoint: str, json_body: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30.0) as client:
            resp = await client.request(method, self._path(endpoint), json=json_body)
        if resp.status_code == 401:
            raise ON24APIError(401, "Invalid credentials")
        if resp.status_code == 403:
            raise ON24APIError(403, "Permission denied")
        if resp.status_code == 404:
            raise ON24APIError(404, f"Not found: {endpoint}")
        if resp.status_code >= 400:
            raise ON24APIError(resp.status_code, resp.text)
        return resp.json()

    async def create_event(self, title: str, event_type: str, start_time: str, end_time: str, description: str | None = None) -> dict:
        body: dict = {"eventType": event_type, "title": title, "startTime": start_time, "endTime": end_time}
        if description:
            body["description"] = description
        return await self._request("POST", "event", body)

    async def update_event(self, event_id: int, title: str | None = None, description: str | None = None, start_time: str | None = None, end_time: str | None = None) -> dict:
        body = {k: v for k, v in {"title": title, "description": description, "startTime": start_time, "endTime": end_time}.items() if v is not None}
        return await self._request("PATCH", f"event/{event_id}", body)

    async def register_attendee(self, event_id: int, email: str, first_name: str, last_name: str, company: str | None = None, job_title: str | None = None) -> dict:
        body: dict = {"email": email, "firstName": first_name, "lastName": last_name}
        if company:
            body["company"] = company
        if job_title:
            body["jobTitle"] = job_title
        return await self._request("POST", f"event/{event_id}/registrant", body)

    async def remove_registration(self, event_id: int, email: str) -> dict:
        return await self._request("DELETE", f"event/{event_id}/registrant/{email}")
```

- [ ] **Step 3: Commit scaffold**

```bash
git add on24-mcp/
git commit -m "feat(mcp): scaffold on24-mcp package with config and ON24 client"
```

---

### Task 3: FastMCP server with blocklist

**Files:**
- Create: `on24-mcp/server.py`

- [ ] **Step 1: Create `on24-mcp/server.py`**

```python
"""ON24 MCP Server — exposes ON24 REST API write operations as MCP tools."""
import logging
from mcp.server.fastmcp import FastMCP
from config import settings
from on24_client import ON24Client, ON24APIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("on24-api", stateless_http=True)

BLOCKLIST = settings.blocklist


def _client() -> ON24Client:
    return ON24Client(
        client_id=settings.on24_client_id,
        token_key=settings.on24_access_token_key,
        token_secret=settings.on24_access_token_secret,
        base_url=settings.on24_base_url,
    )


if "create_event" not in BLOCKLIST:
    @mcp.tool()
    async def create_event(title: str, event_type: str, start_time: str, end_time: str, description: str = "") -> dict:
        """Create a new ON24 event. start_time/end_time in ISO 8601."""
        try:
            resp = await _client().create_event(title, event_type, start_time, end_time, description or None)
            eid = resp.get("eventId") or resp.get("id")
            return {"success": True, "on24_event_id": eid, "message": f"Event '{title}' created."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "update_event" not in BLOCKLIST:
    @mcp.tool()
    async def update_event(on24_event_id: int, title: str = "", description: str = "", start_time: str = "", end_time: str = "") -> dict:
        """Update fields on an existing ON24 event. Pass only fields to change."""
        try:
            await _client().update_event(
                on24_event_id,
                title=title or None,
                description=description or None,
                start_time=start_time or None,
                end_time=end_time or None,
            )
            return {"success": True, "on24_event_id": on24_event_id, "message": f"Event {on24_event_id} updated."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "add_registrant" not in BLOCKLIST:
    @mcp.tool()
    async def add_registrant(on24_event_id: int, email: str, first_name: str, last_name: str, company: str = "", job_title: str = "") -> dict:
        """Register a person for an ON24 event."""
        try:
            await _client().register_attendee(on24_event_id, email, first_name, last_name, company or None, job_title or None)
            return {"success": True, "message": f"{first_name} {last_name} ({email}) registered for event {on24_event_id}."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if "remove_registrant" not in BLOCKLIST:
    @mcp.tool()
    async def remove_registrant(on24_event_id: int, email: str) -> dict:
        """Remove a registrant from an ON24 event by email."""
        try:
            await _client().remove_registration(on24_event_id, email)
            return {"success": True, "message": f"Registration for {email} removed from event {on24_event_id}."}
        except ON24APIError as e:
            return {"success": False, "error": e.message}


if __name__ == "__main__":
    logger.info(f"Starting ON24 MCP server. Blocklist: {BLOCKLIST or 'none'}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001, path="/mcp")
```

- [ ] **Step 2: Verify blocklist works locally**

```bash
cd on24-mcp
USE_MCP_BLOCKLIST=create_event python -c "from config import settings; assert 'create_event' in settings.blocklist"
echo "Blocklist OK"
```

Expected: `Blocklist OK`

- [ ] **Step 3: Commit server**

```bash
git add on24-mcp/server.py
git commit -m "feat(mcp): FastMCP server with 4 ON24 write tools and blocklist enforcement"
```

---

### Task 4: Add on24-mcp to Docker Compose

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add on24-mcp service to `docker-compose.yml`**

Add after the `backend` service block, before `frontend`:

```yaml
  on24-mcp:
    build: ./on24-mcp
    platform: linux/amd64
    env_file:
      - .env.local
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/mcp')\" 2>/dev/null || exit 0"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

Update `backend` service to declare optional dependency:

```yaml
  backend:
    ...
    depends_on:
      postgres:
        condition: service_healthy
```

(No hard dependency on on24-mcp — backend works without it when USE_MCP=N.)

- [ ] **Step 2: Build and verify MCP container starts**

```bash
docker compose build on24-mcp
docker compose up -d on24-mcp
docker compose logs on24-mcp
```

Expected log: `Starting ON24 MCP server. Blocklist: none`

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(mcp): add on24-mcp as 4th Docker Compose service on port 8001"
```

---

## Chunk 2: Backend Integration

### Task 5: Backend config — USE_MCP flag

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add MCP settings to `backend/app/config.py`**

```python
    # MCP server integration
    use_mcp: str = "N"          # "Y" to route admin ops through MCP server
    use_mcp_blocklist: str = ""  # comma-separated tool names to block even if USE_MCP=Y
    mcp_server_url: str = "http://on24-mcp:8001"  # Docker service name

    @property
    def mcp_enabled(self) -> bool:
        return self.use_mcp.upper() == "Y"

    @property
    def mcp_blocklist(self) -> set[str]:
        return {t.strip() for t in self.use_mcp_blocklist.split(",") if t.strip()}
```

- [ ] **Step 2: Add `mcp>=1.9.0` to `backend/pyproject.toml`**

Find the `dependencies` list and add:
```toml
"mcp>=1.9.0",
```

- [ ] **Step 3: Write test for config flag**

In `backend/tests/test_mcp_config.py`:

```python
import os
import importlib


def test_mcp_disabled_by_default(monkeypatch):
    monkeypatch.delenv("USE_MCP", raising=False)
    from app.config import Settings
    s = Settings()
    assert s.mcp_enabled is False


def test_mcp_enabled_when_y(monkeypatch):
    monkeypatch.setenv("USE_MCP", "Y")
    from app.config import Settings
    s = Settings()
    assert s.mcp_enabled is True


def test_mcp_blocklist_parsed(monkeypatch):
    monkeypatch.setenv("USE_MCP_BLOCKLIST", "create_event, remove_registrant")
    from app.config import Settings
    s = Settings()
    assert s.mcp_blocklist == {"create_event", "remove_registrant"}
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_mcp_config.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/pyproject.toml backend/tests/test_mcp_config.py
git commit -m "feat(mcp): add USE_MCP/USE_MCP_BLOCKLIST/MCP_SERVER_URL settings to backend config"
```

---

### Task 6: MCP client helper in backend

**Files:**
- Create: `backend/app/services/mcp_client.py`

- [ ] **Step 1: Create `backend/app/services/mcp_client.py`**

```python
"""Thin async helper for calling the ON24 MCP server from the backend."""
import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a tool on the ON24 MCP server.

    Returns the tool result dict, or raises RuntimeError on failure.
    Checks USE_MCP and blocklist before making the call.
    """
    if not settings.mcp_enabled:
        raise RuntimeError("MCP is disabled (USE_MCP != Y)")
    if tool_name in settings.mcp_blocklist:
        raise RuntimeError(f"Tool '{tool_name}' is in USE_MCP_BLOCKLIST")

    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    url = f"{settings.mcp_server_url.rstrip('/')}/mcp"
    logger.info(f"Calling MCP tool '{tool_name}' at {url}")

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)

        # FastMCP returns result.content as a list of TextContent
        if result.content:
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"success": True, "message": text}
        return {"success": True}

    except Exception as e:
        logger.error(f"MCP tool call failed: {tool_name} → {e}")
        raise
```

- [ ] **Step 2: Write test for MCP client helper**

In `backend/tests/test_mcp_client.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_call_mcp_tool_disabled(monkeypatch):
    monkeypatch.setenv("USE_MCP", "N")
    from app.config import Settings
    settings_mock = Settings()
    with patch("app.services.mcp_client.settings", settings_mock):
        from app.services.mcp_client import call_mcp_tool
        with pytest.raises(RuntimeError, match="disabled"):
            await call_mcp_tool("create_event", {})


@pytest.mark.asyncio
async def test_call_mcp_tool_blocklisted(monkeypatch):
    monkeypatch.setenv("USE_MCP", "Y")
    monkeypatch.setenv("USE_MCP_BLOCKLIST", "create_event")
    from app.config import Settings
    settings_mock = Settings()
    with patch("app.services.mcp_client.settings", settings_mock):
        from app.services.mcp_client import call_mcp_tool
        with pytest.raises(RuntimeError, match="blocklist"):
            await call_mcp_tool("create_event", {})
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_mcp_client.py -v
```

Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/mcp_client.py backend/tests/test_mcp_client.py
git commit -m "feat(mcp): add MCP client helper with USE_MCP and blocklist guard"
```

---

### Task 7: Wire admin_tools.py to use MCP when enabled

**Files:**
- Modify: `backend/app/agents/tools/admin_tools.py`

Replace the direct `ON24Client` calls in the four write functions with a branch: if `settings.mcp_enabled` and tool not in blocklist → call MCP; else → existing path.

- [ ] **Step 1: Update `create_event` in `admin_tools.py`**

```python
async def create_event(title, event_type, start_time, end_time, description=None):
    from app.config import settings
    if settings.mcp_enabled and "create_event" not in settings.mcp_blocklist:
        from app.services.mcp_client import call_mcp_tool
        return await call_mcp_tool("create_event", {
            "title": title, "event_type": event_type,
            "start_time": start_time, "end_time": end_time,
            "description": description or "",
        })
    # Existing direct path
    client = _get_on24_client()
    try:
        response = await client.create_event(title=title, event_type=event_type,
            start_time=start_time, end_time=end_time, description=description)
        on24_event_id = response.get("eventId") or response.get("id")
        return {"success": True, "on24_event_id": on24_event_id,
                "message": f"Event '{title}' created successfully.", "raw_response": response}
    except Exception as e:
        logger.error(f"create_event failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        await client.close()
```

- [ ] **Step 2: Apply same pattern to `update_event`, `add_registrant`, `remove_registrant`**

`update_event`:
```python
    if settings.mcp_enabled and "update_event" not in settings.mcp_blocklist:
        return await call_mcp_tool("update_event", {
            "on24_event_id": on24_event_id,
            "title": title or "", "description": description or "",
            "start_time": start_time or "", "end_time": end_time or "",
        })
```

`add_registrant`:
```python
    if settings.mcp_enabled and "add_registrant" not in settings.mcp_blocklist:
        return await call_mcp_tool("add_registrant", {
            "on24_event_id": on24_event_id, "email": email,
            "first_name": first_name, "last_name": last_name,
            "company": company or "", "job_title": job_title or "",
        })
```

`remove_registrant`:
```python
    if settings.mcp_enabled and "remove_registrant" not in settings.mcp_blocklist:
        return await call_mcp_tool("remove_registrant", {
            "on24_event_id": on24_event_id, "email": email,
        })
```

- [ ] **Step 3: Run existing admin tool tests to confirm direct path unchanged**

```bash
cd backend && python -m pytest tests/ -k "admin" -v
```

Expected: existing tests pass (USE_MCP defaults to N)

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/tools/admin_tools.py
git commit -m "feat(mcp): admin_tools routes through MCP server when USE_MCP=Y"
```

---

### Task 8: Document .env.local additions + rebuild

**Files:**
- Modify: `CLAUDE.md` (env vars section)
- Modify: `.ai/decisions.md`

- [ ] **Step 1: Add MCP env vars to CLAUDE.md env vars table**

```
USE_MCP=N                          # Y to route admin writes through MCP server
USE_MCP_BLOCKLIST=                 # comma-separated tool names to block even if USE_MCP=Y
MCP_SERVER_URL=http://on24-mcp:8001  # override MCP server address (default works in Docker)
```

- [ ] **Step 2: Full rebuild and smoke test**

```bash
docker compose up --build -d
docker compose logs on24-mcp  # should show "Starting ON24 MCP server"
curl http://localhost:8001/mcp  # should return MCP endpoint response (405 or JSON)
docker compose logs backend   # should show no errors
```

- [ ] **Step 3: Final commit and push**

```bash
git add CLAUDE.md .ai/decisions.md
git commit -m "docs: document USE_MCP env vars; MCP server operational"
git push origin main
```
