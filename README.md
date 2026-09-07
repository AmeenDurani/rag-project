# rag-project

A retrieval-augmented generation pipeline over the NASA Systems Engineering
Handbook, built from scratch (no LangChain/LlamaIndex) with an eval harness,
a FastAPI service layer, structured observability, a hermetic test suite,
Docker, and CI.

**[Read the technical whitepaper →](https://YOUR-VERCEL-PROJECT.vercel.app)**
<!-- TODO: replace with the real Vercel URL once whitepaper/ is deployed -->
for the design decisions, the eval-driven chunking iteration story (with real
before/after metrics), and known limitations. This README covers setup only.

[![CI](https://github.com/AmeenDurani/rag-project/actions/workflows/ci.yml/badge.svg)](https://github.com/AmeenDurani/rag-project/actions/workflows/ci.yml)

## Headline eval numbers

22 questions (18 answerable + 4 out-of-scope), current token-aware chunking config:

| Metric | Value |
|---|---|
| Recall@5 | 0.944 |
| MRR | 0.801 |
| Faithfulness | 1.0 |
| Relevance | 1.0 |
| Scope accuracy | 0.864 |

Full methodology, the three-iteration before/after comparison, and why some of
these numbers moved *down* on purpose: see the whitepaper.

## Setup

```bash
git clone https://github.com/AmeenDurani/rag-project.git
cd rag-project
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# fill in ANTHROPIC_API_KEY and PINECONE_API_KEY in .env
```

## Run it

**CLI:**
```bash
python main.py ingest          # loads data/*.pdf, chunks, embeds, upserts to Pinecone
python main.py ask "What is the purpose of the NASA Systems Engineering Handbook?"
```

**API (local dev):**
```bash
uvicorn src.api:app --reload
# POST /ingest (multipart file upload), POST /query, GET /health
```

**API (production-shaped, Gunicorn + Uvicorn workers):**
```bash
WEB_CONCURRENCY=2 gunicorn -k uvicorn.workers.UvicornWorker -w "$WEB_CONCURRENCY" -b 0.0.0.0:8000 src.api:app
```

**Docker:**
```bash
docker build -t rag-project .
docker run --env-file .env -p 8000:8000 -v "$(pwd)/data:/app/data" rag-project
```

## Tests

```bash
pytest     # 23 hermetic tests, ~2s, no live API calls or model downloads
ruff check .
```

## Eval harness

```bash
python -m eval.run_retrieval_eval --namespace default
python -m eval.run_answer_eval --namespace default
```

Results are written to `eval/results/`.

## Repo layout

```
src/            core pipeline: ingestion, embeddings, retrieval, generation, vector_store
src/api/        FastAPI service layer (routes, schemas, dependencies, observability)
eval/           eval harness (retrieval metrics, LLM-as-judge answer quality)
tests/          hermetic unit test suite
whitepaper/     hosted technical whitepaper (design decisions + eval story)
progress/       build log - one entry per topic, what changed and why
PROJECT_PLAN.md the 4-day plan and its reasoning
```

The full build log, including bugs found and fixed and alternatives considered
at each step, is in [`progress/`](progress/progress-log-overview.md).
