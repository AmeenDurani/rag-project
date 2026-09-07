# Experiment: Smaller Chunk Size on the Small Corpus

Diagnostic experiment, not milestone 4 itself. Milestone 4 (token-aware chunking with a real tokenizer) is still open - this tests a narrower question first: is chunk *size* even a lever worth pulling on a corpus this small, before investing in the tokenizer swap?

## Why this experiment happened

The `baseline` results (`first-live-run-and-baseline-results.md`) came back with recall@5 = 1.0 and 100% answer-quality scores. Discussed whether that was a real signal or a ceiling effect, and worked out the actual cause: ingest produced only **16 chunks total** from the ~8000-word corpus (`chunk_size=500`). With `top_k=5`, every query retrieves 5 of 16 chunks - **31% of the entire corpus per query**. Recall@5 = 1.0 mostly reflects that denominator, not chunking quality; there's barely room for any retrieval setup to miss. recall@1 (0.778) was the only metric with real spread, because it's the only one strict enough to still discriminate at this scale.

Two independent levers were identified to fix this: (1) grow the corpus, already on the post-4-day refinement list, or (2) shrink chunk size to increase the total chunk count even on the current corpus, which reduces top_k's share of the corpus without adding source material. Decided to try (2) first, cheaply, before deciding whether (1) is actually necessary.

## Setup

Added `--chunk-size`/`--overlap` options to `main.py ingest` (previously hardcoded to the function defaults) - a small, clearly-motivated addition since milestone 4's "tune chunk size/overlap" step needs this tunability regardless of this experiment.

Ran a second ingest into an **isolated Pinecone namespace** (`small_chunks`, vs. the verified `default`/`baseline` namespace) with `chunk_size=150, overlap=15` - same 10% overlap ratio as the baseline's `500/50`, so chunk size is the only variable that changed. Namespaces are fully isolated in Pinecone, so this could not contaminate or require re-verifying the existing `baseline` results.

Result: 54 chunks (vs. 16 at `chunk_size=500`), roughly matching the ~8000/150 ≈ 53 prediction made before running it.

## Results

| Metric | baseline (500/50, 16 chunks) | small_chunks (150/15, 54 chunks) |
|---|---|---|
| recall@1 | 0.778 | 0.778 |
| recall@3 | 0.944 | 0.944 |
| recall@5 | **1.0** | **0.944** |
| MRR | 0.863 | 0.861 |
| faithfulness_rate | 1.0 | 1.0 |
| relevance_rate | 1.0 | 1.0 |
| scope_accuracy | 1.0 | **0.955** |
| scope_accuracy_answerable | 1.0 | **0.944** |
| scope_accuracy_out_of_scope | 1.0 | 1.0 |

**Smaller chunks did not improve retrieval - they slightly regressed it.** This confirms the ceiling-effect diagnosis was right (recall@5 is no longer trivially 1.0, so the eval can discriminate now), but the direction of the change is a regression, not the hoped-for improvement. Not a wasted experiment: a flat or negative result here is still the answer to the question "is chunk size alone the lever," which was the actual question being tested.

## Two specific failures, diagnosed individually rather than left as aggregate numbers

**q12** ("What is AS9100, and why is it referenced in this handbook?", page 17) - hit at rank 1 in `baseline`, **missed entirely in top 5** with smaller chunks (page 17 doesn't appear anywhere in the top 5 retrieved). The AS9100 explanation is a short passage; at `chunk_size=150` it likely got split away from the surrounding context that made the larger 500-word chunk's embedding a strong match for this query. Smaller isn't strictly more precise - it can also dilute a short passage's signal.

**q08** ("What are the four System Design Processes?", pages 15-16) - retrieval metrics say **hit at rank 1** (a chunk spanning pages 14-15 was retrieved), but the answer-quality eval caught something recall@k couldn't: the model refused to answer, because the four-item list got fragmented across multiple small chunks and no single retrieved chunk contained the complete list. This is exactly why both evals matter together - page-overlap recall confirms the *right page* was retrieved, not that a *complete, coherent* answer was retrievable from what came back. A page-level hit is necessary but not sufficient.

## Interpretation and what's still open

Chunk size alone, on a 16→54 chunk range, is a genuine trade-off (helps some questions' ranking, hurts others), not a clean win - going smaller isn't automatically "more precise." Two live questions for next session, not yet decided:

1. Does token-aware chunking (the actual milestone 4 change - a real tokenizer instead of word-count, which this experiment didn't test) behave differently than a naive size reduction did here?
2. Is corpus expansion (lever 1, still not tried) actually necessary to get a chunking comparison with room to show a real improvement, or is a smarter chunking *strategy* (e.g. one that avoids splitting a numbered list across a chunk boundary, which is what broke q08) a better lever than corpus size?

Not resolved yet - picking this up next session, per the plan to stop here for now.

## Verified / artifacts

- `eval/results/small_chunks.json`, `eval/results/small_chunks_answers.json` - full per-question results, committed alongside `baseline.json`/`baseline_answers.json` for direct comparison.
- `main.py`'s `ingest` command now accepts `--chunk-size`/`--overlap` (defaults unchanged: 500/50).
- `default` namespace (the verified `baseline`) was never touched - this experiment lives entirely in the `small_chunks` namespace.
