#!/usr/bin/env bash
# run_prompt_tests.sh — Run the chat-prompt regression suite and print a summary.
#
# Usage:
#   bash tests/run_prompt_tests.sh              # run all prompts
#   bash tests/run_prompt_tests.sh --report-only # show last saved results, no API calls
#   BACKEND_URL=http://my-host:8000 bash tests/run_prompt_tests.sh
#
# Exit codes:
#   0  — all prompts passed
#   1  — one or more prompts failed
#   3  — backend unreachable (pytest exits early)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_FILE="$SCRIPT_DIR/results/prompt_test_results.json"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}${BOLD}  Databot Chat-Prompt Regression Suite             ${RESET}"
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
echo -e "  Backend : ${BACKEND_URL}"
echo -e "  Results : ${RESULTS_FILE}"
echo ""

# ── Resolve Python / pytest ───────────────────────────────────────────────────
# Prefer the virtualenv inside the backend directory, then fall back to
# the system python / docker exec approach.

PYTEST_CMD=""

# 1. Backend virtualenv (most likely in CI / local dev with venv)
VENV_PYTEST="$PROJECT_ROOT/backend/.venv/bin/pytest"
if [ -x "$VENV_PYTEST" ]; then
    PYTEST_CMD="$VENV_PYTEST"
fi

# 2. Generic venv in project root
if [ -z "$PYTEST_CMD" ] && [ -x "$PROJECT_ROOT/.venv/bin/pytest" ]; then
    PYTEST_CMD="$PROJECT_ROOT/.venv/bin/pytest"
fi

# 3. System pytest
if [ -z "$PYTEST_CMD" ] && command -v pytest &>/dev/null; then
    PYTEST_CMD="pytest"
fi

# 4. Fall back to running inside the backend Docker container
if [ -z "$PYTEST_CMD" ]; then
    CONTAINER_NAME="${DATABOT_CONTAINER:-databot-backend-1}"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${YELLOW}No local pytest found — running inside Docker container: ${CONTAINER_NAME}${RESET}"
        docker exec -e BACKEND_URL="$BACKEND_URL" "$CONTAINER_NAME" \
            python -m pytest /app/tests/test_chat_prompts.py \
                --tb=short -q "$@"
        EXIT_CODE=$?
        _print_exit_banner $EXIT_CODE
        exit $EXIT_CODE
    fi
    echo -e "${RED}ERROR: pytest not found locally and no running backend container detected.${RESET}"
    echo "       Install pytest or start the backend container and retry."
    exit 1
fi

echo -e "  pytest  : ${PYTEST_CMD}"
echo ""

# ── Handle --report-only shortcut ────────────────────────────────────────────
if [[ "${1:-}" == "--report-only" ]]; then
    echo -e "${BOLD}Printing summary of last saved results (no API calls)...${RESET}"
    BACKEND_URL="$BACKEND_URL" "$PYTEST_CMD" \
        "$SCRIPT_DIR/test_chat_prompts.py" \
        --report-only \
        --tb=no -q
    exit $?
fi

# ── Run the tests ─────────────────────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/results"

echo -e "${BOLD}Running prompt regression tests...${RESET}"
echo ""

set +e   # don't exit on test failure — we want to print the summary ourselves
BACKEND_URL="$BACKEND_URL" "$PYTEST_CMD" \
    "$SCRIPT_DIR/test_chat_prompts.py" \
    --tb=short \
    -v \
    "$@"
PYTEST_EXIT=$?
set -e

# ── Print pass/fail summary from JSON report ─────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}${BOLD}  Summary                                          ${RESET}"
echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════${RESET}"

if [ -f "$RESULTS_FILE" ]; then
    python3 - "$RESULTS_FILE" <<'PYEOF'
import json, sys

results_path = sys.argv[1]
with open(results_path, encoding="utf-8") as fh:
    results = json.load(fh)

total  = len(results)
passed = sum(1 for r in results if r.get("passed"))
failed = total - passed

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

print(f"\n  {BOLD}{'ID':<35} {'TOOL':<30} {'STATUS':<8} REASON{RESET}")
print("  " + "-" * 100)

for r in results:
    status_str = f"{GREEN}PASS{RESET}" if r.get("passed") else f"{RED}FAIL{RESET}"
    reason     = (r.get("failure_reason") or "")[:60]
    tool       = (r.get("tool") or "")[:29]
    print(f"  {r['id']:<35} {tool:<30} {status_str:<17} {reason}")

print("  " + "-" * 100)
color = GREEN if failed == 0 else RED
print(f"\n  {color}{BOLD}Total: {total}  |  Passed: {passed}  |  Failed: {failed}{RESET}\n")
PYEOF
else
    echo -e "${YELLOW}No results file found at ${RESULTS_FILE}${RESET}"
fi

# ── Final exit code ───────────────────────────────────────────────────────────
if [ $PYTEST_EXIT -eq 0 ]; then
    echo -e "${GREEN}${BOLD}All prompt tests passed.${RESET}"
    exit 0
elif [ $PYTEST_EXIT -eq 3 ]; then
    echo -e "${RED}${BOLD}Backend was not reachable. Start the backend and retry.${RESET}"
    exit 3
else
    echo -e "${RED}${BOLD}One or more prompt tests failed. See details above.${RESET}"
    exit 1
fi
