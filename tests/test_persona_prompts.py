"""test_persona_prompts.py — Regression tests using marketer and director persona prompts.

Loads prompts from tests/marketer_prompts.json and tests/director_prompts.json.
Each prompt is sent to the /api/chat endpoint and validated.

Usage:
    # Run all persona prompts (300 total — ~2.5 hours at 2s delay)
    pytest tests/test_persona_prompts.py -v

    # Run only marketer prompts
    pytest tests/test_persona_prompts.py -k marketer -v

    # Run only director prompts
    pytest tests/test_persona_prompts.py -k director -v

    # Run a specific category
    pytest tests/test_persona_prompts.py -k "Attendance" -v

    # Run first N prompts only (fast smoke test)
    pytest tests/test_persona_prompts.py -v --max-prompts 10

    # Print summary of last run
    pytest tests/test_persona_prompts.py --report-only
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
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
REQUEST_TIMEOUT = 45
INTER_TEST_DELAY = float(os.environ.get("TEST_DELAY", "2"))
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_FILE = RESULTS_DIR / "persona_test_results.json"

# ---------------------------------------------------------------------------
# Load prompts from JSON files
# ---------------------------------------------------------------------------

_prompts_dir = Path(__file__).parent


def _load_prompts(filename: str, persona: str) -> list[dict]:
    """Load prompts from a JSON file, adding persona tag and default validation fields."""
    filepath = _prompts_dir / filename
    if not filepath.exists():
        return []
    raw = json.loads(filepath.read_text(encoding="utf-8"))
    prompts = []
    for entry in raw:
        entry["persona"] = persona
        # Default forbidden phrases for all prompts
        entry.setdefault("forbidden", ["i cannot", "error", "i don't have access", "traceback"])
        # Map response_type to expect_chart
        rt = entry.get("response_type", "")
        entry.setdefault("expect_chart", "chart" in rt)
        prompts.append(entry)
    return prompts


MARKETER_PROMPTS = _load_prompts("marketer_prompts.json", "marketer")
DIRECTOR_PROMPTS = _load_prompts("director_prompts.json", "director")
ALL_PROMPTS = MARKETER_PROMPTS + DIRECTOR_PROMPTS


# ---------------------------------------------------------------------------
# Result storage
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


_session_results: list[dict] = []


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _chat(prompt: str, session_id: str) -> dict[str, Any]:
    payload = {"message": prompt, "session_id": session_id}
    response = requests.post(CHAT_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(entry: dict[str, Any], response: dict[str, Any]) -> tuple[bool, str]:
    text: str = response.get("text", "")
    chart_data = response.get("chart_data")
    reasons: list[str] = []

    if not text or not text.strip():
        reasons.append("text field is empty")

    if entry.get("expect_data"):
        stripped = text.strip().lower()
        none_phrases = ["none found.", "no events found", "no data found", "no results found"]
        if any(p in stripped for p in none_phrases):
            reasons.append(f"none-found placeholder: {text.strip()[:100]!r}")
        elif len(text.strip()) < 20:
            reasons.append(f"response too short ({len(text.strip())} chars)")

    text_lower = text.lower()
    for forbidden in entry.get("forbidden", []):
        if forbidden.lower() in text_lower:
            reasons.append(f"forbidden: {forbidden!r}")

    if entry.get("expect_chart") and not chart_data:
        reasons.append("expected chart_data but got null")

    return len(reasons) == 0, "; ".join(reasons)


# ---------------------------------------------------------------------------
# pytest hooks
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(session, config, items) -> None:
    if config.getoption("--report-only", default=False):
        for item in items:
            item.add_marker(pytest.mark.skip(reason="--report-only"))
        return

    max_prompts = config.getoption("--max-prompts", default=0)
    if max_prompts > 0 and len(items) > max_prompts:
        for item in items[max_prompts:]:
            item.add_marker(pytest.mark.skip(reason=f"--max-prompts={max_prompts}"))


# ---------------------------------------------------------------------------
# Test parametrize
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entry",
    ALL_PROMPTS,
    ids=[f"{e['persona']}_{e['id']}" for e in ALL_PROMPTS],
)
def test_persona_prompt(entry: dict[str, Any]) -> None:
    prompt_id = entry["id"]
    persona = entry["persona"]
    prompt = entry["prompt"]
    tool = entry.get("tool", "unknown")

    record: dict[str, Any] = {
        "id": prompt_id,
        "persona": persona,
        "category": entry.get("category", ""),
        "prompt": prompt,
        "tool": tool,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": False,
        "failure_reason": "",
        "response_text": "",
        "agent_used": None,
        "has_chart": False,
    }

    time.sleep(INTER_TEST_DELAY)
    session_id = f"test-{persona}-{prompt_id}"

    try:
        response = _chat(prompt, session_id=session_id)
    except requests.exceptions.Timeout:
        record["failure_reason"] = f"Timeout after {REQUEST_TIMEOUT}s"
        _session_results.append(record)
        _save_results(_session_results)
        pytest.fail(record["failure_reason"])
    except Exception as exc:
        record["failure_reason"] = f"Error: {exc}"
        _session_results.append(record)
        _save_results(_session_results)
        pytest.fail(record["failure_reason"])

    text = response.get("text", "")
    record["response_text"] = text[:500]
    record["agent_used"] = response.get("agent_used")
    record["has_chart"] = response.get("chart_data") is not None

    passed, failure_reason = _validate(entry, response)
    record["passed"] = passed
    record["failure_reason"] = failure_reason

    _session_results.append(record)
    _save_results(_session_results)

    if not passed:
        pytest.fail(
            f"[{persona}/{prompt_id}] {prompt!r}\n"
            f"  Tool: {tool} | Agent: {record['agent_used']}\n"
            f"  Failure: {failure_reason}\n"
            f"  Response: {text[:300]!r}"
        )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def pytest_sessionfinish(session, exitstatus) -> None:
    config = session.config
    if config.getoption("--report-only", default=False):
        results = _load_existing_results()
        sys.exit(_print_summary(results))
    elif _session_results:
        passed = sum(1 for r in _session_results if r["passed"])
        total = len(_session_results)
        print(f"\n[persona-regression] {passed}/{total} prompts passed — results: {RESULTS_FILE}")


def _print_summary(results: list[dict]) -> int:
    if not results:
        print("No results found. Run the test suite first.")
        return 1

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    # Per-category breakdown
    categories: dict[str, dict] = {}
    for r in results:
        cat = r.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    print(f"\n{'=' * 100}")
    print(f"  Persona Prompt Regression  |  {passed}/{total} passed  |  {failed} failed")
    print(f"{'=' * 100}")

    # Category summary
    print(f"\n{'Category':<40} {'Pass Rate':<15} {'Details'}")
    print("-" * 70)
    for cat, stats in sorted(categories.items()):
        rate = f"{stats['passed']}/{stats['total']}"
        pct = f"({stats['passed']*100//stats['total']}%)" if stats['total'] > 0 else ""
        print(f"{cat:<40} {rate:<15} {pct}")

    # Failed items
    if failed > 0:
        print(f"\n--- Failed Prompts ({failed}) ---")
        for r in results:
            if not r["passed"]:
                print(f"  {r['id']:<25} {r.get('category',''):<30} {r.get('failure_reason','')[:60]}")

    print(f"\n  Total: {total}  |  Passed: {passed}  |  Failed: {failed}\n")
    return 0 if failed == 0 else 1
