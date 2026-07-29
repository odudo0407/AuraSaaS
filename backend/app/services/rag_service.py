"""RAG service for local Markdown SOP knowledge.

The service prefers ChromaDB when available and keeps a simple keyword fallback so the
open-source demo still works without embeddings or network access.

Query results are cached via Redis (with in-memory fallback) with a 5-min TTL
to reduce redundant vector searches.
"""

from __future__ import annotations

import hashlib
import re
from app.core.redis_client import redis_client
from pathlib import Path
from typing import Iterable
from app.core.config import get_settings

ROOT_DIR = Path(__file__).resolve().parents[3]
KNOWLEDGE_DIR = ROOT_DIR / "docs" / "knowledge"

_COLLECTION_NAME = "aurasaas_knowledge_v2"


def _get_ef():
    try:
        import os
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        from chromadb.utils import embedding_functions
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-zh-v1.5",
        )
    except Exception:
        return None


def _read_markdown_files() -> list[dict]:
    docs = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = next((line.lstrip("# ").strip() for line in content.splitlines() if line.startswith("#")), path.stem)
        docs.append({
            "title": title,
            "source": str(path.relative_to(ROOT_DIR)).replace("\\", "/"),
            "category": path.stem,
            "tags": path.stem.replace("_", ","),
            "content": content,
        })
    return docs


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> Iterable[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(normalized) <= chunk_size:
        yield normalized
        return
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        yield normalized[start:end]
        if end == len(normalized):
            break
        start = max(0, end - overlap)


def ingest_documents() -> dict:
    """Ingest Markdown knowledge into ChromaDB when available."""

    settings = get_settings()
    docs = _read_markdown_files()
    chunks = []
    metadatas = []
    ids = []

    for doc in docs:
        for idx, chunk in enumerate(_chunk_text(doc["content"])):
            ids.append(f"{Path(doc['source']).stem}-{idx}")
            chunks.append(chunk)
            metadatas.append({
                "title": doc["title"],
                "source": doc["source"],
                "category": doc["category"],
                "tags": doc["tags"],
                "scope": "public",
                "tenant_id": "public",
            })

    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_dir)
        collection = client.get_or_create_collection(
            _COLLECTION_NAME, embedding_function=_get_ef()
        )
        if ids:
            existing = collection.get(ids=ids)
            existing_ids = set(existing.get("ids", []))
            new_items = [(i, c, m) for i, c, m in zip(ids, chunks, metadatas) if i not in existing_ids]
            if new_items:
                collection.add(
                    ids=[item[0] for item in new_items],
                    documents=[item[1] for item in new_items],
                    metadatas=[item[2] for item in new_items],
                )
        return {"success": True, "documents": len(docs), "chunks": len(chunks), "backend": "chromadb"}
    except Exception as exc:
        return {"success": False, "documents": len(docs), "chunks": len(chunks), "backend": "keyword", "error": str(exc)}


def _keyword_query(query: str, top_k: int) -> list[dict]:
    tokens = [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", query) if token.strip()]
    scored = []
    for doc in _read_markdown_files():
        haystack = f"{doc['title']} {doc['tags']} {doc['content']}".lower()
        score = sum(haystack.count(token) for token in tokens)
        if score > 0:
            scored.append((score, doc))
    if not scored:
        scored = [(1, doc) for doc in _read_markdown_files()]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "title": doc["title"],
            "snippet": doc["content"][:500],
            "score": float(score),
            "source": doc["source"],
            "category": doc["category"],
            "tags": doc["tags"],
            "type": "public",
            "metadata": {"scope": "public", "tenant_id": "public"},
        }
        for score, doc in scored[:top_k]
    ]


def query_knowledge(query: str, top_k: int = 4, collection: str = None) -> list[dict]:
    """Query public SOP knowledge and return title/snippet/score/source records.

    Results are cached with a 5-min TTL to reduce redundant ChromaDB queries.
    Supports skill-specific collections via the ``collection`` parameter.
    """

    if collection is None:
        collection = _COLLECTION_NAME

    cache_key = f"rag:{collection}:{hashlib.md5(f'{query}|{top_k}'.encode()).hexdigest()}"
    cached = redis_client.get_json(cache_key)
    if cached is not None:
        return cached

    settings = get_settings()
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_dir)
        coll = client.get_or_create_collection(
            collection, embedding_function=_get_ef()
        )
        if coll.count() == 0:
            if collection in ("aurasaas_knowledge", _COLLECTION_NAME):
                ingest_documents()
            else:
                # Skill collection is empty — fall back to keyword search
                results = _keyword_query(query, top_k)
                redis_client.set_json(cache_key, results, ttl=300)
                return results
        result = coll.query(query_texts=[query], n_results=top_k)
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        if docs:
            results = [
                {
                    "title": meta.get("title", "Untitled"),
                    "snippet": doc[:500],
                    "score": float(1 / (1 + distance)) if distance is not None else 0.0,
                    "source": meta.get("source", ""),
                    "category": meta.get("category", ""),
                    "tags": meta.get("tags", ""),
                    "type": meta.get("scope", "public"),
                    "metadata": meta,
                }
                for doc, meta, distance in zip(docs, metas, distances)
            ]
            redis_client.set_json(cache_key, results, ttl=300)
            return results
    except Exception:
        pass
    results = _keyword_query(query, top_k)
    redis_client.set_json(cache_key, results, ttl=300)
    return results