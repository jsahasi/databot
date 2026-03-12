"""test_marketer_prompts.py — Extended regression tests from marketer + director perspectives.

Loads test cases from:
  tests/marketer_prompts.json   — 200 post-webinar marketer questions
  tests/director_prompts.json   — 100 program-level director questions

Each JSON entry:
  id, category, prompt, tool, response_type, expect_data, notes

Usage:
    pytest tests/test_marketer_prompts.py -q
    pytest tests/test_marketer_prompts.py -k "Attendance" -v
    pytest tests/test_marketer_prompts.py --suite marketer
    pytest tests/test_marketer_prompts.py --suite director
"""

from __future__ import annotations

import json
import os
import re
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
SESSION_ID = "test-marketer"
REQUEST_TIMEOUT = 45
TESTS_DIR = Path(__file__).parent
RESULTS_DIR = TESTS_DIR / "results"

# ---------------------------------------------------------------------------
# Known data gaps — skip these regardless of prompt source
# ---------------------------------------------------------------------------

KNOWN_DATA_GAPS_KEYWORDS = {
    "poll", "polls", "resource", "resources", "download", "downloads",
    "partnerref", "traffic source",  # partnerref data gap for client 10710
}

# Response types that don't require substantive text
NO_DATA_RESPONSE_TYPES = {"none_found"}

# ---------------------------------------------------------------------------
# Load prompt suites
# ---------------------------------------------------------------------------

def _load_suite(filename: str) -> list[dict]:
    path = TESTS_DIR / filename
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _all_entries() -> list[dict]:
    marketer = _load_suite("marketer_prompts.json")
    director = _load_suite("director_prompts.json")
    return marketer + director


def _is_data_gap(entry: dict) -> bool:
    """Auto-skip entries that rely on known missing data."""
    if not entry.get("expect_data", True):
        return True
    prompt_lower = entry["prompt"].lower()
    notes_lower = (entry.get("notes") or "").lower()
    return any(kw in prompt_lower or kw in notes_lower for kw in KNOWN_DATA_GAPS_KEYWORDS)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(entry: dict, response: dict) -> tuple[bool, str]:
    text: str = response.get("text", "")
    chart_data = response.get("chart_data")
    reasons: list[str] = []

    if not text or not text.strip():
        reasons.append("text field is empty")

    if entry.get("expect_data") and entry.get("response_type") not in NO_DATA_RESPONSE_TYPES:
        stripped = text.strip().lower()
        none_phrases = ["none found.", "no events found", "no data found", "i cannot", "i don't have access"]
        if any(p in stripped for p in none_phrases):
            reasons.append(f"unexpected none/error response: {text.strip()[:120]!r}")
        elif len(text.strip()) < 15:
            reasons.append(f"response too short ({len(text.strip())} chars): {text.strip()!r}")

    if entry.get("response_type") in ("chart_bar", "chart_line", "chart_pie"):
        if not chart_data:
            reasons.append("expected chart_data but got null")

    bad_phrases = ["traceback", "500 internal", "syntaxerror", "keyerror", "typeerror"]
    text_lower = text.lower()
    for bp in bad_phrases:
        if bp in text_lower:
            reasons.append(f"error phrase in response: {bp!r}")

    return len(reasons) == 0, "; ".join(reasons)


# ---------------------------------------------------------------------------
# pytest parametrize
# ---------------------------------------------------------------------------

_entries = _all_entries()

@pytest.mark.parametrize(
    "entry",
    _entries,
    ids=[e["id"] for e in _entries],
)
def test_marketer_prompt(entry: dict[str, Any]) -> None:
    """Send a marketer/director prompt and validate the response."""
    if _is_data_gap(entry):
        pytest.skip(f"Known data gap: {entry['id']}")

    try:
        r = requests.post(
            CHAT_ENDPOINT,
            json={"message": entry["prompt"], "session_id": SESSION_ID},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        response = r.json()
    except requests.exceptions.Timeout:
        pytest.fail(f"Timed out after {REQUEST_TIMEOUT}s")
    except requests.exceptions.HTTPError as exc:
        pytest.fail(f"HTTP error: {exc}")
    except Exception as exc:
        pytest.fail(f"Unexpected error: {exc}")

    passed, reason = _validate(entry, response)

    # Write result to per-suite results file
    result_file = RESULTS_DIR / "marketer_test_results.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else []
    except Exception:
        existing = []
    existing.append({
        "id": entry["id"],
        "category": entry.get("category", ""),
        "prompt": entry["prompt"],
        "tool": entry.get("tool", ""),
        "response_type": entry.get("response_type", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failure_reason": reason,
        "response_text": response.get("text", "")[:500],
        "has_chart": bool(response.get("chart_data")),
    })
    result_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    if not passed:
        pytest.fail(reason)
