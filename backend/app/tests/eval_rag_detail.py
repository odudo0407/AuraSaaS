"""Per-question diagnostic: show rank of correct answer for each query."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.services.rag_service import query_knowledge, ingest_documents


def main() -> None:
    ingest_documents()

    path = Path(__file__).resolve().parent / "eval_questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))

    print(f"{'#':<3} {'Rank':<6} {'Query':<40} {'Expected':<35} {'Top-1 Title'}")
    print("-" * 130)

    ranks = []
    for i, item in enumerate(questions, 1):
        results = query_knowledge(item["question"], top_k=5)
        rank = None
        for idx, r in enumerate(results, start=1):
            if item["source"] in r.get("source", ""):
                rank = idx
                break

        ranks.append(rank)
        status = f"#{rank}" if rank else "MISS"
        top1 = f"{results[0]['title'][:30]}" if results else "N/A"
        print(f"{i:<3} {status:<6} {item['question'][:38]:<40} {item['source'][:33]:<35} {top1}")

    found = sum(1 for r in ranks if r is not None)
    mrr = sum(1 / r for r in ranks if r is not None) / len(questions)
    print(f"\nFound: {found}/{len(questions)} | MRR: {mrr:.2%}")


if __name__ == "__main__":
    main()
