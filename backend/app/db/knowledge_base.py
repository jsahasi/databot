"""ChromaDB knowledge base for ON24 platform capabilities.

Ingests Zendesk help articles to provide platform-aware redirects when users
ask overly broad questions or need guidance on ON24 features.
"""

import json
import logging
import re
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_CHROMA_DIR = Path("/app/data/chromadb")
_ZENDESK_FILE = Path("/app/data/zendesk-merge-20260226.json")
_client: chromadb.ClientAPI | None = None
_collection_name = "on24_knowledge"


def _strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _chunk_text(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start += max_chars - overlap
    return chunks


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    return _client


def ingest_zendesk_articles() -> int:
    """Ingest Zendesk help articles into ChromaDB. Returns article count."""
    if not _ZENDESK_FILE.exists():
        logger.warning(f"Zendesk file not found: {_ZENDESK_FILE}")
        return 0

    client = _get_client()

    # Delete existing collection if it exists (re-ingest)
    try:
        client.delete_collection(_collection_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=_collection_name,
        metadata={"description": "ON24 platform knowledge base from Zendesk help articles"},
    )

    data = json.loads(_ZENDESK_FILE.read_text(encoding="utf-8"))
    articles = data.get("articles", [])

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for article in articles:
        title = article.get("title", "")
        body_html = article.get("body", "")
        body_text = _strip_html(body_html)

        if not body_text or len(body_text) < 50:
            continue

        # Chunk long articles
        chunks = _chunk_text(f"{title}\n\n{body_text}")
        for i, chunk in enumerate(chunks):
            doc_id = f"article_{article['id']}_{i}"
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append({
                "article_id": str(article["id"]),
                "title": title,
                "url": article.get("html_url", ""),
                "chunk_index": i,
            })

    if ids:
        # ChromaDB handles batching internally
        batch_size = 500
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

    logger.info(f"Ingested {len(articles)} articles ({len(ids)} chunks) into ChromaDB")
    return len(articles)


async def query_knowledge(query: str, n_results: int = 5) -> list[dict]:
    """Search the knowledge base for relevant ON24 platform articles.

    Returns list of {title, url, excerpt} dicts.
    """
    client = _get_client()
    try:
        collection = client.get_collection(_collection_name)
    except Exception:
        # Collection doesn't exist yet — try ingesting
        ingest_zendesk_articles()
        try:
            collection = client.get_collection(_collection_name)
        except Exception:
            return []

    results = collection.query(query_texts=[query], n_results=n_results)

    seen_titles: set[str] = set()
    output: list[dict] = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i]
        title = meta.get("title", "")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        output.append({
            "title": title,
            "url": meta.get("url", ""),
            "excerpt": doc[:300],
        })

    return output
