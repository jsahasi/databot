"""conftest.py — project-root regression test suite.

Checks that the backend is reachable before running any prompt tests.
The backend is expected at http://localhost:8000.
"""

import pytest
import requests

BACKEND_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "prompt_regression: marks a test as a chat-prompt regression test",
    )


def _backend_is_up() -> tuple[bool, str]:
    """Return (reachable, reason)."""
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=10)
        if r.status_code == 200:
            return True, "ok"
        return False, f"HTTP {r.status_code}"
    except requests.ConnectionError as exc:
        return False, f"ConnectionError: {exc}"
    except requests.Timeout:
        return False, "Timeout after 10 s"


def pytest_sessionstart(session):
    """Abort the entire test session if the backend is not reachable."""
    reachable, reason = _backend_is_up()
    if not reachable:
        pytest.exit(
            f"\n[conftest] Backend is NOT reachable at {BACKEND_URL}. "
            f"Reason: {reason}\n"
            "Start the backend (docker compose up) and retry.\n",
            returncode=3,
        )
    else:
        print(f"\n[conftest] Backend is UP at {BACKEND_URL} — proceeding with tests.\n")


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL
