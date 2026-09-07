# RAG Pipeline — Project Plan

Goal: build a naive RAG pipeline, understand it deeply, then turn it into an industry-grade project for an ML engineering internship portfolio. Timeline: 4 full working days (~32 hours).

## Locked-in decisions

| Decision | Choice | Why |
|---|---|---|
| Generation model | Claude Sonnet 5 (`claude-sonnet-5`), Haiku 4.5 (`claude-haiku-4-5`) as configurable cheaper swap | Best quality/cost balance for multi-chunk synthesis; model name kept in config, not hardcoded |
| Vector store | Pinecone, behind a custom `VectorStore` interface | Industry-recognizable, serverless free tier, no infra to babysit; interface keeps it swappable (e.g. FAISS for local/offline tests) |
| Framework | Built from scratch (no LangChain/LlamaIndex) | Forces real understanding of chunking/retrieval/prompting; better interview depth |
| Scope | Full production-shaped treatment: eval harness, API, Docker, CI, observability | Chosen deliberately, see cut-list below for what gives first if time is short |
| UI | Stretch goal, Day 4 only | Streamlit/Gradio demo — first thing cut if behind schedule |

## Current state as of 2026-09-05 (before this plan started)

**Done (partial):**
- `src/ingestion.py::load_documents()` — reads PDFs from `data/` via `pypdf`
- `src/chunk.py::Chunk` — simple container (text, id, source, embedding)
- `src/embeddings.py::add_embedding()` — embeds one `Chunk` via `fastembed`

**In progress / buggy:**
- `chunk_documents()` argument order bug: signature is `(text, source, overlap=50, chunk_size=500)` but the commented-out call site in `main.py` passes `(text, source, 10, 20)`
- `main.py` doesn't run the real pipeline — just a scratch test on one hardcoded string
- Embedding model reloaded from scratch on every call — no batching

**Not started:**
- Vector store / persistence, retrieval, generation, end-to-end wiring
- Dependency manifest (no `requirements.txt`/`pyproject.toml`), no git repo, two stale/duplicate venvs (`.venv`, `.venv312`)

---

## Day 1 — Foundation + working naive RAG end-to-end

- [x] `git init` + `.gitignore` (exclude both venvs, `.env`, `__pycache__`)
- [x] Consolidate to one env via `pyproject.toml`; drop the loose venvs
- [x] `.env.example` for `ANTHROPIC_API_KEY` / `PINECONE_API_KEY`
- [x] Fix `chunk_documents` argument-order bug
- [x] Batch embeddings: load the `fastembed` model once, embed in batches (not per-call)
- [x] `VectorStore` interface + `PineconeStore` implementation — create index, upsert chunks with metadata (source, chunk_id)
- [x] Retrieval: embed query → top-k similarity search
- [x] Generation: prompt template (system + retrieved context + question) → Claude Sonnet 5 → answer with cited sources
- [x] Wire it together: simple CLI (`ingest`, `ask`)

**Milestone:** working naive RAG, queryable from the CLI. **Status: verified end-to-end** — ingest and ask both run successfully against live Pinecone + Anthropic. See `progress/first-live-run-and-baseline-results.md`.

## Day 2 — Prove it works, then improve it

