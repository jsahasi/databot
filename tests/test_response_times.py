"""test_response_times.py — Response time profiling for all chat agents.

Connects to the running backend via WebSocket, sends representative prompts
covering every agent, measures wall-clock response time, and saves results
to tests/results/response_time_results.json.

Severity thresholds:
    ok       — < 5 s
    medium   — 5–10 s
    high     — 10–20 s
    critical — > 20 s

Hard fail: any prompt exceeding 30 s (timeout) or any CRITICAL response.

Usage:
    pytest tests/test_response_times.py -v --tb=short
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import websockets

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WS_URI = "ws://localhost:8000/ws/chat"
RECV_TIMEOUT = 30  # seconds — hard ceiling per prompt
INTER_PROMPT_DELAY = 2  # seconds between prompts to avoid rate limiting

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_FILE = RESULTS_DIR / "response_time_results.json"

# ---------------------------------------------------------------------------
# Profiling prompts (cover all agents)
# ---------------------------------------------------------------------------

PROFILING_PROMPTS: list[dict[str, str]] = [
    # Data Agent — event queries
    {"id": "data_simple", "prompt": "How many events did we have last month?", "agent": "data"},
    {"id": "data_chart", "prompt": "Show attendance trends as a line chart", "agent": "data"},
    {"id": "data_top_events", "prompt": "Show me top 5 events by attendance", "agent": "data"},
    {"id": "data_last_event", "prompt": "What was my last event?", "agent": "data"},
    {"id": "data_companies", "prompt": "Which companies attended the most?", "agent": "data"},
    # Data Agent — AI content
    {"id": "ai_content_blog", "prompt": "Show me the most recent AI-generated blog posts", "agent": "data"},
    {"id": "ai_content_kt", "prompt": "Show me the most recent AI-generated Key Takeaways", "agent": "data"},
    {"id": "ai_content_email", "prompt": "Show me the most recent AI-generated follow-up emails", "agent": "data"},
    {"id": "ai_content_social", "prompt": "Show me the most recent AI-generated social media posts", "agent": "data"},
    {"id": "ai_content_faq", "prompt": "Show me the most recent AI-generated FAQ articles", "agent": "data"},
    {"id": "ai_content_ebook", "prompt": "Show me the most recent AI-generated eBooks", "agent": "data"},
    # Concierge Agent
    {"id": "concierge_howto", "prompt": "How do I set up a webinar?", "agent": "concierge"},
    {"id": "concierge_api", "prompt": "What REST API endpoints are available?", "agent": "concierge"},
    {"id": "concierge_polls", "prompt": "How do I add polls to my webinar?", "agent": "concierge"},
    # Content Agent
    {"id": "content_suggest", "prompt": "Suggest content topics based on my best-performing events", "agent": "content"},
    {"id": "content_create", "prompt": "Help me write a blog post about our most recent webinar", "agent": "content"},
    {"id": "content_social", "prompt": "Help me create social media posts for my last event", "agent": "content"},
]


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

def _classify_severity(elapsed: float) -> str:
    """Return severity label based on elapsed seconds."""
    if elapsed < 5:
        return "ok"
    if elapsed < 10:
        return "medium"
    if elapsed < 20:
        return "high"
    return "critical"


# ---------------------------------------------------------------------------
# WebSocket send-and-measure helper
# ---------------------------------------------------------------------------

async def _send_and_measure(prompt: str, session_id: str) -> dict[str, Any]:
    """Send a prompt via WebSocket and measure wall-clock response time."""
    start = time.monotonic()
    response_text = ""
    agent_used = ""

    try:
        async with websockets.connect(WS_URI, open_timeout=10) as ws:
            await ws.send(json.dumps({
                "type": "message",
                "content": prompt,
                "session_id": session_id,
                "permissions": [],
            }))

            # Collect messages until message_complete or error
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
                    data = json.loads(msg)
                    msg_type = data.get("type", "")

                    if msg_type == "text":
                        response_text += data.get("content", "")
                    elif msg_type == "agent_start":
                        agent_used = data.get("agent", "")
                    elif msg_type == "message_complete":
                        break
                    elif msg_type == "error":
                        response_text = f"ERROR: {data.get('message', '')}"
                        break
                except asyncio.TimeoutError:
                    response_text = "TIMEOUT (30s)"
                    break
    except (OSError, websockets.exceptions.WebSocketException) as exc:
        response_text = f"ERROR: Connection failed — {exc}"

    elapsed = time.monotonic() - start
    return {
        "elapsed_seconds": round(elapsed, 2),
        "response_length": len(response_text),
        "agent_used": agent_used,
        "has_error": "ERROR" in response_text or "TIMEOUT" in response_text,
    }


# ---------------------------------------------------------------------------
# Results persistence
# ---------------------------------------------------------------------------

def _save_results(results: list[dict], summary: dict) -> None:
    """Write the full results payload to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": summary,
    }
    RESULTS_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _build_summary(results: list[dict]) -> dict[str, Any]:
    """Build summary statistics from individual results."""
    total = len(results)
    counts = {"ok": 0, "medium": 0, "high": 0, "critical": 0}
    elapsed_vals: list[float] = []

    for r in results:
        severity = r.get("severity", "ok")
        counts[severity] = counts.get(severity, 0) + 1
        elapsed_vals.append(r.get("elapsed_seconds", 0))

    avg = round(sum(elapsed_vals) / total, 2) if total else 0
    return {
        "total": total,
        "ok": counts["ok"],
        "medium": counts["medium"],
        "high": counts["high"],
        "critical": counts["critical"],
        "avg_seconds": avg,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _check_backend_reachable():
    """Skip the entire module if the backend WebSocket is not reachable."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect(("localhost", 8000))
        sock.close()
    except (ConnectionRefusedError, OSError, socket.timeout):
        pytest.skip("Backend not reachable at localhost:8000 — skipping response time tests")


# Module-level accumulator for results across parametrized tests
_session_results: list[dict] = []


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entry",
    PROFILING_PROMPTS,
    ids=[p["id"] for p in PROFILING_PROMPTS],
)
async def test_response_time(entry: dict[str, str], _check_backend_reachable) -> None:
    """Send a prompt via WebSocket and assert response time is acceptable."""
    prompt_id = entry["id"]
    prompt = entry["prompt"]
    expected_agent = entry["agent"]
    session_id = f"perf-{prompt_id}"

    # Throttle between prompts
    if _session_results:
        await asyncio.sleep(INTER_PROMPT_DELAY)

    result = await _send_and_measure(prompt, session_id)

    elapsed = result["elapsed_seconds"]
    severity = _classify_severity(elapsed)
    has_error = result["has_error"]

    record = {
        "id": prompt_id,
        "prompt": prompt,
        "agent": expected_agent,
        "elapsed_seconds": elapsed,
        "severity": severity,
        "response_length": result["response_length"],
        "agent_used": result["agent_used"],
        "has_error": has_error,
    }
    _session_results.append(record)

    # Persist results after every test (progressive save)
    summary = _build_summary(_session_results)
    _save_results(_session_results, summary)

    # Log warnings for slow responses
    if severity == "medium":
        print(f"\n  WARNING [{prompt_id}]: {elapsed}s (>5s) — severity: medium")
    elif severity == "high":
        print(f"\n  WARNING [{prompt_id}]: {elapsed}s (>10s) — severity: high")
    elif severity == "critical":
        print(f"\n  CRITICAL [{prompt_id}]: {elapsed}s (>20s) — severity: critical")

    # Hard assertions
    assert not has_error, (
        f"[{prompt_id}] Prompt returned an error or timed out after {elapsed}s"
    )
    assert elapsed <= RECV_TIMEOUT, (
        f"[{prompt_id}] Response exceeded hard timeout of {RECV_TIMEOUT}s (took {elapsed}s)"
    )
    assert severity != "critical", (
        f"[{prompt_id}] Response time {elapsed}s exceeds critical threshold (20s)"
    )


# ---------------------------------------------------------------------------
# Session summary
# ---------------------------------------------------------------------------

def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Print a compact summary table after all response-time tests complete."""
    if not _session_results:
        return

    summary = _build_summary(_session_results)

    header = f"{'ID':<25} {'AGENT':<15} {'TIME (s)':<10} {'SEVERITY':<10}"
    sep = "-" * 65
    print(f"\n{'=' * 65}")
    print(f"  Response Time Results  |  avg={summary['avg_seconds']}s  |  {summary['total']} prompts")
    print(f"{'=' * 65}")
    print(header)
    print(sep)

    for r in _session_results:
        sev = r["severity"].upper()
        marker = " <<<" if sev in ("HIGH", "CRITICAL") else ""
        print(f"{r['id']:<25} {r.get('agent', ''):<15} {r['elapsed_seconds']:<10} {sev}{marker}")

    print(sep)
    print(
        f"  ok={summary['ok']}  medium={summary['medium']}  "
        f"high={summary['high']}  critical={summary['critical']}  "
        f"avg={summary['avg_seconds']}s"
    )
    print(f"  Results saved: {RESULTS_FILE}\n")
