# Evidence experiment

All runs used the same 119 handbook chunks, answer model, and five-passage limit. Main uses hybrid search. The coverage baseline uses dense search with question splitting and heading diversity. The gap branch adds an evidence check and targeted retry for compound questions. The scoring branch leaves retrieval and generation unchanged and evaluates the coverage baseline at the chunk level.

## Retrieval and routing

| Question set | Runtime | Heading recall@5 | Complete headings | Correct route | Mean local time |
|---|---|---:|---:|---:|---:|
| Original | Main | 90.9% | 9/11 | 15/15 | 2.31 s |
| Original | Coverage baseline | 90.9% | 9/11 | 15/15 | 2.63 s |
| Original | Gap filling | 90.9% | 9/11 | 15/15 | 2.90 s |
| Holdout | Main | 42.9% | 2/7 | 8/10 | 2.05 s |
| Holdout | Coverage baseline | 85.7% | 6/7 | 10/10 | 3.05 s |
| Holdout | Gap filling | 92.9% | 6/7 | 10/10 | 3.54 s |
| Fresh | Main | 50.0% | 1/4 | 4/4 | 2.56 s |
| Fresh | Coverage baseline | 100.0% | 4/4 | 4/4 | 3.80 s |
| Fresh | Gap filling | 100.0% | 4/4 | 4/4 | 4.00 s |

## Chunk-level scores

An evidence group represents one required fact or procedure and can accept multiple equivalent chunk IDs. Complete evidence requires one hit in each group. For each run below, expected citation coverage equaled chunk recall. These scores measure evidence selection and citation. They do not measure whether every generated claim follows from the cited text.

| Question set | Runtime | Chunk recall@5 | Complete evidence |
|---|---|---:|---:|
| Holdout | Main | 42.9% | 2/7 |
| Holdout | Coverage baseline | 85.7% | 6/7 |
| Holdout | Gap filling | 85.7% | 5/7 |
| Fresh | Main | 50.0% | 1/4 |
| Fresh | Coverage baseline | 100.0% | 4/4 |
| Fresh | Gap filling | 100.0% | 4/4 |

## Findings and merge recommendation

- In the holdout run, gap filling found the illness-disclosure passage for H06 but still missed global parental-pay guidance. The coverage baseline answer incorrectly told employees they needed to share medical details. The gap answer correctly described employees’ discretion.
- In H07, the gap run found the reinstatement window but missed the separate chunk explaining the position the employee returns to. Heading scoring credited both variants. Chunk scoring detected the omission. The gap answer also invoked a legal rule outside the retrieved passages.
- When both variants reused identical split queries in a targeted H06 and H07 replay, they selected the same five passages for both questions. The evidence checker did not trigger a retry in either replay. The separate-run difference therefore does not establish a gain or loss caused by the retry.
- The four fresh cases are a small, manually labeled set. The benchmark grades retrieval, citations and routing, with targeted review of H06 and H07. Full claim accuracy and production latency were not measured.

Merge the chunk-scoring tools and labeled fixtures first. The branch includes the coverage experiment as its parent, and hybrid remains the default. Keep gap filling experimental. It added time without improving complete evidence on either labeled set. The split retriever is the leading candidate for a later runtime change after a larger claim-level review.

## Reproduce

On the gap branch, run `uv run python evaluate_coverage.py --output data/coverage-round2.json --variants hybrid dense_split dense_gap --fresh-cases PATH`. Use `eval_chunk_fresh.json` from the chunk-scoring branch as PATH. Score the saved run with `evaluate_chunks.py` on the scoring branch for the holdout and fresh suites. Supply the indexed snapshot via `--snapshot` if it is stored elsewhere.
