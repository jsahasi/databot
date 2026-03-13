"""Brand voice service.

Builds and maintains a brand voice JSON document from two sources:
  1. AI-generated content in on24master.video_library (AUTOGEN_ rows) — analyzed on startup
     if the file doesn't exist or is >30 days old.
  2. Company blog / news pages (optional) — scraped and merged at most once per month.

The resulting file is stored at data/brand_voice.json (Docker volume, persists across rebuilds).
"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import anthropic
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.db.on24_db import get_pool, get_tenant_client_ids

logger = logging.getLogger(__name__)

BRAND_VOICE_PATH = Path("data/brand_voice.json")

# Article types to analyse (TRANSCRIPT excluded — too verbose, low signal)
ANALYSABLE_TYPES = ["BLOG", "EBOOK", "FAQ", "KEYTAKEAWAYS", "FOLLOWUPEMAI", "SOCIALMEDIAP"]

# How many sample articles per type to feed the LLM for analysis
_SAMPLE_PER_TYPE = 8

_QUERY_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# ON24 DB helpers
# ---------------------------------------------------------------------------

async def _fetch_articles_by_type(article_type: str, limit: int = _SAMPLE_PER_TYPE) -> list[str]:
    """Return up to `limit` most-recent article texts for a given AUTOGEN_ type."""
    pool = await get_pool()
    client_ids = await get_tenant_client_ids()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT media_content
            FROM on24master.video_library
            WHERE source = $1
              AND client_id = ANY($2::bigint[])
              AND media_content IS NOT NULL
              AND TRIM(media_content) <> ''
            ORDER BY creation_timestamp DESC
            LIMIT $3
            """,
            f"AUTOGEN_{article_type}",
            client_ids,
            limit,
            timeout=_QUERY_TIMEOUT,
        )
    return [r["media_content"] for r in rows]


async def get_recent_articles(article_type: str, limit: int = 5) -> list[dict]:
    """Return last `limit` articles of a given type (never TRANSCRIPT).

    Used by the content agent to load context examples — not exposed to users.
    """
    if article_type.upper() == "TRANSCRIPT":
        return []
    pool = await get_pool()
    client_ids = await get_tenant_client_ids()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                replace(source, 'AUTOGEN_', '')  AS type,
                media_content                    AS text,
                creation_timestamp               AS created_at,
                source_event_id                  AS event_id
            FROM on24master.video_library
            WHERE source = $1
              AND client_id = ANY($2::bigint[])
              AND media_content IS NOT NULL
              AND TRIM(media_content) <> ''
            ORDER BY creation_timestamp DESC
            LIMIT $3
            """,
            f"AUTOGEN_{article_type.upper()}",
            client_ids,
            limit,
            timeout=_QUERY_TIMEOUT,
        )
    return [
        {
            "type": r["type"],
            "text": r["text"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "event_id": r["event_id"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# LLM analysis helpers
# ---------------------------------------------------------------------------

async def _analyse_type_voice(article_type: str, samples: list[str]) -> dict:
    """Ask the LLM to characterise the brand voice for a given article type."""
    if not samples:
        return {}

    # Truncate each sample to avoid context overflow
    truncated = [s[:1500] for s in samples]
    combined = "\n\n---\n\n".join(f"[Sample {i+1}]\n{t}" for i, t in enumerate(truncated))

    prompt = f"""You are a brand strategist. Analyse the following {len(samples)} {article_type} samples written for an ON24 marketing/webinar platform client. Identify their brand voice characteristics.

{combined}

Return ONLY valid JSON with this exact structure (no markdown, no commentary):
{{
  "tone": "2-sentence description of the overall tone",
  "sentence_style": "short description of sentence length, structure, and rhythm",
  "opening_style": "how articles typically open",
  "vocabulary_preferences": ["list", "of", "preferred", "words", "or", "phrases"],
  "avoid": ["things", "they", "never", "do"],
  "cta_patterns": "how they close or call to action",
  "example_phrases": ["3", "to", "5", "characteristic", "phrases"]
}}"""

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


async def _analyse_overall_voice(type_voices: dict) -> dict:
    """Synthesise an overall brand voice from all per-type analyses."""
    summary_input = json.dumps(type_voices, indent=2)
    prompt = f"""Given these per-content-type brand voice analyses for a company:

{summary_input}

