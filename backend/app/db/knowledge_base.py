"""Postgres-backed knowledge base for ON24 platform capabilities.

Ingests Zendesk help articles; stores OpenAI text-embedding-3-small embeddings
in the local databot Postgres DB. Cosine similarity search via numpy.
"""

import json
import logging
import re
from pathlib import Path

import numpy as np
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from sqlalchemy import text

from app.config import settings
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)

_ZENDESK_FILE = Path("/app/data/zendesk_articles.json")
_API_REF_FILE = Path("/app/data/on24_api_reference.json")
_EMBED_MODEL = "text-embedding-3-small"
_EMBED_DIMS = 1536
_BATCH_SIZE = 100  # OpenAI embeddings per API call

_openai: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai
    if _openai is None:
        _openai = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + max_chars])
        start += max_chars - overlap
    return chunks


async def _embed_batch(texts: list[str]) -> list[list[float]]:
    client = _get_openai()
    resp = await client.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


async def ingest_zendesk_articles() -> int:
    """Ingest Zendesk help articles into Postgres with OpenAI embeddings.

    Clears existing rows, re-embeds all chunks, and stores them.
    Returns article count.
    """
    if not _ZENDESK_FILE.exists():
        logger.warning(f"Zendesk file not found: {_ZENDESK_FILE}")
        return 0

    data = json.loads(_ZENDESK_FILE.read_text(encoding="utf-8"))
    articles = data.get("articles", [])

    rows: list[dict] = []
    for article in articles:
        title = article.get("title", "")
        body_text = _strip_html(article.get("body", ""))
        if not body_text or len(body_text) < 50:
            continue
        for i, chunk in enumerate(_chunk_text(f"{title}\n\n{body_text}")):
            rows.append({
                "article_id": str(article["id"]),
                "title": title,
                "url": article.get("html_url", ""),
                "chunk_index": i,
                "content": chunk,
            })

    if not rows:
        logger.warning("No articles to ingest")
        return 0

    # Embed in batches
    all_texts = [r["content"] for r in rows]
    embeddings: list[list[float]] = []
    for start in range(0, len(all_texts), _BATCH_SIZE):
        batch = all_texts[start : start + _BATCH_SIZE]
        embeddings.extend(await _embed_batch(batch))
        logger.info(f"Embedded {min(start + _BATCH_SIZE, len(all_texts))}/{len(all_texts)} chunks")

    for row, emb in zip(rows, embeddings):
        row["embedding"] = emb

    async with async_session_factory() as session:
        # Clear existing
        await session.execute(text("DELETE FROM knowledge_base_articles"))
        # Insert new rows in batches
        for start in range(0, len(rows), 500):
            batch = rows[start : start + 500]
            await session.execute(
                text("""
                    INSERT INTO knowledge_base_articles
                        (article_id, title, url, chunk_index, content, embedding)
                    VALUES
                        (:article_id, :title, :url, :chunk_index, :content, :embedding)
                """),
                batch,
            )
        await session.commit()

    logger.info(f"Ingested {len(articles)} articles ({len(rows)} chunks) into Postgres")
    return len(articles)


