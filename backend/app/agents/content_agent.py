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
    (re.compile(r"\b(email|follow.?up)\b", re.I), "FOLLOWUPEMAI"),
    (re.compile(r"\b(social|linkedin|twitter|tweet)\b", re.I), "SOCIALMEDIAP"),
    (re.compile(r"\b(faq|frequently asked)\b", re.I), "FAQ"),
    (re.compile(r"\b(ebook|e-book|guide)\b", re.I), "EBOOK"),
    (re.compile(r"\b(key\s*takeaway|takeaway|summary)\b", re.I), "KEYTAKEAWAYS"),
    (re.compile(r"\b(blog|article|post)\b", re.I), "BLOG"),
]


# Block-level HTML tags used for density detection
_BLOCK_TAGS = re.compile(r"<(?:h[1-6]|p|div|article|section|ul|ol)\b", re.I)

# nh3 (Rust-based HTML sanitizer) — replaces fragile regex approach
try:
    import nh3 as _nh3
except ImportError:
    _nh3 = None  # type: ignore[assignment]

# Allowlisted tags and attributes for content HTML
_ALLOWED_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "br",
    "hr",
    "div",
    "span",
    "article",
    "section",
    "blockquote",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "a",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "s",
    "code",
    "pre",
    "mark",
    "small",
    "sub",
    "sup",
    "img",
    "figure",
    "figcaption",
}
_ALLOWED_ATTRS = {
    "*": {"class", "style", "id"},
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height", "loading"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
}


def _extract_html(text: str) -> tuple[str, str | None]:
    """Extract HTML from fenced ```html blocks or detect high HTML density.

    Returns (cleaned_text, extracted_html). cleaned_text has the fenced block
    removed. If no HTML found, returns (original_text, None).
    """
    # Try fenced ```html block first
    pattern = r"```html\s*\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        html = m.group(1).strip()
        cleaned = text[: m.start()] + text[m.end() :]
        return cleaned.strip(), html

    # Fallback: detect high density of block-level HTML tags (3+)
    if len(_BLOCK_TAGS.findall(text)) >= 3:
        return text, text

    return text, None


def _sanitize_html(html: str) -> str:
    """Sanitize HTML using nh3 (Rust-based allowlist sanitizer).

    Only permits safe structural/content tags. Strips all scripts, event
    handlers, javascript: URLs, iframes, forms, and other dangerous elements.
    """
    if _nh3 is not None:
        return _nh3.clean(
            html,
            tags=_ALLOWED_TAGS,
            attributes=_ALLOWED_ATTRS,
            url_schemes={"http", "https", "mailto", "data"},
            link_rel="noopener noreferrer",
        )
    # Fallback: aggressive strip if nh3 not installed (development only)
    logger.warning("nh3 not installed — using aggressive regex fallback for HTML sanitization")
    result = re.sub(r"<\s*script\b[^>]*>.*?</\s*script\s*>", "", html, flags=re.I | re.DOTALL)
    result = re.sub(r"<\s*(?:iframe|object|embed|form|input|link|meta)\b[^>]*/?>", "", result, flags=re.I)
    result = re.sub(r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", result, flags=re.I)
    return result


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


def _inject_banner(html: str, banner_url: str) -> str:
    """Inject a banner image at the top of HTML content, with 16:9 crop via CSS."""
    if not banner_url:
        return html
    # Sanitise URL to prevent attribute injection (escape quotes and angle brackets)
    safe_url = banner_url.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    banner_html = (
        '<div style="width:100%;max-height:300px;overflow:hidden;border-radius:12px;margin-bottom:1.5rem;">'
        f'<img src="{safe_url}" alt="Banner" style="width:100%;height:300px;object-fit:cover;object-position:center;" />'
        "</div>"
    )
    return banner_html + html


def _load_default_banner_url() -> str:
    """Load the banner image URL from the default brand template for the current client."""
    try:
        from app.api.brand_templates import _load_templates

        templates = _load_templates()  # uses get_client_id() internally
        for t in templates:
            if t.get("isDefault") and t.get("bannerImageUrl"):
                return t["bannerImageUrl"]
        for t in templates:
            if t.get("bannerImageUrl"):
                return t["bannerImageUrl"]
    except Exception as e:
        logger.debug(f"Banner URL load skipped: {e}")
    return ""


# Content types that should receive a banner image
_BANNER_CONTENT_TYPES = {"BLOG", "EBOOK"}


class ContentAgent:
    """Agent that analyzes event content, recommends strategy, and creates brand-voice content."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"
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
                                asyncio.create_task(self._write_audit_log(session_id, tool_name, tool_input, result))
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(result, default=str),
                                    }
                                )
                            except Exception as e:
                                logger.error(f"Tool {tool_name} failed: {e}")
                                asyncio.create_task(self._write_audit_log(session_id, tool_name, tool_input, None, error=str(e)))
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps({"error": str(e)}),
                                        "is_error": True,
                                    }
                                )
                        else:
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps({"error": f"Unknown tool: {tool_name}"}),
                                    "is_error": True,
                                }
                            )

                messages.append({"role": "user", "content": tool_results})
            else:
                text_parts = [block.text for block in response.content if hasattr(block, "text")]
                full_text = "\n".join(text_parts)
                cleaned_text, extracted_html = _extract_html(full_text)
                content_html = _sanitize_html(extracted_html) if extracted_html else None
                # Inject banner image for blog/ebook content
                if content_html and article_type in _BANNER_CONTENT_TYPES:
                    banner_url = _load_default_banner_url()
                    if banner_url:
                        content_html = _inject_banner(content_html, banner_url)
                return {
                    "text": cleaned_text,
                    "chart_data": None,
                    "tool_calls": tool_calls_made,
                    "content_html": content_html,
                }

        return {
            "text": "I've gathered the data but hit the analysis limit. Here's what I found so far.",
            "chart_data": None,
            "tool_calls": tool_calls_made,
            "content_html": None,
        }
