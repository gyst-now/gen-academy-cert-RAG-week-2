"""Measure section retrieval and, when configured, answer routing and citation coverage."""
import argparse
import json
import os
from pathlib import Path
from statistics import mean
from time import perf_counter

from dotenv import load_dotenv

from corpus import ROOT
from rag import TOP_K, retrieve, respond


def matches(doc, target):
    source, heading = target
    return doc.metadata["source"] == source and heading.casefold() in doc.metadata["section"].casefold()


def evaluate(cases, mode, rerank, generate, *, search=None):
    results = []
    for case in cases:
        start = perf_counter()
        docs = search(case["question"]) if search is not None else retrieve(case["question"], mode, rerank)
        ranks = [
            next((rank for rank, doc in enumerate(docs, 1) if matches(doc, target)), None)
            for target in case.get("targets", [])
        ]
        relevant = [rank for rank in ranks if rank is not None]
        result = {
            **case, "target_ranks": ranks,
            "recall_at_k": len(relevant) / len(ranks) if ranks else None,
            "reciprocal_rank": (1 / min(relevant) if relevant else 0) if ranks else None,
            "retrieved": [
                {"source": doc.metadata["source"], "section": doc.metadata["section"],
                 "id": doc.id, "url": doc.metadata["url"]}
                for doc in docs
            ],
        }
        if generate:
            answer = respond({"documents": docs, "question": case["question"]})["response"]
            cited_ids = {item["id"] for item in answer["sources"]}
            result.update(
                response=answer,
                route_pass=answer["status"] == case["expected_status"],
                citation_coverage=(
                    sum(any(doc.id in cited_ids and matches(doc, target) for doc in docs)
                        for target in case["targets"]) / len(ranks)
                    if ranks else None
                ),
            )
        result["latency_ms"] = round((perf_counter() - start) * 1000, 1)
        results.append(result)

    answerable = [row for row in results if row["recall_at_k"] is not None]
    return {
        "mode": mode, "rerank": rerank,
        "recall_at_k": round(mean(row["recall_at_k"] for row in answerable), 4),
        "mrr_at_k": round(mean(row["reciprocal_rank"] for row in answerable), 4),
        "all_targets_at_k": round(mean(row["recall_at_k"] == 1 for row in answerable), 4),
        "route_accuracy": round(mean(row["route_pass"] for row in results), 4) if generate else None,
        "citation_coverage": (
            round(mean(row["citation_coverage"] for row in answerable), 4) if generate else None
        ),
        "cases": results,
    }


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "evaluation.json")
    args = parser.parse_args()
    if args.generate and not os.getenv("CHAT_MODEL"):
        parser.error("--generate requires CHAT_MODEL and CHAT_API_KEY")
    store = os.getenv("POLICY_STORE", "local")
    cases = json.loads((ROOT / "eval_cases.json").read_text(encoding="utf-8"))
    variants = [("lexical", False), ("lexical", True)]
    if store == "supabase":
        variants += [("dense", False), ("hybrid", False), ("hybrid", True)]
    active = ("hybrid" if store == "supabase" else "lexical", os.getenv("POLICY_RERANK") == "1")
    runs = [
        evaluate(cases, mode, rerank, args.generate and (mode, rerank) == active)
        for mode, rerank in variants
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"store": store, "k": TOP_K, "runs": runs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for run in runs:
        print({key: value for key, value in run.items() if key != "cases"})
    print(args.output)


if __name__ == "__main__":
    main()
