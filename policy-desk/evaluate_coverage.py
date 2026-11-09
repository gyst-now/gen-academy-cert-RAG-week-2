"""Compare retrieval variants on the original and fresh question sets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from corpus import ROOT
from evaluate import evaluate
from rag import RETRIEVAL_VARIANTS, TOP_K
from rag import retrieve_variant


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variants", nargs="+", choices=RETRIEVAL_VARIANTS, default=RETRIEVAL_VARIANTS)
    parser.add_argument("--fresh-cases", type=Path)
    args = parser.parse_args()
    if os.getenv("POLICY_STORE") != "supabase" or not os.getenv("CHAT_MODEL"):
        parser.error("The comparison requires Supabase and a configured chat model.")
    suites = {
        "original": ROOT / "eval_cases.json",
        "holdout": ROOT / "eval_coverage_holdout.json",
    }
    if args.fresh_cases:
        suites["fresh"] = args.fresh_cases
    results = {}
    with ThreadPoolExecutor(max_workers=len(args.variants)) as pool:
        for suite, filename in suites.items():
            cases = json.loads(filename.read_text(encoding="utf-8"))
            jobs = {
                variant: pool.submit(
                    evaluate, cases, variant, False, True,
                    search=partial(retrieve_variant, variant=variant),
                )
                for variant in args.variants
            }
            results[suite] = {variant: job.result() for variant, job in jobs.items()}
            for variant, result in results[suite].items():
                print(suite, variant, {key: value for key, value in result.items() if key != "cases"}, flush=True)
    args.output.write_text(json.dumps({"k": TOP_K, "suites": results}, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
