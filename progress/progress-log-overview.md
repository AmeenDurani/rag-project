# Progress Log — Overview

A running build log for this project (see `../PROJECT_PLAN.md` for the 4-day plan and its reasoning). One file per topic/change — not per calendar day — so an entry stays self-contained regardless of when the work happened.

Each entry covers: what changed, why, and any decisions/trade-offs made along the way. This captures *process* — refactors, bugs found and fixed, design decisions and alternatives considered — not just a final feature list.

## Open blockers (action needed from the project owner)

- [ ] **Get a Pinecone API key** (free tier is fine) — needed for `PINECONE_API_KEY` in `.env`.
- [ ] **Get an Anthropic API key** — needed for `ANTHROPIC_API_KEY` in `.env`.

Without both, nothing past Day 1's code can be verified end-to-end — see `wire-cli-and-fix-config-consistency.md` for what's blocked on this. This now also blocks Day 2's eval harness: `python -m eval.run_retrieval_eval` and `python -m eval.run_answer_eval` are both code-complete but have never actually been run, so there is no real `baseline` results file yet.

## Where things stand (stopping point, end of this session)

Day 2 milestones 1–3 (eval Q&A set, retrieval metrics, LLM-judge answer-quality eval) are code-complete per `add-page-provenance-to-chunks.md`, `add-retrieval-metrics-eval.md`, and `add-answer-quality-eval.md` below. All verified only offline (synthetic data, no live API calls) — nothing has touched real Pinecone/Anthropic yet.

**Next up (milestone 4):** upgrade `chunk_documents()` to a real tokenizer (fastembed's own, per the earlier design decision) instead of word-count chunking, then tune chunk size/overlap using a real `baseline` eval run and re-run to produce the before/after comparison the README needs. This can't produce a *meaningful* before/after until the API-key blocker above is resolved and a real baseline run exists — there's a live open question (not yet decided) of whether to unblock the API keys now versus continuing to build milestone 4's code unverified, same as everything so far.

## Entries

- [`repo-foundation-and-housekeeping.md`](repo-foundation-and-housekeeping.md) — git init, dependency management, env/config setup
- [`fix-chunking-bug-and-batch-embeddings.md`](fix-chunking-bug-and-batch-embeddings.md) — fixed the chunking arg-order bug, refactored embeddings to batch
- [`add-pinecone-vector-store.md`](add-pinecone-vector-store.md) — VectorStore interface + Pinecone implementation
- [`add-retrieval-and-generation.md`](add-retrieval-and-generation.md) — retrieval + generation stages, composition-root pattern
- [`wire-cli-and-fix-config-consistency.md`](wire-cli-and-fix-config-consistency.md) — main.py CLI, fixed a config-boundary inconsistency in PineconeStore
- [`add-page-provenance-to-chunks.md`](add-page-provenance-to-chunks.md) — Chunk/RetrievedChunk gained page_start/page_end, needed for page-level eval ground truth
- [`add-retrieval-metrics-eval.md`](add-retrieval-metrics-eval.md) — recall@k/MRR scoring against the eval set, composition-root runner
- [`add-answer-quality-eval.md`](add-answer-quality-eval.md) — LLM-as-judge faithfulness/relevance/scope-handling eval, binary pass/fail scoring
