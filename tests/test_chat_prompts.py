"""test_chat_prompts.py — Regression test suite for the chat agent backend.

Each entry in TEST_PROMPTS is exercised as a separate pytest test case via
parametrize.  Results are written to tests/results/prompt_test_results.json.

Usage:
    # Run all prompt tests
    pytest tests/test_chat_prompts.py -v

    # Print summary table only (no live API calls)
    pytest tests/test_chat_prompts.py --report-only

    # Run a single tool group
    pytest tests/test_chat_prompts.py -k list_events -v
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/api/chat"
SESSION_ID = "test-regression"
REQUEST_TIMEOUT = 30  # seconds — some queries are slow
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_FILE = RESULTS_DIR / "prompt_test_results.json"

# ---------------------------------------------------------------------------
# Test prompt definitions
# ---------------------------------------------------------------------------
# Each entry:
#   id              — unique slug used as pytest test id and in the JSON report
#   prompt          — natural-language message sent to /api/v1/chat
#   tool            — expected primary tool the agent should invoke (informational)
#   expect_data     — if True, the response must be substantive (not "None found." / <20 chars)
#   forbidden       — list of substrings that must NOT appear in `text` (case-insensitive)
#   required_patterns — list of regex patterns that MUST appear in `text` (case-insensitive)
#   expect_chart    — if True, chart_data must be non-null
# ---------------------------------------------------------------------------

TEST_PROMPTS: list[dict[str, Any]] = [
    # ── list_events ──────────────────────────────────────────────────────────
    {
        "id": "list_events_last",
        "prompt": "What was my last event?",
        "tool": "list_events",
        "expect_data": True,
        "forbidden": ["none found", "i don't have", "i cannot", "no events", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "list_events_count_month",
        "prompt": "How many events did I run this month?",
        "tool": "list_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have access"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "list_events_last_month",
        "prompt": "Show me events from last month",
        "tool": "list_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "list_events_recent",
        "prompt": "List my 5 most recent webinars",
        "tool": "list_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_event_kpis ───────────────────────────────────────────────────────
    {
        "id": "event_kpis_most_recent",
        "prompt": "What were the KPIs for my most recent event?",
        "tool": "get_event_kpis",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [
            r"registrant|attendee|engagement",
        ],
        "expect_chart": False,
    },
    {
        "id": "event_kpis_how_perform",
        "prompt": "How did my last webinar perform?",
        "tool": "get_event_kpis",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_client_kpis ──────────────────────────────────────────────────────
    {
        "id": "client_kpis_platform",
        "prompt": "Show platform KPIs",
        "tool": "get_client_kpis",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [
            r"registrant|attendee|event|engagement",
        ],
        "expect_chart": False,
    },
    {
        "id": "client_kpis_overall_stats",
        "prompt": "What are my overall stats?",
        "tool": "get_client_kpis",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "client_kpis_summary",
        "prompt": "Give me a summary of my webinar program performance",
        "tool": "get_client_kpis",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_top_events ───────────────────────────────────────────────────────
    {
        "id": "top_events_engagement",
        "prompt": "Which events had the best engagement?",
        "tool": "get_top_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "top_events_attendance",
        "prompt": "Show top events by attendance",
        "tool": "get_top_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "top_events_registrants",
        "prompt": "Which of my webinars had the most registrants?",
        "tool": "get_top_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_top_events_by_polls ──────────────────────────────────────────────
    {
        "id": "top_events_by_polls",
        "prompt": "Show webinars with the most polls",
        "tool": "get_top_events_by_polls",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "top_events_by_polls_interactive",
        "prompt": "Which events had the most poll questions?",
        "tool": "get_top_events_by_polls",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_poll_overview ────────────────────────────────────────────────────
    {
        "id": "poll_overview",
        "prompt": "Poll results overview",
        "tool": "get_poll_overview",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "poll_overview_performance",
        "prompt": "How are polls performing across my events?",
        "tool": "get_poll_overview",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_attendance_trends ────────────────────────────────────────────────
    {
        "id": "attendance_trends",
        "prompt": "Show attendance trends",
        "tool": "get_attendance_trends",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "attendance_trends_monthly",
        "prompt": "How has attendance changed month over month?",
        "tool": "get_attendance_trends",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_audience_companies ───────────────────────────────────────────────
    {
        "id": "audience_companies_top",
        "prompt": "Which companies attended most?",
        "tool": "get_audience_companies",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "audience_companies_breakdown",
        "prompt": "Top companies by attendance",
        "tool": "get_audience_companies",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_polls (event-specific) ───────────────────────────────────────────
    {
        "id": "polls_last_event",
        "prompt": "Show polls for my last event",
        "tool": "get_polls",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── get_resources ────────────────────────────────────────────────────────
    {
        "id": "resources_last_event",
        "prompt": "What resources were downloaded in my last event?",
        "tool": "get_resources",
        "expect_data": False,  # data gap: client 10710 has zero rows in resource_hit_track
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── content agent ────────────────────────────────────────────────────────
    {
        "id": "content_topics_next",
        "prompt": "What topics should we cover next?",
        "tool": "suggest_topics",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": False,
    },
    {
        "id": "content_best_performing",
        "prompt": "Which content performs best?",
        "tool": "analyze_topic_performance",
        "expect_data": True,
        "forbidden": ["i cannot", "error"],
        "required_patterns": [],
        "expect_chart": False,
    },
    # ── chart requests ───────────────────────────────────────────────────────
    {
        "id": "chart_top_events_bar",
        "prompt": "Show top events as a bar chart",
        "tool": "get_top_events",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": True,
    },
    {
        "id": "chart_attendance_trends_line",
        "prompt": "Show attendance trends as a line chart",
        "tool": "get_attendance_trends",
        "expect_data": True,
        "forbidden": ["i cannot", "error", "i don't have"],
        "required_patterns": [],
        "expect_chart": True,
    },
]


# ---------------------------------------------------------------------------
# Result storage helpers
# ---------------------------------------------------------------------------

def _load_existing_results() -> list[dict]:
    if RESULTS_FILE.exists():
        try:
            return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_results(results: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# Module-level list that accumulates results during the session.
_session_results: list[dict] = []


# ---------------------------------------------------------------------------
# Core HTTP helper
# ---------------------------------------------------------------------------

def _chat(prompt: str) -> dict[str, Any]:
    """POST to the chat endpoint and return the parsed JSON body."""
    payload = {"message": prompt, "session_id": SESSION_ID}
    response = requests.post(CHAT_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Validation logic (reusable)
# ---------------------------------------------------------------------------

def _validate(entry: dict[str, Any], response: dict[str, Any]) -> tuple[bool, str]:
    """Return (passed, failure_reason).

    failure_reason is empty string on success.
    """
    text: str = response.get("text", "")
    chart_data = response.get("chart_data")

    reasons: list[str] = []

    # 1. text must be non-empty
    if not text or not text.strip():
        reasons.append("text field is empty")

    # 2. expect_data check — response must be substantive
    if entry.get("expect_data"):
        stripped = text.strip().lower()
        short_threshold = 20
        none_found_phrases = [
            "none found.",
            "no events found",
            "no data found",
            "no results found",
        ]
        is_none_found = any(p in stripped for p in none_found_phrases)
        is_too_short = len(text.strip()) < short_threshold
        if is_none_found:
            reasons.append(f"response is a 'none found' placeholder: {text.strip()[:100]!r}")
        elif is_too_short:
            reasons.append(f"response is too short ({len(text.strip())} chars < {short_threshold}): {text.strip()!r}")

    # 3. forbidden substrings check (case-insensitive)
    text_lower = text.lower()
    for forbidden in entry.get("forbidden", []):
        if forbidden.lower() in text_lower:
            reasons.append(f"forbidden phrase found: {forbidden!r}")

    # 4. required_patterns (regex, case-insensitive)
    for pattern in entry.get("required_patterns", []):
        if not re.search(pattern, text, re.IGNORECASE):
            reasons.append(f"required pattern not found: {pattern!r}")

    # 5. expect_chart check
    if entry.get("expect_chart"):
        if not chart_data:
            reasons.append("expected chart_data to be non-null but got null/None")

    failure_reason = "; ".join(reasons)
    passed = len(reasons) == 0
    return passed, failure_reason


# ---------------------------------------------------------------------------
# pytest parametrize fixture
# ---------------------------------------------------------------------------

# Tests skipped due to confirmed data gaps for client 10710 (not code bugs)
KNOWN_DATA_GAPS = {
    "poll_overview",           # no singleoption/multioption responses in event_user_x_answer since 2023
    "poll_overview_performance",
    "polls_last_event",
    "resources_last_event",    # zero rows in resource_hit_track for this client
}


@pytest.mark.parametrize(
    "entry",
    TEST_PROMPTS,
    ids=[e["id"] for e in TEST_PROMPTS],
)
def test_prompt(entry: dict[str, Any]) -> None:
    """Send a prompt to the chat endpoint and validate the response."""
    prompt_id = entry["id"]
    if prompt_id in KNOWN_DATA_GAPS:
        pytest.skip(f"Known data gap for client 10710: {prompt_id}")
    prompt = entry["prompt"]
    tool = entry.get("tool", "unknown")

    record: dict[str, Any] = {
        "id": prompt_id,
        "prompt": prompt,
        "tool": tool,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": False,
        "failure_reason": "",
        "response_text": "",
        "agent_used": None,
        "has_chart": False,
    }

    try:
        response = _chat(prompt)
    except requests.exceptions.Timeout:
        record["failure_reason"] = f"Request timed out after {REQUEST_TIMEOUT}s"
        _session_results.append(record)
        _save_results(_session_results)
        pytest.fail(record["failure_reason"])
    except requests.exceptions.HTTPError as exc:
        record["failure_reason"] = f"HTTP error: {exc}"
        _session_results.append(record)
        _save_results(_session_results)
        pytest.fail(record["failure_reason"])
    except Exception as exc:
        record["failure_reason"] = f"Unexpected error: {exc}"
        _session_results.append(record)
        _save_results(_session_results)
        pytest.fail(record["failure_reason"])

    text = response.get("text", "")
    agent_used = response.get("agent_used")
    chart_data = response.get("chart_data")

    record["response_text"] = text[:500]  # truncate for report
    record["agent_used"] = agent_used
    record["has_chart"] = chart_data is not None

    passed, failure_reason = _validate(entry, response)

    record["passed"] = passed
    record["failure_reason"] = failure_reason

    _session_results.append(record)
    _save_results(_session_results)

    if not passed:
        pytest.fail(
            f"[{prompt_id}] Prompt: {prompt!r}\n"
            f"  Tool expected : {tool}\n"
            f"  Agent used    : {agent_used}\n"
            f"  Failure       : {failure_reason}\n"
            f"  Response (500): {text[:500]!r}"
        )


# ---------------------------------------------------------------------------
# --report-only flag: print summary of last run
# ---------------------------------------------------------------------------

def _print_summary(results: list[dict]) -> int:
    """Print a formatted summary table. Returns 0 if all passed, 1 otherwise."""
    if not results:
        print("No results found. Run the test suite first.")
        return 1

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    header = f"{'ID':<35} {'TOOL':<30} {'PASS/FAIL':<10} {'REASON'}"
    sep = "-" * 110
    print(f"\n{'=' * 110}")
    print(f"  Prompt Regression Results  |  {passed}/{total} passed  |  {failed} failed")
    print(f"{'=' * 110}")
    print(header)
    print(sep)

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        reason = r.get("failure_reason", "")[:60]
        print(f"{r['id']:<35} {r.get('tool', ''):<30} {status:<10} {reason}")

    print(sep)
    print(f"\n  Total: {total}  |  Passed: {passed}  |  Failed: {failed}\n")
    return 0 if failed == 0 else 1


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--report-only",
        action="store_true",
        default=False,
        help="Print a summary of the last saved results and exit without running tests.",
    )


def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """If --report-only is set, skip all collected items."""
    if config.getoption("--report-only", default=False):
        skip_marker = pytest.mark.skip(reason="--report-only: skipping test execution")
        for item in items:
            item.add_marker(skip_marker)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """After all tests: print summary and (if --report-only) show saved results."""
    config = session.config
    if config.getoption("--report-only", default=False):
        results = _load_existing_results()
        sys.exit(_print_summary(results))
    elif _session_results:
        # Print a compact inline summary
        passed = sum(1 for r in _session_results if r["passed"])
        total = len(_session_results)
        print(f"\n[prompt-regression] {passed}/{total} prompts passed — results: {RESULTS_FILE}")