- [x] Build an eval set: 15–25 Q&A pairs grounded in the NASA handbook
- [x] Include a handful of **out-of-scope / no-answer** questions (see "make this better" below — don't skip this)
- [x] Retrieval metrics: recall@k, MRR against the eval set
- [x] Answer quality eval: LLM-as-judge (Claude) scoring faithfulness/relevance, logged to JSON/CSV
- [x] Upgrade chunking to token-aware (real tokenizer, not word count), tune chunk size/overlap using the baseline, re-run eval
- [ ] Stretch: citations in the answer (page/source per claim)

**Milestone:** quantified retrieval/answer quality with a documented before/after improvement. **Status: complete.** Real `baseline` numbers: recall@1=0.778, recall@3=0.944, recall@5=1.0, MRR=0.863; faithfulness/relevance/scope accuracy all 1.0 (spot-checked by hand, not taken on faith - see `progress/first-live-run-and-baseline-results.md`). That perfect baseline turned out to be a ceiling effect (only 16 total chunks, so top_k=5 = 31% of the corpus) - a diagnostic experiment shrinking chunk size alone (word-based, not yet token-aware) *reduced* recall@5 to 0.944 rather than improving it, with two individually-diagnosed failures (see `progress/experiment-smaller-chunk-size.md`). Milestone 4 closed with `progress/token-aware-chunking-and-truncation-fix.md`: word-based chunking turned out to silently truncate ~30% of every chunk's text at embedding time (chunks averaged ~700 real tokens against the model's 512-token limit) - a correctness bug, not just a tuning question. Page-level chunking was considered and rejected (55% of pages exceed 512 tokens alone). Token-aware chunking (400 tokens/40 overlap) fixed the truncation bug and is now the `default` namespace; eval numbers moved flat-to-slightly-down on this small corpus (same ceiling-effect-unmasking pattern, not a quality drop) but sharpened a specific finding - a process-category list on pages 15-16 gets fragmented across a chunk boundary under every chunking scheme tried so far, pointing at chunking *strategy* (not corpus size) as the more promising lever for whenever this gets revisited (see "Making this project better" below).

## Day 3 — Service layer + observability + tests

- [ ] FastAPI: `/ingest`, `/query`, `/health` with pydantic schemas and error handling
- [ ] Logging/tracing: per-stage latency (embed/retrieve/generate), token usage & cost per request, request IDs
- [ ] Unit tests: chunking, batch embedding, vector store interface (mocked), API endpoints via `TestClient`
- [ ] Config: `pydantic-settings` for all env vars, fail-fast on missing keys

**Milestone:** runnable API with per-request logs/metrics and test coverage on core logic.

## Day 4 — Containerize, CI, document, stretch UI

- [ ] Dockerfile for the API (Pinecone stays managed, no local DB container needed)
- [ ] GitHub Actions: lint (ruff) + pytest on push/PR
- [ ] README: architecture diagram, setup steps, eval results table (before/after), a design-decisions section (why Pinecone, why Sonnet 5, why from-scratch, known limitations)
- [ ] Stretch: Streamlit/Gradio UI — question box, shows retrieved chunks + answer + sources

**Milestone:** containerized, CI-checked, documented project ready to link from a resume.

### Cut order if behind schedule
1. UI (stretch, cut first)
2. CI
3. Docker
4. Detailed tracing/observability depth

Eval + a working API are non-negotiable — they're what separates "naive" from "industry grade" on paper.

---

## Project quality assessment: pros and cons

### Pros
- **Evaluation-driven, not just a demo.** recall@k/MRR + LLM-judge faithfulness + a documented before/after from a chunking change is the single biggest differentiator versus typical tutorial RAG projects, which stop at "look, it answers questions."
- **Built from scratch.** No LangChain/LlamaIndex means you can explain retrieval/chunking/prompting from first principles in an interview instead of "the framework handles that."
- **Architecture shows engineering maturity:** `VectorStore` interface, `pydantic-settings`, structured logging, per-request token/cost tracking — small additions that read as production-aware, not notebook-aware.
- **Resume/ATS-friendly tool selection:** Pinecone, FastAPI, Docker, CI, Claude API are all recognizable names.

