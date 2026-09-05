# Repo Foundation & Housekeeping

The project had no version control, no dependency manifest, and two stale/duplicate Python environments before this. This entry covers getting the repo to a state where it can actually be handed to someone else (or reproduced later) and is version-controlled.

## What changed

- **`git init`**, default branch renamed `master` → `main` (current GitHub convention).
- **`.gitignore`**: excludes both venvs, `.env`, caches. Deliberately keeps `data/*.pdf` tracked — git should track things that can't be regenerated (source data), not things that can (a venv is 100% derived from `pyproject.toml` and is OS/architecture-specific, so committing it would actively break on another machine).
- **`pyproject.toml`** replacing the informal, manifest-less setup. Two things this gives us that a flat `requirements.txt` can't:
  - `dependencies` vs `optional-dependencies.dev` — runtime deps (pypdf, fastembed, anthropic, pinecone, pydantic-settings, typer) are separate from dev-only tooling (pytest, ruff, fastapi, uvicorn). A production Docker image (Day 4) only needs the former.
  - Makes the project an installable package, so `src/` is imported as `src.xxx` from anywhere, not just when the working directory happens to be the repo root. Installed with `pip install -e ".[dev]"` (editable — code edits take effect without reinstalling).
- **Consolidated two venvs into one.** The old `.venv` (Python 3.14) had only `pip`+`pypdf` installed and wasn't actually used; `.venv312` (Python 3.12) had the real dependencies. Deleted the stale one and rebuilt a single `.venv`.
  - **Gotcha hit along the way:** tried `mv .venv312 .venv` first — this broke, because every script under a venv's `bin/` has the interpreter's *absolute path* hardcoded in its shebang line, and `pyvenv.cfg` records the absolute source path too. Renaming the directory doesn't rewrite either. Fixed by deleting and recreating from the actual `python3.12` interpreter instead of trying to relocate it. Venvs are a build artifact, not a portable unit — same reason CI/Docker always build a fresh one rather than copying an existing one.
- **`.env.example`** documenting required env vars (`ANTHROPIC_API_KEY`, `GENERATION_MODEL`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, `PINECONE_REGION`, `TOP_K`).
- **`src/config.py`**: a typed `Settings` class (`pydantic-settings`) reading from `.env`, instantiated once at import time (`settings = Settings()`). Two things this buys:
  - Every place that needs a key/config value reads from one typed object instead of scattered `os.environ.get(...)` calls — a bad value (e.g. `TOP_K="five"`) fails validation immediately with a clear error instead of surfacing as a `TypeError` deep inside some other library later.
  - **Fail-fast by design**: importing `config` with a missing required key raises immediately, rather than the app running for a while and only failing right before the first API call. Trade-off: anything importing `config` now requires a valid `.env` to even import — so `chunk.py`/`embeddings.py` were kept free of any dependency on `config`, to stay testable/importable without secrets.
