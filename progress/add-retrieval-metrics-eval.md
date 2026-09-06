# Add Retrieval Metrics Eval (recall@k, MRR)

Milestone #2 of the Day 2 plan: score retrieval quality against `eval/nasa_handbook_qa_set.json` using the page-level ground truth added in `add-page-provenance-to-chunks.md`.

## `eval/retrieval_metrics.py` — scoring logic, no I/O

- `chunk_hits_pages(chunk, relevant_pages)` — a chunk counts as a hit if its `[page_start, page_end]` range overlaps *any* labeled page (any-overlap, not full-containment — the design fork flagged before building this; overlap is simpler and matches how the ground truth itself was defined).
- `first_hit_rank(retrieved, relevant_pages)` — 1-indexed rank of the first hit in a ranked retrieval list, or `None` if nothing hit.
- `recall_at_k` / `mrr` — standard definitions over a list of per-question score records.
- `summarize(scored_questions, max_k)` — computes recall@{1, 3, max_k} and MRR from a *single* top-`max_k` retrieval per question, rather than re-querying per k: `first_hit_rank <= k` for a smaller k is equivalent to only having looked at the top k of the same ranked list, so one retrieval call covers every k up to `max_k`.

## `eval/run_retrieval_eval.py` — the runner (composition root for this eval)

- Invoke as `python -m eval.run_retrieval_eval` (not `python eval/run_retrieval_eval.py`) — needs to run from the repo root so both `src.*` and `eval.*` imports resolve; direct script execution would only put `eval/` on `sys.path`, breaking the `src` imports. Added `eval/__init__.py` to make this a proper package.
- Follows the same composition-root/lazy-import pattern as `main.py`: `settings` and `PineconeStore` are only imported inside the command function, so `--help` works with zero configuration (verified).
- **Only scores `expected_answerable: true` questions.** Out-of-scope questions have no `relevant_pages` to hit against — including them here would score every one as a permanent miss for a reason that has nothing to do with retrieval quality. They're deferred to milestone #3 (LLM-judge), where "correctly said I don't know" is the actual thing worth measuring, not recall.
- `--label` (default `baseline`) controls the output filename under `eval/results/<label>.json` — deliberately so milestone #4 (chunking upgrade) can re-run this under a different label (e.g. `token_aware_chunking`) and diff the two result files directly, without the first run being clobbered.
- Output includes both the aggregate summary and full per-question detail (retrieved chunks, ranks) so a failing question can be inspected directly instead of re-run with debugging added after the fact.

## Verified

- Compiles; `--help` succeeds with no `.env`.
- Metrics logic checked offline against synthetic `RetrievedChunk` lists (hit-at-rank-2, no-hit, hit-at-rank-1 cases), asserting exact `recall@1`, `recall@3`, and `mrr` values by hand computation.
- **Not yet run against live Pinecone** — same open blocker as everything since Day 1 (no `.env` / API keys).

## Still open

- `eval/results/` doesn't exist until the first real run creates it (`.gitignore` doesn't need an entry — it's created on demand, and results files are meant to be committed once real, to preserve the before/after comparison).
