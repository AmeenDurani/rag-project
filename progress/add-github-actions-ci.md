# Add GitHub Actions CI (Lint + Pytest)

Second Day 4 item (`PROJECT_PLAN.md`).

## Design decisions made explicitly before coding

Mechanical, stated rather than debated:
- **Two parallel jobs (`lint`, `test`)**, not one combined job - gives independent pass/fail signal per concern in the PR UI instead of one job hiding which check actually failed.
- **`ubuntu-latest` + Python 3.12** - matches `requires-python`/`target-version = "py312"` already set in `pyproject.toml`.
- **Triggers: `push` and `pull_request` on `main`** - matches the plan's own wording ("lint + pytest on push/PR").
- **`pip install ".[dev]"`** in both jobs, no lockfile - same install command local dev already uses, no new tooling introduced.

No live-API secrets needed: `tests/conftest.py` already sets dummy `ANTHROPIC_API_KEY`/`PINECONE_API_KEY` via `os.environ.setdefault()` before any `src.*` import (from `add-unit-test-suite.md`), and the test suite is fully hermetic (mocked `fastembed`/`pinecone`/`anthropic`, no real network calls). So CI runs with zero repository secrets configured.

## Verified

Ran the exact commands the workflow uses, from a completely clean copy of the repo (no `.venv`, no real `.env`) in a fresh Python 3.12 venv, with no API keys set in the environment:
- `pip install ".[dev]"` - succeeds.
- `ruff check .` - all checks pass.
- `pytest` - 23 passed, matching the local dev run.

This confirms the workflow will pass on a fresh GitHub-hosted runner without any secrets configured, before ever pushing it.