Synthesise an overall brand voice. Return ONLY valid JSON (no markdown):
{{
  "voice_summary": "2-3 sentence overall description",
  "tone": "overall tone descriptor",
  "vocabulary_preferences": ["cross-type preferred terms"],
  "avoid": ["cross-type things to avoid"],
  "sentence_style": "overall sentence pattern"
}}"""

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Web scraping helpers
# ---------------------------------------------------------------------------

async def _discover_blog_urls(website: str) -> list[str]:
    """Try to find blog/news post URLs on the company website."""
    candidates = []
    base = website.rstrip("/")
    for path in ["/blog", "/news", "/insights", "/resources", "/articles"]:
        candidates.append(f"{base}{path}")

    found: list[str] = []
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0 (compatible; DataBot/1.0)"}) as client:
        for url in candidates:
            try:
                r = await client.get(url)
                if r.status_code == 200 and len(r.text) > 500:
                    found.append(url)
                    if len(found) >= 2:
                        break
            except Exception:
                continue
    return found


async def _extract_recent_posts(blog_url: str, max_posts: int = 6) -> list[str]:
    """Fetch a blog listing page and extract text excerpts from recent posts."""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0 (compatible; DataBot/1.0)"}) as client:
        r = await client.get(blog_url)
        if r.status_code != 200:
            return []

    soup = BeautifulSoup(r.text, "html.parser")

    # Remove boilerplate
    for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
        tag.decompose()

    # Heuristic: find article/post containers
    excerpts: list[str] = []
    containers = (
        soup.find_all("article")
        or soup.find_all(class_=re.compile(r"post|blog|article|entry", re.I))
    )

    for el in containers[:max_posts]:
        text = el.get_text(separator=" ", strip=True)
        if len(text) > 100:
            excerpts.append(text[:800])

    # Fallback: just grab paragraphs
    if not excerpts:
        paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 80]
        excerpts = paras[:max_posts]

    return excerpts


async def _analyse_web_voice(excerpts: list[str]) -> dict:
    """Use LLM to extract brand voice signals from web content."""
    combined = "\n\n---\n\n".join(f"[Post {i+1}]\n{t}" for i, t in enumerate(excerpts))
    prompt = f"""Analyse the following blog/news excerpts from a company website. Extract their brand voice.

{combined}

Return ONLY valid JSON (no markdown):
{{
  "tone": "description",
  "vocabulary_preferences": ["list"],
  "avoid": ["list"],
  "sentence_style": "description",
  "key_themes": ["recurring", "themes"],
  "example_phrases": ["characteristic", "phrases"]
}}"""

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_brand_voice() -> dict | None:
    """Load brand_voice.json from disk. Returns None if file doesn't exist."""
    if not BRAND_VOICE_PATH.exists():
        return None
    try:
        return json.loads(BRAND_VOICE_PATH.read_text())
    except Exception as e:
        logger.warning(f"Failed to read brand_voice.json: {e}")
        return None


def _save_brand_voice(data: dict) -> None:
    BRAND_VOICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRAND_VOICE_PATH.write_text(json.dumps(data, indent=2, default=str))
    logger.info(f"brand_voice.json saved ({BRAND_VOICE_PATH})")


def _is_stale(data: dict, field: str = "generated_at", max_days: int = 30) -> bool:
    ts = data.get(field)
    if not ts:
        return True
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt) > timedelta(days=max_days)
    except Exception:
        return True


async def analyse_from_video_library() -> dict:
    """Query ON24 DB, sample articles per type, run LLM analysis, save JSON.

    Safe to call repeatedly — merges into any existing data without losing web_voice.
    """
    logger.info("Brand voice: analysing from video_library …")
    existing = load_brand_voice() or {}

    type_voices: dict[str, dict] = {}
    covered_types: list[str] = []

    for article_type in ANALYSABLE_TYPES:
        try:
            samples = await _fetch_articles_by_type(article_type)
            if not samples:
                continue
            voice = await _analyse_type_voice(article_type, samples)
            type_voices[article_type] = voice
            covered_types.append(article_type)
            logger.info(f"Brand voice: analysed {article_type} ({len(samples)} samples)")
        except Exception as e:
            logger.warning(f"Brand voice: skipped {article_type}: {e}")

    if not type_voices:
        logger.warning("Brand voice: no article types found — skipping save")
        return existing

    # Overall synthesis
    try:
        overall = await _analyse_overall_voice(type_voices)
    except Exception as e:
        logger.warning(f"Brand voice: overall synthesis failed: {e}")
        overall = {}

    data = {
        **existing,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "covered_types": covered_types,
        "overall": overall,
        "by_type": type_voices,
    }
    _save_brand_voice(data)
    return data


async def update_from_web() -> dict:
    """Scrape the company website blog and merge voice signals into brand_voice.json.

    Skipped if COMPANY_WEBSITE_URL is not set, or if last web update was <30 days ago.
    """
    website = settings.company_website_url
    if not website:
        logger.info("Brand voice: COMPANY_WEBSITE_URL not set — skipping web update")
        return load_brand_voice() or {}

    existing = load_brand_voice() or {}
    if not _is_stale(existing, "web_last_updated"):
        logger.info("Brand voice: web voice is fresh — skipping web update")
        return existing

    logger.info(f"Brand voice: scraping {website} …")
    try:
        blog_urls = await _discover_blog_urls(website)
        if not blog_urls:
            logger.warning(f"Brand voice: no blog pages found at {website}")
            return existing

        all_excerpts: list[str] = []
        for url in blog_urls:
            excerpts = await _extract_recent_posts(url)
            all_excerpts.extend(excerpts)

        if not all_excerpts:
            logger.warning("Brand voice: no blog post content extracted")
            return existing

        web_voice = await _analyse_web_voice(all_excerpts[:12])
        existing["web_voice"] = web_voice
        existing["web_last_updated"] = datetime.now(timezone.utc).isoformat()
        existing["website"] = website
        _save_brand_voice(existing)
        logger.info("Brand voice: web update complete")
    except Exception as e:
        logger.warning(f"Brand voice: web update failed: {e}")

    return existing


async def refresh_if_stale() -> None:
    """Called at startup. Regenerate from ON24 DB if stale; update from web if stale."""
    data = load_brand_voice()
    if data is None or _is_stale(data, "generated_at"):
        data = await analyse_from_video_library()
    await update_from_web()
