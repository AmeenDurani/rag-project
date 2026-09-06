# Progress Log — Overview

A running build log for this project (see `../PROJECT_PLAN.md` for the 4-day plan and its reasoning). One file per topic/change — not per calendar day — so an entry stays self-contained regardless of when the work happened.

Each entry covers: what changed, why, and any decisions/trade-offs made along the way. This captures *process* — refactors, bugs found and fixed, design decisions and alternatives considered — not just a final feature list.

## Open blockers (action needed from the project owner)

- [ ] **Get a Pinecone API key** (free tier is fine) — needed for `PINECONE_API_KEY` in `.env`.
- [ ] **Get an Anthropic API key** — needed for `ANTHROPIC_API_KEY` in `.env`.

Without both, nothing past Day 1's code can be verified end-to-end — see `wire-cli-and-fix-config-consistency.md` for what's blocked on this.

## Entries

- [`repo-foundation-and-housekeeping.md`](repo-foundation-and-housekeeping.md) — git init, dependency management, env/config setup
- [`fix-chunking-bug-and-batch-embeddings.md`](fix-chunking-bug-and-batch-embeddings.md) — fixed the chunking arg-order bug, refactored embeddings to batch
- [`add-pinecone-vector-store.md`](add-pinecone-vector-store.md) — VectorStore interface + Pinecone implementation
- [`add-retrieval-and-generation.md`](add-retrieval-and-generation.md) — retrieval + generation stages, composition-root pattern
- [`wire-cli-and-fix-config-consistency.md`](wire-cli-and-fix-config-consistency.md) — main.py CLI, fixed a config-boundary inconsistency in PineconeStore
- [`add-page-provenance-to-chunks.md`](add-page-provenance-to-chunks.md) — Chunk/RetrievedChunk gained page_start/page_end, needed for page-level eval ground truth
- [`add-retrieval-metrics-eval.md`](add-retrieval-metrics-eval.md) — recall@k/MRR scoring against the eval set, composition-root runner
- [`add-answer-quality-eval.md`](add-answer-quality-eval.md) — LLM-as-judge faithfulness/relevance/scope-handling eval, binary pass/fail scoring
