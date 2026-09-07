# Add Unit Test Suite (chunking, batch embedding, vector store, API)

Second Day 3 item, done before logging/tracing per explicit direction. All design forks were discussed and decided before writing any test - see the decisions below.

## Decisions made explicitly before coding

1. **`chunk_documents()` refactored to accept an optional `tokenizer` parameter**, defaulting to `get_tokenizer()` when not given - the same store-injection pattern `retrieve()` already uses for `VectorStore`. Without this, testing the chunker would require loading the real fastembed model (slow, network-dependent) just to count tokens.
2. **Embedding tests mock `fastembed.TextEmbedding` entirely** (patch the class, verify `embed_texts`/`embed_chunks` batching behavior against a fake) rather than exercising the real model - fast, hermetic, no download.
3. **Vector store tests cover two different things, not one:** `PineconeStore` itself is tested against a mocked `pinecone.Pinecone` client (verifies it builds correct `Vector`/metadata on upsert and parses `response.matches` correctly on query) - this is the "vector store interface (mocked)" item the plan names. Separately, a hand-written in-memory `FakeVectorStore` (implementing the same `VectorStore` Protocol) is used to test `retrieve()` and the `/query` endpoint's own logic, decoupled from any Pinecone-specific concern.
4. **Fixture PDFs are synthesized on the fly**, not the real corpus file. Built via pypdf's own `PdfWriter` object model (`add_blank_page` + a manually-attached content stream) rather than a rendering library - no new dependency just for test fixtures, and pypdf's writer handles xref/trailer bookkeeping, so this doesn't need hand-computed byte offsets (verified empirically: `PdfReader` round-trips real extractable text from a document built this way).

## A gap this surfaced: hermetic test collection vs. fail-fast config

`src/config.py::Settings()` is instantiated at import time and fails fast if `ANTHROPIC_API_KEY`/`PINECONE_API_KEY` aren't set - correct behavior for production, but it means importing anything that transitively imports `src.config` (including `src.api`) would break during test collection in an environment with no real `.env` (e.g. CI, or a fresh clone), even though none of these tests make a real API call. Fixed by setting dummy fallback values via `os.environ.setdefault(...)` at the very top of `tests/conftest.py`, before any `src.*` import - `setdefault` only fills gaps, and `os.environ` always wins over `.env` in pydantic-settings' resolution order, so this guarantees the test suite never actually depends on real secrets without touching an environment that already has them (verified: this machine's real `.env` keys are untouched, tests still pass).

## Testing `/ingest` and `/query` without hitting live Pinecone/Anthropic

FastAPI's `app.dependency_overrides` only replaces `Depends()` callables - it doesn't stop `lifespan()` from running, which fires unconditionally on every `TestClient` startup and would otherwise try to build a real `PineconeStore` (a real `list_indexes()` call). Instead, API tests patch what `dependencies.lifespan()` itself constructs - `src.api.dependencies.PineconeStore` and `src.api.dependencies.anthropic.Anthropic` - so `get_store()`/`get_anthropic_client()` naturally return the fakes via `app.state`, with no other code path changed and no app-factory refactor needed.

## Chunker refactor detail

`chunk_documents(..., tokenizer=None)` - when a tokenizer is passed, it's still cloned via `to_str()`/`from_str()` and had truncation disabled the same way the default path does, so tests exercise the exact same code path as production, not a special-cased branch. The test tokenizer itself (`tests/conftest.py::make_test_tokenizer()`) is a real minimal `tokenizers.Tokenizer` (WordLevel model + `Whitespace` pre-tokenizer, one token per whitespace-separated word) rather than a hand-rolled fake reimplementing the `encode()` -> offsets/special_tokens_mask/`to_str()` interface - confirmed empirically it produces the exact same `Encoding` shape (offsets, `special_tokens_mask` flagging `[CLS]`/`[SEP]`) the real bge tokenizer does.

## Verified

23 tests, all passing, full suite runs in under 2 seconds - no model downloads, no live API calls. Covers: `extract_pages`/`chunk_documents` (chunk-size respect, overlap sharing, the redundant-tail guard, page provenance, sequential ids, byte-identical text slicing), `embed_texts`/`embed_chunks` (batch size passthrough, correct chunk-to-embedding assignment, model loaded once), `PineconeStore` (index-exists vs. needs-creation, upsert metadata shape, query response parsing), `retrieve()` (query embedding + pass-through args), `generate()` (context formatting, the same empty-text-block failure mode as the judge-thinking bug, tested directly this time), and all three API endpoints (health, query golden path + 404, ingest golden path + 415 content-type rejection).

Ran `ruff check` on `tests/` after writing - two auto-fixable import-order issues, fixed via `--fix`, then re-verified the full suite still passes.

## Not done yet

Logging/tracing (per-stage latency, token/cost per request, request IDs) is the remaining Day 3 item.