### Cons — be honest about these, in the README and in interviews
- **Single small PDF corpus.** Proves the pipeline works but exercises none of the hard problems at scale (incremental re-indexing, dedup, staleness, sharding). Name this explicitly as a known limitation rather than letting it surprise you in an interview.
- **This is naive-RAG-plus, not advanced RAG.** No hybrid (BM25+dense) search, no re-ranking, no query rewriting. Right scope for 4 days — but don't oversell it as "advanced/agentic RAG" in resume language; say "implemented and evaluated a RAG pipeline."
- **15–25 eval questions is a smoke test, not a statistically meaningful benchmark.** Frame it as "an eval harness plus a sanity-check dataset."
- **LLM-as-judge bias risk:** using Claude to both generate and judge answers has a known self-preference bias. Preempt this in the README (e.g. spot-check judge scores by hand, or use a stricter reference-based rubric) — doing so turns it from a weakness into a sign of eval literacy.
- **No "no answer in context" handling** was in the original scope — added into Day 2 above. This is one of the most common real-world RAG failure modes and costs almost nothing to test for.
- **"Production treatment" here is production-*shaped*, not production-*proven*.** No real traffic, no load testing, no live monitoring. Normal for a solo 4-day project — just phrase resume bullets accordingly ("production-oriented tooling: Docker, CI, structured logging, cost tracking" rather than "built a production service").

**Bottom line:** strong for an ML engineering internship bar. The payoff comes almost entirely from the eval numbers and the "why" section of the README — that's where to spend disproportionate care if the 4 days get tight, more than on Docker/CI polish.

---

## Making this project better (post-4-day refinement)

If there's time after the initial 4 days, tackle these roughly in priority order — each is chosen because it directly answers one of the "cons" above.

### 1. Close the credibility gaps first (highest ROI, lowest effort)
- [ ] Grow the eval set from ~20 to 75–100+ questions, including out-of-scope/no-answer cases and a few adversarial/ambiguous ones
- [ ] Mitigate judge bias: manually spot-check 15–20% of LLM-judge scores against your own labels, report agreement rate; consider a second judge model or a stricter rubric with explicit reference answers
- [ ] Add explicit "I don't know" behavior when retrieval confidence is low, and test it — don't let the model hallucinate confidently on out-of-scope questions
- [ ] Rewrite README limitations section to be specific and quantified (not just "small dataset" — say exactly how small, and what you'd need to fix it)

### 2. Expand the corpus and prove it scales
- [ ] Add multiple documents / a full document set (tens to hundreds of pages across several files), not just one PDF
- [ ] Implement incremental ingestion: detect new/changed documents, upsert only deltas instead of rebuilding the whole index
- [ ] Add dedup logic for overlapping/duplicate chunks across documents
- [ ] Load-test retrieval latency as corpus size grows; report numbers

### 3. Add retrieval sophistication (moves from naive-plus toward advanced RAG)
- [ ] Hybrid search: combine dense (Pinecone) with sparse/keyword (BM25) retrieval, fuse rankings (e.g. reciprocal rank fusion)
- [ ] Re-ranking: cross-encoder or Claude-based re-ranker on top-k candidates before final context selection
- [ ] Query transformation: query rewriting or decomposition for multi-part questions
- [ ] Metadata filtering (by source/section/date) as a retrieval parameter

### 4. Strengthen the "production" story with real evidence
- [ ] Deploy the API somewhere real (Render/Fly.io/AWS free tier) rather than only Docker-locally
- [ ] Add basic monitoring/alerting on the deployed instance (even a simple uptime + error-rate check)
- [ ] Add rate limiting and basic auth on the API
- [ ] Write a short load test (e.g. locust or a simple script) and report p50/p95 latency under concurrent requests

### 5. Portfolio presentation polish
- [ ] Architecture diagram as an actual image (not ASCII), showing data flow ingest → chunk → embed → store → retrieve → generate
- [ ] A "lessons learned / what I'd do differently at scale" section in the README — this is often what differentiates interview conversations
- [ ] Short demo video/GIF if the UI stretch goal was built
- [ ] Pin exact eval numbers (recall@k, MRR, faithfulness score) in the README with the before/after chunking comparison front and center

Do not attempt all of these at once — pick whichever section addresses the weakest point an interviewer is most likely to probe, given how far the 4-day build actually got.
