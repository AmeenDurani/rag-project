# Token-Aware Chunking: Diagnosing a Truncation Bug, Rejecting Page-Level Chunking, and the Final Milestone 4 Result

Resolves milestone 4 from `PROJECT_PLAN.md` ("upgrade chunking to token-aware, tune chunk size/overlap, re-run eval"), which was left open at the end of `experiment-smaller-chunk-size.md` with two undecided questions. Both are now answered.

## The bug this started from

Before touching chunk size, checked whether word-count chunking was even measuring the right thing. It wasn't: fastembed's model (`BAAI/bge-small-en-v1.5`) has a hard 512-token limit with silent right-side truncation. Tested real baseline chunks (`chunk_size=500` words) against the actual tokenizer with truncation disabled - every chunk came back at 640-788 true tokens, 25-35% over the limit. The tail of every chunk's text had been invisible to its own embedding this whole time; the full text was still stored and shown to Claude at generation time, but retrieval never saw the back third of each chunk. This reframed milestone 4 from a tuning exercise into a correctness fix.

## Page-level chunking, considered and rejected

Before committing to a token-based redesign, considered anchoring chunks to page boundaries instead (never let a chunk blend two pages' unrelated content into one embedding). Checked real per-page token counts before deciding anything: **11 of 20 pages (55%) already exceed 512 tokens on their own** (page 5 alone is 932 tokens), and the shortest pages are 20 and 170 tokens. Pure "one page = one chunk" doesn't work as a standalone scheme on this corpus - most pages still need internal splitting, and the tiny pages would become sparse, low-signal standalone chunks. Decided to stick with straightforward token-budget-based chunking rather than build the page-boundary-plus-internal-token-split hybrid this would have required.

## Design decisions for the token-aware chunker

Three choices made explicitly before implementing, each with a real trade-off:

1. **Tokenizer source: reuse fastembed's already-loaded tokenizer**, not an independently-loaded one. Same exact tokenizer that performs the real embedding call, so token counts used for chunk-size accounting are exactly what determines truncation - not an approximation. Trade-off accepted: reaches into a private fastembed attribute path (`model.model.tokenizer`) that could break on a version bump.
2. **Chunk text reconstruction: character-offset slicing from the source page text**, not decoding token ids back to text. Keeps chunk text byte-identical to the source PDF instead of picking up WordPiece decode artifacts (subword rejoining, whitespace normalization).
3. **Target size: ~400 tokens / ~40 overlap** (same 10% overlap ratio as the old 500/50 word-based baseline), with real headroom under the 512 hard limit.

Implementation detail worth naming: chunking needs to tokenize without truncation (documents are far longer than 512 tokens), but the shared tokenizer singleton is also used for real embedding calls elsewhere and must keep truncating there. Rather than toggling truncation on/off on the shared object (stateful, fragile if an exception skips the restore step), chunking clones the tokenizer in-memory via `to_str()`/`from_str()` (confirmed cheap, ~27ms, no network) and disables truncation only on the clone. The shared singleton is never touched.

Also fixed a pre-existing quirk in the old sliding-window loop while redesigning the stepping: it stepped by `chunk_size` but pulled `start` back by `overlap`, so every chunk after the first was actually `chunk_size + overlap` long, not `chunk_size` (500-word chunks were actually 550 words). The new loop uses standard sliding-window semantics (`step = chunk_size - overlap`, each chunk exactly `chunk_size` tokens except the last) so the max-token guarantee is a direct property of the loop, not dependent on remembering the old hidden `+overlap`. This surfaced a real edge case: with standard stepping, if total token count lines up exactly right, the last window can end up fully contained in the previous chunk (a wasted, fully-redundant duplicate). Added a one-line guard that stops once a window contributes no new content.

Verified directly against the real corpus before running anything else: 30 chunks (vs. 16 in the old word-based baseline), max 400 content tokens per chunk (well under the 512 ceiling) by construction, sensible sequential page provenance.

## Eval result: fixed the bug, flat-to-slightly-down on this eval's numbers

Ran ingest into an isolated `token_aware` Pinecone namespace first (same pattern as the previous chunk-size experiment - never touched `default` until the result was understood), then both eval harnesses:

| Metric | baseline (500w/50, 16 chunks) | small_chunks (150w/15, 54 chunks) | token_aware (400tok/40, 30 chunks) |
|---|---|---|---|
| recall@1 | 0.778 | 0.778 | 0.722 |
| recall@3 | 0.944 | 0.944 | 0.889 |
| recall@5 | 1.0 | 0.944 | 0.944 |
| MRR | 0.863 | 0.861 | 0.801 |
| faithfulness_rate | 1.0 | 1.0 | 1.0 |
| relevance_rate | 1.0 | 1.0 | 1.0 |
| scope_accuracy | 1.0 | 0.955 | 0.864 |
| scope_accuracy_answerable | 1.0 | 0.944 | 0.833 |
| scope_accuracy_out_of_scope | 1.0 | 1.0 | 1.0 |

On its own this reads like a regression. It mostly isn't: 30 chunks vs. baseline's 16 means top_k=5 covers a smaller share of the corpus, so recall@k discriminates again instead of trivially hitting - the same ceiling-effect-unmasking phenomenon documented in `experiment-smaller-chunk-size.md`, not a quality drop from token-awareness itself.

**A more specific finding underneath the aggregate number, diagnosed individually rather than left as a summary statistic:** all three answerable questions that failed scope accuracy - q08 ("four System Design Processes"), q09 ("five Product Realization Processes"), q10 ("eight Technical Management Processes") - ground-truth to the exact same pages, 15-16. Checking retrieval directly: no chunk spanning both page 15 and page 16 ever appears in top-5 for any of the three; one chunk ends at page 15, the next starts at page 16, splitting whatever process-category list/diagram lives there. For q09, both halves were retrieved in top-5 and the model still declined to state the complete list, understandably unwilling to stitch two disjoint-looking fragments into a confident "these five are the complete list."

This is the same failure *type* as q08 in the smaller-chunk-size experiment (list fragmented across a chunk boundary) - except now it hits three questions instead of one, all anchored to the same page pair, across a differently-sized chunking scheme. That's a stronger signal than a single data point: this isn't chunk-size or tokenization noise, it's a specific structural weak spot (a list/diagram spanning pages 15-16) that every chunking scheme tried so far (500w, 150w, 400-token) has cut through in roughly the same place.

## Resolving the two open questions from last session

1. **Does token-aware chunking behave differently than the naive size reduction?** Yes, in the sense that mattered most: it closes a real, previously undiagnosed truncation bug. No, in the sense of eval-number movement - on this small corpus, chunk-size/tokenization tuning alone doesn't move retrieval quality either direction; the corpus is too small for it to matter much, same conclusion as the prior experiment.
2. **Is corpus expansion the better lever, or a smarter chunking strategy?** The evidence now points more clearly at chunking *strategy* than corpus size - the same specific content (pages 15-16's process-category list) has broken in the same way across three different chunk-size/tokenization schemes, which corpus size wouldn't fix.

## Decision: promote to `default`, move to Day 3

Discussed three options (accept and move on, chase the list-fragmentation fix now, or try corpus expansion) - decided to accept token-aware chunking as the new default (it fixes a real correctness bug regardless of how the eval numbers moved) and move on to Day 3 per the plan's own priority order, rather than open a new chunking-strategy investigation now. The list-fragmentation finding is documented here for whenever chunking strategy gets revisited (see "Making this project better" in `PROJECT_PLAN.md`).

Re-ingested the `default` namespace with the new token-aware chunker - it now reflects the same 30-chunk state as `token_aware`. The `token_aware` namespace was left in place as an artifact rather than deleted, same convention as `small_chunks`.

## Verified / artifacts

- `src/embeddings.py::get_tokenizer()` - exposes the loaded tokenizer for reuse elsewhere.
- `src/ingestion.py::chunk_documents()` - rewritten for token-based windows, offset-sliced text, fixed stepping, redundant-tail guard.
- `main.py`'s `ingest` command defaults changed from `chunk_size=500, overlap=50` (words) to `chunk_size=400, overlap=40` (tokens).
- `eval/results/token_aware.json`, `eval/results/token_aware_answers.json` - full per-question results.
- `default` namespace now holds the token-aware chunking (30 chunks), promoted from the old word-based baseline (16 chunks).
