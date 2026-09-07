# Progress Log — Overview

A running build log for this project (see `../PROJECT_PLAN.md` for the 4-day plan and its reasoning). One file per topic/change — not per calendar day — so an entry stays self-contained regardless of when the work happened.

Each entry covers: what changed, why, and any decisions/trade-offs made along the way. This captures *process* — refactors, bugs found and fixed, design decisions and alternatives considered — not just a final feature list.

## Open blockers

None currently. Both API keys are in place as of `first-live-run-and-baseline-results.md` — the pipeline and eval harness have run against real Pinecone/Anthropic for the first time.

## Where things stand

Day 1 (full pipeline) and Day 2 milestones 1–3 (eval Q&A set, retrieval metrics, LLM-judge answer-quality eval) are now verified end-to-end, not just code-complete — see `first-live-run-and-baseline-results.md` for the real baseline numbers (recall@5 = 1.0, MRR = 0.863, faithfulness/relevance/scope accuracy all 1.0, spot-checked by hand rather than trusted blindly).

**Next up (milestone 4):** upgrade `chunk_documents()` to a real tokenizer (fastembed's own, per the earlier design decision) instead of word-count chunking, then tune chunk size/overlap against the `baseline` results and re-run both eval scripts under a new `--label` to produce the before/after comparison the README needs.

## Entries

- [`repo-foundation-and-housekeeping.md`](repo-foundation-and-housekeeping.md) — git init, dependency management, env/config setup
- [`fix-chunking-bug-and-batch-embeddings.md`](fix-chunking-bug-and-batch-embeddings.md) — fixed the chunking arg-order bug, refactored embeddings to batch
- [`add-pinecone-vector-store.md`](add-pinecone-vector-store.md) — VectorStore interface + Pinecone implementation
- [`add-retrieval-and-generation.md`](add-retrieval-and-generation.md) — retrieval + generation stages, composition-root pattern
- [`wire-cli-and-fix-config-consistency.md`](wire-cli-and-fix-config-consistency.md) — main.py CLI, fixed a config-boundary inconsistency in PineconeStore
- [`add-page-provenance-to-chunks.md`](add-page-provenance-to-chunks.md) — Chunk/RetrievedChunk gained page_start/page_end, needed for page-level eval ground truth
- [`add-retrieval-metrics-eval.md`](add-retrieval-metrics-eval.md) — recall@k/MRR scoring against the eval set, composition-root runner
- [`add-answer-quality-eval.md`](add-answer-quality-eval.md) — LLM-as-judge faithfulness/relevance/scope-handling eval, binary pass/fail scoring
- [`first-live-run-and-baseline-results.md`](first-live-run-and-baseline-results.md) — first real run against live Pinecone/Anthropic; baseline recall@k/MRR and answer-quality numbers, spot-checked
