# Week 2 evaluation report

The 15 cases comprise seven direct questions, four cross-document questions, two ambiguous questions, and two out-of-scope questions. Expected handbook sections and manual answer checks are in [eval_cases.json](eval_cases.json).

## Measured retrieval

The five-page snapshot contains 119 chunks. These scores come from the 11 answerable questions against the local BM25 baseline. The other four cases have routing expectations and are excluded from retrieval metrics.

| Local variant | Mean section recall@5 | MRR@5 | All required sections in top 5 |
|---|---:|---:|---:|
| BM25 | 77.27% | 72.73% | 8 / 11 |
| BM25 + section-overlap reranking | 68.18% | 71.21% | 6 / 11 |

Recall measures how many expected sections appear in the first five chunks per question, averaged across questions. MRR measures the reciprocal rank of the first expected section. The all-sections metric penalizes a cross-document result that only finds half the evidence.

## Failure analysis

- **D03, death in the family.** The request used everyday language while the target section was labeled “Bereavement.” BM25 retrieved family-leave and general absence sections. This is a case for testing semantic retrieval.
- **D04, jury duty documentation.** The baseline found the request process and jury duty pay. The separate documentation section fell outside the top five. Shared terms across adjacent sections crowded out the target.
- **X02, short versus extended sickness.** Extended sick leave appeared at rank two. The short-absence instructions were absent from the top five, which included several neighboring sick-leave sections.
- The section-overlap reranker reduced full evidence coverage. It remains an experimental variant. The default leaves the original rank intact.

## Verification status

The mobile browser reached the FastAPI endpoint, searched the real snapshot, and displayed a link to the relevant Workday PTO section. A local PostgreSQL/pgvector fixture verified lexical, dense, and hybrid SQL, transactional refresh rollback, and denied anonymous access.

## Live Supabase and OpenAI evaluation

The 119 handbook chunks were indexed with OpenAI text-embedding-3-small. The app answered questions with gpt-4.1-mini. The evaluation ran locally against the live Supabase and OpenAI APIs.

| Supabase retrieval | Mean section recall@5 | MRR@5 | All required sections in top 5 |
|---|---:|---:|---:|
| Full-text | 59.09% | 38.18% | 6 / 11 |
| Full-text with reranking | 63.64% | 49.24% | 6 / 11 |
| Dense | 90.91% | 84.85% | 9 / 11 |
| Hybrid | 90.91% | 59.70% | 9 / 11 |
| Hybrid with reranking | 90.91% | 73.03% | 9 / 11 |

With the app's default hybrid retrieval, 14 of 15 questions followed the expected route and mean citation coverage was 90.91%. Mean elapsed time was 2.09 seconds, with a maximum of 2.94 seconds. These times cover retrieval and generation from the local runner. Vercel response time and manual claim faithfulness remain unmeasured.

The default hybrid search missed one expected section each for the short-versus-extended sickness question and the question combining time-off terminology with parental leave. The sole routing error was the personal Workday balance question. The model asked for clarification where the expected behavior was to explain that the handbook cannot provide an individual's balance.
