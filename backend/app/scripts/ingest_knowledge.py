"""Ingest Markdown SOP knowledge into the local AuraSaaS RAG store.

Supports:
    python -m app.scripts.ingest_knowledge
"""

from app.services.rag_service import ingest_documents


if __name__ == "__main__":
    result = ingest_documents()
    print(result)
