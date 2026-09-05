# Wire End-to-End CLI, Fix a Config-Boundary Inconsistency

## `main.py` — the composition root

Added a `typer`-based CLI with two commands:
- `ingest [--namespace]` — `load_documents()` → `chunk_documents()` per document → `embed_chunks()` → `store.upsert()`.
- `ask <question> [--namespace]` — `retrieve()` → `generate()` → prints the answer, numbered sources, and token counts.

This is the first place in the codebase that reads `settings` and constructs concrete objects (`PineconeStore`, `anthropic.Anthropic`) — every other module (`chunk.py`, `embeddings.py`, `retrieval.py`, `generation.py`) takes what it needs as parameters and stays config-agnostic, per the composition-root pattern established while designing `retrieval.py`.

## Found and fixed: `PineconeStore` didn't actually follow that pattern

Writing `main.py` surfaced that `vector_store.py` (written before the composition-root pattern was made explicit) imported `settings` at module level and read it directly inside `PineconeStore.__init__`. Concretely, this broke `python main.py --help` — even asking for help text crashed with a `pydantic` `ValidationError` for missing API keys, because importing `PineconeStore` transitively imported and validated `config.Settings()`.

**Fix:** `PineconeStore.__init__` now takes `api_key`, `index_name`, `cloud`, `region` as explicit constructor parameters instead of reaching into global `settings`. `vector_store.py` no longer imports `config` at all. `main.py` reads `settings` lazily (import inside each command function, via a small `_build_store()` helper), so:
- `--help` and command listing work with zero configuration.
- Actually running `ingest`/`ask` without real keys still fails immediately with a clear, specific error (`Field required: anthropic_api_key, pinecone_api_key`) — fail-fast is preserved exactly where it matters, not everywhere indiscriminately.

Verified both behaviors directly: `main.py --help` / `main.py ingest --help` / `main.py ask --help` all succeed with no `.env` present; `main.py ingest` still fails fast with the expected validation error.

## Status: Day 1 code-complete, unverified end-to-end

All 9 Day 1 tasks are done. Every module is written and syntax-checked; SDK usage (Pinecone v10, Anthropic) was verified against the actually-installed packages rather than assumed from memory. Nothing has been run against live Pinecone/Anthropic yet — no API keys available. That's the real remaining blocker before naive RAG can be confirmed working, not a design or implementation gap.
