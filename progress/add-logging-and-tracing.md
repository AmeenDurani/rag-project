# Add Structured Logging, Request IDs, Per-Stage Timing, and Cost Estimation

Last Day 3 item. Four design forks discussed and decided before implementing:

1. **Structured JSON logs**, not plain text - each log line is a JSON object a real log aggregator could query, explicitly named in `PROJECT_PLAN.md` as one of the things that separates "production-shaped" from "notebook-shaped."
2. **Request ID propagation via `contextvars` + a logging `Filter`**, not explicit parameter threading. A FastAPI middleware generates a UUID per request and stores it in a `ContextVar`; a `logging.Filter` reads it and injects it into every log record automatically. No function signature in the embed -> retrieve -> generate call chain needed to change.
3. **API only, not the CLI.** `main.py` keeps its existing direct-to-stdout human-readable output - it already prints token counts for a human reading a terminal, a different purpose than structured per-request logs for a service.
4. **A hardcoded pricing table, computing estimated dollar cost per request** - `{model: {input, output}}` dollars-per-million-tokens for the two models this project actually configures (`claude-sonnet-5`, `claude-haiku-4-5`). Returns `None` (not a guess) for any other model.

A fifth question came up mid-implementation: `retrieve()` currently does query-embedding and vector search in one call, so a literal "embed/retrieve/generate" three-way latency split isn't available without either touching `retrieve()`'s interface or duplicating its two-line body in the route. Decided to keep `retrieve()` untouched (still a small, pure, unit-tested function) and time it as one combined `embed_and_retrieve` stage instead - slightly less granular than the plan's literal wording, but avoids mixing logging/timing concerns into `src/retrieval.py`.

## Implementation

`src/api/observability.py` - new module, scoped to `src/api/` per decision 3:
- `request_id_var` (`contextvars.ContextVar`) + `RequestIdFilter` (a `logging.Filter` that injects it into every record).
- `JsonFormatter` - serializes standard fields (timestamp, level, logger, message, request_id) plus any caller-supplied `extra={...}` fields, by diffing a record's `__dict__` against a `logging.LogRecord`'s default attribute set (so any `extra` field anywhere in the app is included automatically, not a hardcoded field list).
- `configure_logging()` - replaces the root logger's handlers with the JSON formatter + request-ID filter. Called once from `dependencies.lifespan()` at app startup.
- `stage_timer(stages, name)` - a context manager recording elapsed milliseconds for one named stage into a dict the caller passes in. One consolidated summary log line per request (not one line per stage) - enough visibility at this project's scale without building out full span/trace concepts.
- `PRICING_PER_MILLION_TOKENS` + `estimate_cost_usd()`.

`src/api/routes.py`:
- `request_context_middleware` - assigns the request ID, times the whole request, logs one `"request completed"` (or `"request failed"`, on an unhandled exception) line with method/path/status/duration, and adds an `X-Request-ID` response header.
- `/query` wraps `retrieve()` as `embed_and_retrieve` and `generate()` as `generate`, then logs one `"query completed"` line with `stages_ms`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `num_sources`.
- `/ingest` wraps extract+chunk, embed, and upsert as three stages, then logs one `"ingest completed"` line with `stages_ms`, `documents`, `chunks`.
- The `anthropic.APIError`/`pinecone.exceptions.PineconeException` handlers now also log a warning with the actual exception message, not just returning the 502 response body.

## Verified

Ran a real request through `TestClient` against live Pinecone/Anthropic (not just the mocked unit tests) and inspected the actual log output:
- `request_id` correctly ties every log line for one request together, including from third-party loggers (`pinecone`, `httpx2`) that also propagate to the root logger - an unintended but useful side effect of configuring the root logger's handlers rather than only `src.*`.
- `X-Request-ID` response header present and matching the logged `request_id`.
- Real `/query` call: `stages_ms: {"embed_and_retrieve": 1612.09, "generate": 2496.09}`, `input_tokens: 4239`, `output_tokens: 83`, `estimated_cost_usd: 0.009308` - all correct.
- Full 23-test unit suite still passes after the change (lifespan now also calls `configure_logging()` on every test's `TestClient` startup - harmless, just means test runs print JSON logs too).

This closes out Day 3 (`PROJECT_PLAN.md`): FastAPI service layer, unit tests, and logging/tracing are all done. Config was already done on Day 1.
