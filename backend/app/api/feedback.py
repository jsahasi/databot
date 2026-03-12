"""Feedback endpoint: stores user thumbs-up/down ratings on bot responses."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.on24_db import get_client_id

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_DIR = Path("/app/data")


class FeedbackRequest(BaseModel):
    feedback_type: str          # "positive" or "negative"
    feedback_text: str = ""     # user's explanation (thumbs-down only)
    message_content: str        # bot response text
    user_question: str = ""     # the question that triggered this response
    agent_used: str = ""        # e.g. "data_agent"
    message_timestamp: str = "" # ISO timestamp of the original message


def _build_improvement_prompt(req: FeedbackRequest, logged_at: datetime, client_id: int | str) -> str:
    """Build a structured LLM-ready prompt from the feedback context."""
    ts = logged_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    agent = req.agent_used or "unknown"

    lines = [
        "=== IMPROVEMENT FEEDBACK ===",
        f"Logged: {ts}",
        f"Client ID: {client_id}",
        f"Agent: {agent}",
        "",
        "USER QUESTION:",
        f'"{req.user_question}"' if req.user_question else "(not captured)",
        "",
        "BOT RESPONSE:",
        req.message_content.strip(),
        "",
        "USER FEEDBACK:",
        req.feedback_text.strip() if req.feedback_text else "(no details provided)",
        "",
        "--- IMPROVEMENT PROMPT ---",
        "The following bot response was flagged as incorrect by a user.",
        "Review the response and the user's complaint. Identify the most likely root cause",
        "and suggest a targeted fix — either to the agent prompt, query logic, or tool behavior.",
        "",
        f"User asked: {req.user_question!r}",
        f"Agent ({agent}) responded:",
        req.message_content.strip(),
        "",
        f"User says it's wrong because: {req.feedback_text.strip()!r}",
        "",
        "Investigate and suggest specific improvements to:",
        f"  1. backend/app/agents/prompts/{agent.replace('_agent', '')}_agent.md  (prompt rules)",
        f"  2. backend/app/agents/tools/on24_query_tools.py  (query logic, if data issue)",
        "  3. Any other relevant file based on the root cause",
        "",
        "Proposed fix:",
        "The user believes the correct data exists but the bot either missed it or got it wrong.",
        "Before suggesting a fix, work through these questions:",
        "",
        "  Q1. What data does the user expect? Describe it in plain English",
        "      (e.g. 'the most recent past event', 'total attendees across all events this year').",
        "",
        "  Q2. Where does that data live in on24master?",
        "      Name the table(s), column(s), and any join keys needed to retrieve it.",
        "",
        "  Q3. Is the data actually there? Write a SQL query that would fetch it",
        "      for client_id = {client_id} and confirm it returns the expected result.",
        "",
        "  Q4. Why did the bot miss it or get it wrong?",
        "      Choose one: (a) wrong table/column, (b) wrong filter or sort,",
        "      (c) agent misunderstood the question, (d) prompt rule conflict, (e) other.",
        "",
        "  Q5. What is the minimal one-line fix — SQL change, prompt rule addition, or tool param?",
        "",
        "Answer:",
        "(LLM to complete)",
        "=" * 60,
        "",
    ]
    return "\n".join(lines)


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Record a thumbs-up or thumbs-down on a bot response.

    Thumbs-down entries are written to data/improvement-inbox-MM-DD-YYYY.txt
    as a structured LLM-ready prompt for later review.
    """
    now = datetime.now(timezone.utc)

    if req.feedback_type == "negative":
        try:
            client_id = get_client_id()
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            filename = DATA_DIR / f"improvement-inbox-{now.strftime('%m-%d-%Y')}.txt"
            entry = _build_improvement_prompt(req, now, client_id)
            with open(filename, "a", encoding="utf-8") as f:
                f.write(entry)
            logger.info(f"Feedback written to {filename}")
        except Exception:
            logger.exception("Failed to write feedback")

    return {"status": "ok"}
