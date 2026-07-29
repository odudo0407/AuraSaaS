"""RAG retrieval evaluation script.

Usage:
    cd backend
    python -m app.tests.eval_rag

Measures Recall@K, Precision@K, and MRR for the SOP knowledge base.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from backend/ directory
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.services.rag_service import query_knowledge, ingest_documents


def load_questions() -> list[dict]:
    path = Path(__file__).resolve().parent / "eval_questions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(k_values: tuple[int, ...] = (1, 3, 5)) -> dict:
    """Run retrieval eval and return metrics dict."""
    questions = load_questions()
    k_max = max(k_values)

    # Per-question results
    hits_at_k = {k: [] for k in k_values}
    reciprocal_ranks = []
    total_relevant = 0

    for item in questions:
        query = item["question"]
        expected_source = item["source"]
        results = query_knowledge(query, top_k=k_max)

        retrieved_sources = [r.get("source", "") for r in results]

        # Find rank of first correct hit (1-indexed)
        rank = None
        for idx, src in enumerate(retrieved_sources, start=1):
            if expected_source in src:
                rank = idx
                break

        if rank is not None:
            total_relevant += 1
            reciprocal_ranks.append(1.0 / rank)
            for k in k_values:
                hits_at_k[k].append(1 if rank <= k else 0)
        else:
            reciprocal_ranks.append(0.0)
            for k in k_values:
                hits_at_k[k].append(0)

    n = len(questions)
    metrics = {
        "total_questions": n,
        "total_retrieved": total_relevant,
        "mrr": round(sum(reciprocal_ranks) / n, 4) if n else 0,
    }
    for k in k_values:
        metrics[f"recall@{k}"] = round(sum(hits_at_k[k]) / n, 4)
        metrics[f"precision@{k}"] = round(sum(hits_at_k[k]) / (n * k), 4)

    return metrics


def print_report(metrics: dict) -> None:
    print("=" * 50)
    print("RAG Retrieval Evaluation Report")
    print("=" * 50)
    print(f"Questions:          {metrics['total_questions']}")
    print(f"Found in top-K:     {metrics['total_retrieved']}")
    print(f"MRR:                {metrics['mrr']:.2%}")
    print("-" * 50)
    for key in sorted(metrics):
        if key.startswith("recall@"):
            print(f"  {key:<18} {metrics[key]:.2%}")
    print("-" * 50)
    for key in sorted(metrics):
        if key.startswith("precision@"):
            print(f"  {key:<18} {metrics[key]:.2%}")
    print("=" * 50)


def main() -> None:
    print("Ingesting documents into ChromaDB...")
    result = ingest_documents()
    print(f"  backend: {result.get('backend')}, docs: {result.get('documents')}, chunks: {result.get('chunks')}")

    metrics = evaluate(k_values=(1, 3, 5))
    print_report(metrics)

    # Sanity check: spot-print one query result
    print("\n[spot check] 雨天外卖退单率:")
    for r in query_knowledge("雨天外卖退单率超过多少算异常", top_k=3):
        print(f"  [{r['score']:.4f}] {r['source']} — {r['title']}")


if __name__ == "__main__":
    main()
