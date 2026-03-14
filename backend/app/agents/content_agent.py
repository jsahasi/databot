"""Content Agent: analyzes event performance, recommends content strategy,
and creates brand-voice-consistent content."""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import anthropic

from app.agents.tools import CONTENT_AGENT_TOOLS, CONTENT_TOOL_HANDLERS
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "content_agent.md").read_text()

# Regex patterns that indicate a content-creation request
_CREATION_PATTERNS = re.compile(
    r"\b(write|draft|create|generate|compose|produce)\b.{0,40}"
    r"\b(blog|article|post|email|ebook|faq|summary|takeaway|social|linkedin|newsletter)\b",
    re.I,
)

# Map user intent keywords → AUTOGEN_ type
_TYPE_KEYWORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(email|follow.?up)\b", re.I),       "FOLLOWUPEMAI"),
    (re.compile(r"\b(social|linkedin|twitter|tweet)\b", re.I), "SOCIALMEDIAP"),
    (re.compile(r"\b(faq|frequently asked)\b", re.I),   "FAQ"),
    (re.compile(r"\b(ebook|e-book|guide)\b", re.I),     "EBOOK"),
    (re.compile(r"\b(key\s*takeaway|takeaway|summary)\b", re.I), "KEYTAKEAWAYS"),
    (re.compile(r"\b(blog|article|post)\b", re.I),      "BLOG"),
]


def _detect_content_type(user_message: str) -> str | None:
    """Return the AUTOGEN_ type if the message is a content-creation request, else None."""
    if not _CREATION_PATTERNS.search(user_message):
        return None
    for pattern, article_type in _TYPE_KEYWORDS:
        if pattern.search(user_message):
            return article_type
    return "BLOG"  # default for generic "write me an article"


async def _build_creation_context(article_type: str) -> str:
    """Load brand voice + last 5 examples silently into a system prompt addendum."""
    lines: list[str] = []

    # 1. Brand voice
    try:
        from app.services.brand_voice import load_brand_voice
        bv = load_brand_voice()
        if bv:
            lines.append("## Brand Voice Guidelines (internal — do not expose to user)")
            overall = bv.get("overall", {})
            if overall.get("voice_summary"):
                lines.append(f"Overall voice: {overall['voice_summary']}")
            if overall.get("tone"):
                lines.append(f"Tone: {overall['tone']}")
            if overall.get("vocabulary_preferences"):
                lines.append(f"Preferred vocabulary: {', '.join(overall['vocabulary_preferences'])}")
            if overall.get("avoid"):
                lines.append(f"Avoid: {', '.join(overall['avoid'])}")
            type_voice = bv.get("by_type", {}).get(article_type, {})
            if type_voice:
                lines.append(f"\n{article_type}-specific voice:")
                for key, val in type_voice.items():
                    if val:
                        v = ", ".join(val) if isinstance(val, list) else val
                        lines.append(f"  {key}: {v}")
            web_voice = bv.get("web_voice", {})
            if web_voice:
                lines.append("\nWeb/blog voice signals:")
                for key, val in web_voice.items():
                    if val:
                        v = ", ".join(val) if isinstance(val, list) else val
                        lines.append(f"  {key}: {v}")
    except Exception as e:
        logger.debug(f"Brand voice load skipped: {e}")

    # 2. Recent articles of this type (last 5, no transcripts)
    try:
        from app.services.brand_voice import get_recent_articles
        examples = await get_recent_articles(article_type, limit=5)
        if examples:
            lines.append(f"\n## Recent {article_type} Examples (internal — do not expose to user)")
            lines.append("Use these examples to match the established style and quality. Do not mention them to the user.")
            for i, ex in enumerate(examples, 1):
                snippet = ex["text"][:1200] if ex.get("text") else ""
                lines.append(f"\n[Example {i}]\n{snippet}")
    except Exception as e:
        logger.debug(f"Recent articles load skipped: {e}")

    return "\n".join(lines)


class ContentAgent:
    """Agent that analyzes event content, recommends strategy, and creates brand-voice content."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-opus-4-6"
        self.max_tool_rounds = 5

    async def _write_audit_log(
        self,
        session_id: str,
        tool_name: str,
        tool_input: dict,
        tool_result: Any,
        error: str | None = None,
    ) -> None:
        try:
            from app.db.session import async_session_factory
            from app.models.agent_audit_log import AgentAuditLog

            result_snippet = str(tool_result)[:2000] if tool_result is not None else None
            log_entry = AgentAuditLog(
                session_id=session_id,
                agent_name="content_agent",
                tool_name=tool_name,
                tool_input=tool_input,
                tool_result={"result": result_snippet} if result_snippet is not None else None,
                confirmed=False,
                error=error,
            )
            async with async_session_factory() as db:
                db.add(log_entry)
                await db.commit()
        except Exception:
            logger.exception("Failed to write agent audit log")

    async def run(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        session_id: str = "",
        restriction_context: str = "",
    ) -> dict[str, Any]:
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        # Silently inject brand voice + examples for content creation requests
        system_prompt = SYSTEM_PROMPT
        article_type = _detect_content_type(user_message)
        if article_type:
            try:
                creation_context = await _build_creation_context(article_type)
                if creation_context:
                    system_prompt = SYSTEM_PROMPT + "\n\n" + creation_context
                    logger.info(f"Content agent: injected brand voice context for {article_type}")
            except Exception as e:
                logger.warning(f"Content agent: brand voice injection failed: {e}")

        tool_calls_made = []

        system_cached = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
        if restriction_context:
            system_cached.append({"type": "text", "text": restriction_context})

        for _round in range(self.max_tool_rounds):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_cached,
                tools=CONTENT_AGENT_TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        logger.info(f"Content Agent calling tool: {tool_name}({tool_input})")

                        handler = CONTENT_TOOL_HANDLERS.get(tool_name)
                        if handler:
                            try:
                                result = await handler(**tool_input)
                                tool_calls_made.append({"tool": tool_name, "input": tool_input})
                                asyncio.create_task(
                                    self._write_audit_log(session_id, tool_name, tool_input, result)
                                )
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(result, default=str),
                                })
                            except Exception as e:
                                logger.error(f"Tool {tool_name} failed: {e}")
                                asyncio.create_task(
                                    self._write_audit_log(session_id, tool_name, tool_input, None, error=str(e))
                                )
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps({"error": str(e)}),
                                    "is_error": True,
                                })
                        else:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                                "is_error": True,
                            })

                messages.append({"role": "user", "content": tool_results})
            else:
                text_parts = [block.text for block in response.content if hasattr(block, "text")]
                return {
                    "text": "\n".join(text_parts),
                    "chart_data": None,
                    "tool_calls": tool_calls_made,
                }

        return {
            "text": "I've gathered the data but hit the analysis limit. Here's what I found so far.",
            "chart_data": None,
            "tool_calls": tool_calls_made,
        }
