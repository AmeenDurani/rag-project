# Add FastAPI Service Layer (/ingest, /query, /health)

First piece of Day 3 (`PROJECT_PLAN.md`). Chose to start here rather than tests or logging since the API is the biggest structural piece and the other two Day 3 items naturally attach to it - logging wraps the request path, tests exercise the endpoints that now exist.

## Design decisions made explicitly before coding

Two were close to mechanical given the existing codebase, stated rather than debated:

- **Sync `def` endpoints, not `async def`.** Pinecone, Anthropic, and fastembed are all synchronous SDKs. FastAPI auto-dispatches plain `def` path operations to a threadpool, so sync SDK calls never block the event loop - making the endpoints `async def` without also swapping in async clients would have been the wrong call.
- **Build `PineconeStore`/Anthropic client once at startup**, not per request - via FastAPI's `lifespan` + `Depends()`, extending the same composition-root pattern `main.py::_build_store()` already established for the CLI. Rebuilding `PineconeStore` per request would re-run its index-existence check (a `list_indexes()` call) on every single request.

Four were genuine forks, discussed and decided explicitly:

1. **File layout: `src/api/` package** (`routes.py`, `schemas.py`, `dependencies.py`), not a single `api.py` at repo root. Chose the more structured option over matching `main.py`'s flat single-file precedent.
2. **`POST /ingest` accepts file uploads** (multipart), not just a "re-ingest whatever's already in `data/`" trigger like the CLI. More realistic as an actual ingestion API.
3. **Uploaded files are persisted to `data/`** before processing, not just processed transiently in memory. Keeps `data/` as the single source of truth the CLI already treats it as - a later re-ingest (different chunk_size/overlap, or CLI-triggered) will still find the file.
4. **`GET /health` is shallow** (process + config only) rather than actually pinging Pinecone/Anthropic on every check - standard liveness-check behavior, avoids adding latency/cost to something that should be fast and free. Downstream failures surface through the query/ingest endpoints themselves instead.
5. **Error mapping:** no relevant chunks retrieved -> 404 (nothing to return). A Pinecone or Anthropic call raising -> 502 Bad Gateway (this service is fine, its dependency isn't) via global `@app.exception_handler` registrations for `anthropic.APIError` and `pinecone.exceptions.PineconeException` (both SDKs' actual base exception classes, confirmed by inspecting the installed packages rather than guessed). Validation errors (e.g. malformed request body) fall through to FastAPI's default 422 via pydantic - no custom handling needed there.

## Implementation notes

- `src/ingestion.py::load_documents()` had its `PdfReader` call inlined; split it out into `extract_pages(path)` so the new upload endpoint can extract pages from a saved upload the same way the CLI does from `data/`, without duplicating the pypdf call.
- `python-multipart` was missing (required by FastAPI for any file-upload/form endpoint) - added to `pyproject.toml`'s main dependencies, not dev-only, since the app can't start without it once `/ingest` exists. Also moved `fastapi`/`uvicorn` from the `dev` optional-dependency group to main dependencies - they were previously dev-only when the API didn't exist yet, but the app can't run in production without them now.
- Ruff flagged `Depends(...)` in argument defaults (B008, "don't call functions in mutable default arguments") - this is FastAPI's actual required DI pattern, not the bug the rule exists to catch. Added `extend-immutable-calls = ["fastapi.Depends", "fastapi.Query", "fastapi.Body"]` under `[tool.ruff.lint.flake8-bugbear]` rather than restructuring away from the correct pattern.

## Verified

Ran the app under `TestClient` (not just import-checked) against real Pinecone/Anthropic:
- `GET /health` -> 200.
- `POST /ingest` with a real PDF into an isolated `api_test` namespace -> 200, correct chunk count (30, matching the token-aware chunker).
- `POST /query` against that namespace -> 200, sensible grounded answer with 5 sources.
- `POST /ingest` with a non-PDF content-type -> 415, correctly rejected.
- `POST /query` against a namespace with no data -> 404, correctly reports no relevant chunks.

Test artifacts (the `api_test` namespace and its duplicate uploaded PDF in `data/`) were deleted after verification - this was a smoke test, not a lasting experiment artifact worth keeping like the chunking experiments' namespaces.

## Noted, not yet fixed

`src/generation.py::generate()` has the same latent bug class as the judge-eval fix in `fix-judge-thinking-token-budget-bug.md`: Claude Sonnet 5's default adaptive thinking could in principle consume the whole `max_tokens=1024` budget and leave no room for the answer. Lower risk here (1024 is generous vs. the judge's 256, and a `stop_reason != "end_turn"` mismatch is already logged), so left alone for now - flagged here in case it's worth a matching `thinking: {"type": "disabled"}` fix later.

## Not done yet (remaining Day 3 items)

Unit tests (chunking, batch embedding, vector store interface mocked, API endpoints via `TestClient`) and structured logging/tracing (per-stage latency, token/cost per request, request IDs) are still open.
