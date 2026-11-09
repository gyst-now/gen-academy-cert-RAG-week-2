"""Score evidence groups from ranked and cited chunk IDs in a saved coverage run."""
import argparse
import json
from pathlib import Path
from statistics import mean

from corpus import ROOT, SNAPSHOT


def score(cases, requirements, k):
    results = []
    for case in cases:
        groups = requirements.get(case["id"])
        if not groups:
            continue
        top_ids = {chunk["id"] for chunk in case["retrieved"][:k]}
        response = case.get("response")
        cited_ids = {chunk["id"] for chunk in response["sources"]} if response else set()
        missing = [name for name, accepted in groups.items() if top_ids.isdisjoint(accepted)]
        uncited = [name for name, accepted in groups.items() if cited_ids.isdisjoint(accepted)]
        results.append({
            "id": case["id"],
            "recall": 1 - len(missing) / len(groups),
            "complete": not missing,
            "citation_coverage": 1 - len(uncited) / len(groups) if response else None,
            "missing": missing,
            "uncited": uncited if response else None,
        })
    if not results:
        raise ValueError("No evidence requirements matched the evaluation cases.")
    citations = [case["citation_coverage"] for case in results if case["citation_coverage"] is not None]
    return {
        "recall": mean(case["recall"] for case in results),
        "complete": sum(case["complete"] for case in results),
        "questions": len(results),
        "citation_coverage": mean(citations) if citations else None,
        "cases": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--suite", choices=("holdout", "fresh"), default="holdout")
    args = parser.parse_args()
    requirements = json.loads((ROOT / "eval_chunk_requirements.json").read_text(encoding="utf-8"))
    snapshot_ids = {chunk["id"] for chunk in json.loads(args.snapshot.read_text(encoding="utf-8"))}
    for groups in requirements.values():
        for accepted in groups.values():
            if not accepted or not snapshot_ids.issuperset(accepted):
                parser.error("Evidence labels do not match the indexed snapshot. Review the labels before scoring.")
    evaluation = json.loads(args.evaluation.read_text(encoding="utf-8"))
    variants = evaluation["suites"][args.suite]
    prefix = "H" if args.suite == "holdout" else "F"
    requirements = {key: groups for key, groups in requirements.items() if key.startswith(prefix)}
    for variant, run in variants.items():
        if not set(requirements) <= {case["id"] for case in run["cases"]}:
            parser.error(f"{variant} is missing labeled questions.")
    scored = {variant: score(run["cases"], requirements, evaluation["k"]) for variant, run in variants.items()}
    args.output.write_text(json.dumps(scored, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
