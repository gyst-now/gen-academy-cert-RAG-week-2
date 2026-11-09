# Policy Desk

Set `POLICY_RETRIEVAL_VARIANT=dense_gap` to test evidence recovery. When a question is split into two searches, the chat model checks each part against the five selected passages. If evidence is missing, a targeted hybrid search expands the candidate pool and a second check selects supporting passages. The final limit remains five.

With Supabase and chat configured, compare this experiment with the previous retrievers using `uv run python evaluate_coverage.py --output data/coverage-experiment.json --variants hybrid dense_split dense_gap`. Add `--fresh-cases PATH` with the fresh question file from the `evaluate-chunks` branch to include that set.

A browser chat that helps GitLab team members find answers about time off and leave in five public GitLab Handbook pages. The evaluation targets are 90% claim faithfulness and a 10-second warm response time. These are project goals; see the evaluation report for what has been measured.

## Run locally

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run these commands from this folder.

```powershell
uv sync --locked
uv run python corpus.py
uv run uvicorn app:app --port 8765
```

Open [the local browser chat](http://127.0.0.1:8765). With no credentials, it runs in evidence search mode and shows retrieved sections with links. Copy `.env.example` to `.env` and fill the chat settings to enable generated answers against the local snapshot. Restart the server after changing settings.

## Configure Supabase

1. In a dedicated Supabase project with the Data API enabled, run [supabase/schema.sql](supabase/schema.sql) in SQL Editor. The two RPCs and the table are restricted to the service role.
2. In `.env`, set `POLICY_STORE=supabase`, the project URL in `SUPABASE_URL`, and a server secret key or legacy service-role key in `SUPABASE_SERVICE_ROLE_KEY`.
3. Configure `EMBED_BASE_URL`, `EMBED_API_KEY`, and `EMBED_MODEL`. Configure the corresponding `CHAT_*` variables for answer generation. For Nebius Token Factory use `https://api.tokenfactory.nebius.com/v1` and model IDs enabled for your account. The two endpoints and credentials can be set independently. [Nebius API](https://api.tokenfactory.nebius.com/docs)
4. Run `uv run python corpus.py --snapshot --upload` after the local snapshot exists. Use `uv run python corpus.py --upload` for a fresh download and upload. If you switch embedding providers or models, re-embed before switching the running app to the new setting.
5. Restart locally and submit an example question. Then run the 15-question evaluation with `uv run python evaluate.py --generate`.

## Deploy to Vercel

Use the FastAPI framework preset, with this folder as the project root and Python 3.12. Add the Supabase and model variables to the intended Vercel environment. Set `POLICY_STORE=supabase` and generate a strong `DEMO_ACCESS_CODE` for the demo audience. The hosted API requires the code before invoking the model. Keep all keys in server environment variables.

Deploy a preview through the Vercel dashboard or by running `vercel deploy` from a linked project. Open the preview, enter the demo access code, ask an example question, and check that its source opens the right handbook section. Promote the tested preview if a production URL is needed. [Vercel FastAPI guide](https://vercel.com/docs/frameworks/backend/fastapi)

## Corpus and retrieval

- **Corpus.** Five public GitLab Handbook articles in English, including the company-wide and U.S. leave guidance. The source manifest records the canonical URLs. [GitLab Handbook](https://handbook.gitlab.com/handbook/people-group/time-off-and-absence/)
- **Ingestion and cleaning.** Download rendered HTML, start at the article heading, and extract paragraphs, lists, and tables with their heading hierarchy. Keep each section’s title, URL anchor, scope and fetch timestamp.
- **Freshness.** This demo uses an explicit snapshot. Refresh before recording or whenever evaluating an updated policy set. Supabase replaces the snapshot atomically after all embeddings are available.
- **Chunking and embedding.** LangChain recursively splits long sections at 1,800 characters with 200 characters of overlap. The provider-specific embedding model is configurable and the model identity travels with the snapshot.
- **Retrieval.** Local BM25 is a baseline. Supabase combines exact pgvector cosine retrieval and English full-text search using reciprocal rank fusion, then sends the top five passages to generation. The optional section-overlap reranker is disabled by default based on the baseline results. [Supabase hybrid search](https://supabase.com/docs/guides/ai/hybrid-search)
- **Answers.** A LangGraph flow retrieves evidence, then requests an answer, clarification or abstention. The server maps validated citation numbers to retrieved passages. The browser carries the preceding question into a clarification follow-up.

## Evaluation and demo

Run `uv run python evaluate.py` to measure retrieval. With a configured chat model, add `--generate` to score routing and citation coverage for the app's active variant. Review the factual claims against the cited excerpts for faithfulness. The detailed JSON goes to `data/evaluation.json`; the [evaluation report](EVALUATION.md) records the baseline and what remains to be measured.

For the class recording, show a direct Workday PTO question, one question combining parental leave and PTO, an ambiguous two-week absence, and an expense question outside the corpus. Open a cited section and briefly show the evaluation results and a retrieval miss. Record after the live model evaluation is available.

Handbook content is attributed to GitLab. [GitLab’s handbook licensing explanation](https://about.gitlab.com/blog/our-handbook-is-open-source-heres-why/)
