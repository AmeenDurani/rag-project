# Add Dockerfile (Gunicorn + Uvicorn Workers)

First Day 4 item (`PROJECT_PLAN.md`).

## Design decisions made explicitly before coding

Mechanical, stated rather than debated:
- **Single-stage `python:3.12-slim` build.** No compiled-artifact/build-vs-runtime split here (just `pip install`ing wheels), so a multi-stage build would add complexity without a real image-size or security payoff at this project's scope.
- **Port 8000**, standard Gunicorn/Uvicorn convention.
- **Secrets via `docker run --env-file .env`** at run time, never baked into the image - matches the `.env`/`pydantic-settings` pattern already established on Day 1.
- **No dependency lockfile.** The project has used floor-pinned (`>=`) versions in `pyproject.toml` with no lockfile since Day 1; adding one now would be a scope expansion beyond what containerizing the existing setup requires.

Two were genuine forks, discussed and decided explicitly:

1. **Gunicorn (with `uvicorn.workers.UvicornWorker`) as a process manager, not a bare `uvicorn` process.** A single Uvicorn process is one OS process with one GIL - FastAPI's sync `def` endpoints get dispatched to a threadpool *within* that process, which helps I/O-bound work (waiting on Pinecone/Anthropic) overlap, but CPU-bound work (tokenizing, embedding inference) still serializes on one core, and a single unhandled crash takes the whole service down. Multiple Gunicorn-managed worker processes let the app use multiple CPU cores and gives crash isolation + auto-restart per worker. This is single-host/vertical scaling (using more of one machine's cores) - a different axis from horizontal scaling (multiple container replicas behind a load balancer), which is out of scope here (no orchestrator in this project).
2. **`data/` (where `/ingest` persists uploaded PDFs) is mounted as a volume**, not left as container-ephemeral storage - `docker run -v ./data:/app/data ...`. A container's filesystem is ephemeral by default; without a mount, an uploaded PDF disappears on restart even though its vectors would already be durable in Pinecone (external to the container).

## Implementation notes

- **Worker count is env-var configurable** (`WEB_CONCURRENCY`, Gunicorn's standard convention), defaulting to 2 - not a `2 x CPU_count + 1` formula. That formula assumes CPU-bound-ish workloads; this app's per-request time is dominated by waiting on Pinecone/Anthropic network calls (per `add-logging-and-tracing.md`'s real numbers, e.g. `embed_and_retrieve: 1612ms, generate: 2496ms`), so the formula's assumption doesn't cleanly transfer. A fixed small default also keeps the number honest for a portfolio-scale deployment rather than implying it's been load-tested and tuned.
- `src/embeddings.py`'s embedding model is a **process-level singleton** - with N Gunicorn workers, the model gets loaded into memory N separate times (once per process, no sharing). Worth sizing `WEB_CONCURRENCY` with this in mind; flagged here rather than in a comment buried in the Dockerfile.
- `.dockerignore` excludes `tests/`, `eval/`, `progress/`, `rules/`, and all markdown - none of it is needed to serve the API, and keeping it out keeps the image lean.
- `data/` (containing the existing NASA handbook PDF) is copied into the image so it's self-contained if run without a volume mount; when the volume mount is used, the host directory shadows it, which is the intended, more common case.

## Verified

Docker itself isn't installed on this machine, so the actual `docker build`/`docker run` couldn't be exercised. Verified the equivalent pieces directly instead:
- **Packaging step**: copied the exact file set the Dockerfile stages (`pyproject.toml`, `src/`, `main.py`) into a scratch directory, ran `pip install --no-cache-dir .` (clean, non-editable - not the `-e .` install used in local dev) in a fresh venv, and confirmed `src.api` imports and `app` builds successfully.
- **The exact CMD** (`gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 src.api:app`) run locally against real Pinecone/Anthropic credentials: two independent worker processes (distinct PIDs) each ran `lifespan()` startup fully (real Pinecone index-existence check succeeded on both), and both served real `/health` requests successfully (200, distinct `request_id`s, sub-5ms).

**Gap:** the Dockerfile's own build layer (base image behavior, `COPY` paths, build cache) has not been exercised in an actual container. Recommend running `docker build` once Docker is available before treating this as fully verified end-to-end, matching the bar every other progress entry in this project holds itself to.
