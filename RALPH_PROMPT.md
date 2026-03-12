# Ralph Loop — Regression Test Fixer

You are iterating on a webinar analytics chatbot to fix failing regression tests.
Run the test suite, identify failures, fix root causes, loop until all non-poll tests pass or 2 hours elapsed.

## Start of each iteration

1. Record current time. If more than 2 hours have elapsed since first iteration, stop.
2. Run: `cd C:/Users/jayesh.sahasi/databot && python -m pytest tests/test_chat_prompts.py -q --tb=no 2>&1`
3. If all non-poll tests pass → output `<promise>REGRESSION TESTS FIXED</promise>` and stop.
4. For each failing non-poll test, investigate and fix.

## Test command
```
cd C:/Users/jayesh.sahasi/databot && python -m pytest tests/test_chat_prompts.py -q --tb=short 2>&1
```

## Known skips — do NOT fix, data gap not code
- poll_overview
- poll_overview_performance
- polls_last_event
Reason: client 10710 has zero poll responses in event_user_x_answer since 2023.

## Targets to fix
- resources_last_event
- content_topics_next
- chart_top_events_bar
- chart_attendance_trends_line

## Investigate a failure
1. `python -m pytest tests/test_chat_prompts.py::test_prompt[ID] -v --tb=long`
2. Read `tests/results/prompt_test_results.json` for the failure reason and actual response
3. `docker compose logs backend --tail=50` for errors
4. Fix in `backend/app/agents/` or `backend/app/agents/tools/`
5. `docker compose restart backend`
6. Re-run the specific test

## After fixing
- `docker compose restart backend` after any backend change
- `docker compose up --build -d frontend` after any frontend change
- Commit every 3-4 fixes: `git add -A && git commit -m "fix: ..."`
- Push: `git push origin main`

## Architecture
- Data agent tools: `backend/app/agents/tools/on24_query_tools.py` + `__init__.py`
- Content agent tools: `backend/app/agents/tools/content_tools.py`
- Agent prompts: `backend/app/agents/prompts/`
- `generate_chart_data` is async — captured when `tool_name == "generate_chart_data"`
- All DB queries scope to client via `get_tenant_client_ids()`
- ON24 DB = on24master schema via asyncpg

## Done condition
Output `<promise>REGRESSION TESTS FIXED</promise>` when:
- All non-poll tests pass, OR
- 2 hours elapsed from first iteration
