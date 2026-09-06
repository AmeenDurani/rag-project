# Add Page Provenance to Chunks

Day 2 planning surfaced a gap: the Day 2 eval harness needs to label eval questions with "which page(s) of the source PDF answer this," then check whether retrieval returns a chunk overlapping those pages (recall@k/MRR). Day 1's `Chunk` had no way to answer that — it only carried `chunk_id` (a sequential counter reassigned every chunking run) and `source` (the filename). `load_documents()` also flattened all PDF pages into one joined string before chunking, discarding page boundaries entirely.

## Why `chunk_id` alone doesn't work for eval ground truth

`chunk_id` identifies a chunk *within a given chunking run* — useful for the Pinecone vector ID (`f"{source}::{chunk_id}"`) and for distinguishing multiple chunks that land on the same page. But Day 2 also upgrades chunking (token-aware, tuned size/overlap) specifically to produce a before/after comparison. Re-chunking reassigns every `chunk_id` from scratch, so ground truth labeled by chunk ID would be invalidated by the exact change we're trying to measure. Page numbers are a property of the source PDF, not of any chunking run, so they survive re-chunking unchanged. `chunk_id` and page numbers aren't redundant — one is identity-within-a-run, the other is provenance-across-runs — so both are kept.

## What changed

- `src/ingestion.py::load_documents()` — extracts each PDF page's text separately (`pages: list[str]`) instead of joining into one string, so page boundaries survive into chunking.
- `src/ingestion.py::chunk_documents()` — signature changed from `(text, source, ...)` to `(pages, source, ...)`. The word-based overlapping-chunk algorithm itself is unchanged; it now also builds a parallel `word_pages` array (which page each word in the concatenated stream came from) and uses it to compute `page_start`/`page_end` per chunk. A chunk can still span two pages (e.g. `page_start=2, page_end=3`) if a chunk boundary falls mid-page — chunking behavior wasn't changed to avoid spanning pages, since forcing chunks to stay within a single page would fragment text at every page break for no retrieval-quality benefit, just eval-bookkeeping convenience.
- `src/chunk.py::Chunk` — added `page_start`, `page_end` fields.
- `src/vector_store.py` — `PineconeStore.upsert()` now writes `page_start`/`page_end` into Pinecone metadata; `RetrievedChunk` gained the same two fields, populated in `PineconeStore.query()`.
- `main.py::ingest()` — updated call site for the `chunk_documents` signature change (`document["pages"]` instead of `document["text"]`).

## Verified

- `python main.py --help` / `ingest --help` still succeed with no `.env` (composition-root laziness from the previous entry is unaffected).
- Offline unit-level check of `chunk_documents()` with synthetic 3-page input confirms page tracking is correct across a chunk that spans a page boundary, including with overlap.
- `load_documents()` confirmed returning 20 separate page strings for the NASA handbook PDF (matches the PDF's actual page count).
- Not yet verified end-to-end against live Pinecone (same open blocker as Day 1 — no API keys yet).

## Still open

- `src/generation.py::_format_context()` still cites chunks as `(source: ..., chunk N)` without page number. Left untouched here since it's out of scope for this change (page number isn't needed for generation grounding, only for eval) — Day 2's citation stretch goal may revisit this.