async def ingest_api_reference() -> int:
    """Ingest ON24 API reference endpoints into the knowledge base.

    Each endpoint becomes a searchable document alongside Zendesk articles.
    Does NOT clear existing rows — call after ingest_zendesk_articles.
    Returns endpoint count.
    """
    if not _API_REF_FILE.exists():
        logger.warning(f"API reference file not found: {_API_REF_FILE}")
        return 0

    data = json.loads(_API_REF_FILE.read_text(encoding="utf-8"))
    endpoints = data.get("endpoints", [])
    auth = data.get("authentication", {})
    base_urls = data.get("base_urls", {})

    # Build a preamble chunk for general API info
    preamble = (
        f"ON24 REST API v2 Overview\n\n"
        f"Base URLs: NA={base_urls.get('na','')}, EU={base_urls.get('eu','')}, "
        f"QA={base_urls.get('qa','')}\n"
        f"Authentication: {auth.get('description', '')}\n"
        f"Headers: {', '.join(auth.get('headers', []))}\n"
        f"Total endpoints: {len(endpoints)}"
    )

    rows: list[dict] = []
    # Preamble chunk
    rows.append({
        "article_id": "api_ref_overview",
        "title": "ON24 REST API v2 Overview",
        "url": "",
        "chunk_index": 0,
        "content": preamble,
    })

    for ep in endpoints:
        ep_id = ep.get("id", "unknown")
        title = f"ON24 API: {ep.get('name', '')} ({ep.get('method', '')} {ep.get('path', '')})"
        # Build rich text for embedding
        parts = [
            title,
            f"\nCategory: {ep.get('category', '')}",
            f"Content-Type: {ep.get('content_type', 'application/json')}",
            f"\n{ep.get('description', '')}",
        ]
        params = ep.get("parameters", [])
        if params:
            parts.append("\nParameters:")
            for p in params:
                req = " (required)" if p.get("required") else ""
                parts.append(f"  - {p.get('name', '')}: {p.get('type', 'string')}{req} — {p.get('description', '')}")
        notes = ep.get("notes", "")
        if notes:
            parts.append(f"\nNotes: {notes}")
        resp = ep.get("response_fields", [])
        if resp:
            parts.append("\nResponse fields:")
            for rf in resp:
                parts.append(f"  - {rf.get('name', '')}: {rf.get('description', '')}")

        body_text = "\n".join(parts)
        for i, chunk in enumerate(_chunk_text(body_text)):
            rows.append({
                "article_id": f"api_{ep_id}",
                "title": title,
                "url": "",
                "chunk_index": i,
                "content": chunk,
            })

    if not rows:
        logger.warning("No API endpoints to ingest")
        return 0

    all_texts = [r["content"] for r in rows]
    embeddings: list[list[float]] = []
    for start in range(0, len(all_texts), _BATCH_SIZE):
        batch = all_texts[start : start + _BATCH_SIZE]
        embeddings.extend(await _embed_batch(batch))
        logger.info(f"Embedded API ref {min(start + _BATCH_SIZE, len(all_texts))}/{len(all_texts)} chunks")

    for row, emb in zip(rows, embeddings):
        row["embedding"] = emb

    async with async_session_factory() as session:
        # Remove old API ref rows only (keep Zendesk rows)
        await session.execute(
            text("DELETE FROM knowledge_base_articles WHERE article_id LIKE 'api_%'")
        )
        for start in range(0, len(rows), 500):
            batch = rows[start : start + 500]
            await session.execute(
                text("""
                    INSERT INTO knowledge_base_articles
                        (article_id, title, url, chunk_index, content, embedding)
                    VALUES
                        (:article_id, :title, :url, :chunk_index, :content, :embedding)
                """),
                batch,
            )
        await session.commit()

    logger.info(f"Ingested {len(endpoints)} API endpoints ({len(rows)} chunks) into knowledge base")
    return len(endpoints)


async def query_knowledge(query: str, n_results: int = 5) -> list[dict]:
    """Search the knowledge base for relevant ON24 platform articles.

    Returns list of {title, url, excerpt} dicts.
    """
    client = _get_openai()
    resp = await client.embeddings.create(model=_EMBED_MODEL, input=[query])
    query_vec = np.array(resp.data[0].embedding, dtype=np.float32)

    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT article_id, title, url, chunk_index, content, embedding FROM knowledge_base_articles")
        )
        rows = result.fetchall()

    if not rows:
        # Attempt on-demand ingest
        logger.info("Knowledge base empty — triggering ingest")
        await ingest_zendesk_articles()
        await ingest_api_reference()
        async with async_session_factory() as session:
            result = await session.execute(
                text("SELECT article_id, title, url, chunk_index, content, embedding FROM knowledge_base_articles")
            )
            rows = result.fetchall()
        if not rows:
            return []

    # Cosine similarity
    scores: list[tuple[float, int]] = []
    for i, row in enumerate(rows):
        emb = np.array(row.embedding, dtype=np.float32)
        norm = np.linalg.norm(emb) * np.linalg.norm(query_vec)
        sim = float(np.dot(emb, query_vec) / norm) if norm > 0 else 0.0
        scores.append((sim, i))

    scores.sort(reverse=True)
    top = scores[:n_results * 3]  # over-fetch to deduplicate by title

    seen_titles: set[str] = set()
    output: list[dict] = []
    for sim, i in top:
        row = rows[i]
        title = row.title or ""
        if title in seen_titles:
            continue
        seen_titles.add(title)
        output.append({
            "title": title,
            "url": row.url or "",
            "excerpt": row.content[:300],
        })
        if len(output) >= n_results:
            break

    return output
