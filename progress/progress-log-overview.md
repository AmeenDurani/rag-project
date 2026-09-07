# Progress Log — Overview

A running build log for this project (see `../PROJECT_PLAN.md` for the 4-day plan and its reasoning). One file per topic/change — not per calendar day — so an entry stays self-contained regardless of when the work happened.

Each entry covers: what changed, why, and any decisions/trade-offs made along the way. This captures *process* — refactors, bugs found and fixed, design decisions and alternatives considered — not just a final feature list.

## Open blockers

None currently. Both API keys are in place as of `first-live-run-and-baseline-results.md` — the pipeline and eval harness have run against real Pinecone/Anthropic for the first time.

## Where things stand

Day 1 (full pipeline) and all of Day 2's core milestones are now complete and verified end-to-end, not just code-complete.

`first-live-run-and-baseline-results.md` has the original baseline numbers (recall@5 = 1.0, MRR = 0.863, faithfulness/relevance/scope accuracy all 1.0). That perfect baseline turned out to be a ceiling effect, not a real signal: only 16 total chunks existed, so `top_k=5` retrieved 31% of the entire corpus every query. `experiment-smaller-chunk-size.md` tested shrinking chunk size alone (still word-based) and found a slight regression with two individually-diagnosed failures, one of them a list fragmented across a chunk boundary.

`token-aware-chunking-and-truncation-fix.md` closes out milestone 4. Before tuning chunk size, checked whether word-count chunking was even measuring the right thing - it wasn't: chunks averaged ~700 real tokens against the embedding model's hard 512-token limit, so every chunk was silently truncated at embedding time (retrieval never saw roughly the last third of each chunk's text). Considered and rejected page-level chunking (55% of pages exceed 512 tokens on their own, so it isn't viable standalone on this corpus). Implemented token-based chunking instead (400 tokens/40 overlap, offset-sliced text, tokenizer reused from the embedding model itself) and promoted it to the `default` namespace. Eval numbers moved flat-to-slightly-down on this corpus (same ceiling-effect-unmasking pattern as the chunk-size experiment, not a quality drop), but a sharper finding emerged: three answerable questions now fail scope accuracy, and all three ground-truth to the same two pages (15-16), where a process-category list/diagram gets split across a chunk boundary every chunking scheme tried so far has cut through in roughly the same place. That's stronger evidence for "chunking *strategy* is the real lever" than corpus size, though neither has been tried yet.

**Decision made:** accept token-aware chunking as-is (it fixes a real correctness bug regardless of eval-number movement) and move on to Day 3 rather than chase the list-fragmentation issue now. That issue, and the corpus-expansion alternative, are documented for whenever chunking strategy gets revisited (see "Making this project better" in `PROJECT_PLAN.md`).

**Next up: Day 3** - FastAPI service layer, logging/tracing, unit tests. Nothing started yet.

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
- [`experiment-smaller-chunk-size.md`](experiment-smaller-chunk-size.md) — diagnosed the baseline's ceiling effect (16 total chunks); tested a smaller chunk size in an isolated namespace, found a regression with two specific diagnosed failures
- [`token-aware-chunking-and-truncation-fix.md`](token-aware-chunking-and-truncation-fix.md) — found and fixed a silent embedding-truncation bug (word-based chunks were ~35% over the model's 512-token limit); rejected page-level chunking after checking real per-page token counts; implemented and promoted token-aware chunking, closing out milestone 4
