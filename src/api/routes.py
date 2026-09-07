import logging
import time
import uuid
from pathlib import Path

import anthropic
import pinecone.exceptions
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from src.api.dependencies import get_anthropic_client, get_store, lifespan
from src.api.observability import estimate_cost_usd, request_id_var, stage_timer
from src.api.schemas import (
    HealthResponse,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceSchema,
)
from src.config import settings
from src.embeddings import embed_chunks
from src.generation import generate
from src.ingestion import chunk_documents, extract_pages
from src.retrieval import retrieve
from src.vector_store import PineconeStore

app = FastAPI(title="rag-project", lifespan=lifespan)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Assigns a request ID (via contextvars, so no function signature in the
    embed/retrieve/generate call chain needs to carry it) and logs one
    completion (or failure) line per request with total latency.
    """
    request_id = uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "request failed",
            extra={"method": request.method, "path": request.url.path, "duration_ms": duration_ms},
        )
        raise
    finally:
        request_id_var.reset(token)


@app.exception_handler(anthropic.APIError)
async def anthropic_error_handler(request: Request, exc: anthropic.APIError) -> JSONResponse:
    logger.warning("Anthropic API error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": f"Anthropic API error: {exc}"})


@app.exception_handler(pinecone.exceptions.PineconeException)
async def pinecone_error_handler(
    request: Request, exc: pinecone.exceptions.PineconeException
) -> JSONResponse:
    logger.warning("Pinecone error: %s", exc)
    return JSONResponse(status_code=502, content={"detail": f"Pinecone error: {exc}"})


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    files: list[UploadFile],
    namespace: str = "default",
    chunk_size: int = 400,
    overlap: int = 40,
    store: PineconeStore = Depends(get_store),
) -> IngestResponse:
    """Save each uploaded PDF into data/ (so it's a durable part of the
    corpus, same source of truth the CLI's ingest reads from), then chunk,
    embed, and upsert.
    """
    if not files:
        raise HTTPException(status_code=422, detail="No files provided.")

    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=415,
                detail=f"{file.filename}: expected application/pdf, got {file.content_type}",
            )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    stages: dict[str, float] = {}

    with stage_timer(stages, "extract_and_chunk"):
        for file in files:
            dest = DATA_DIR / file.filename
            dest.write_bytes(await file.read())

            pages = extract_pages(dest)
            all_chunks.extend(
                chunk_documents(pages, file.filename, chunk_size=chunk_size, overlap=overlap)
            )

    with stage_timer(stages, "embed"):
        embed_chunks(all_chunks)

    with stage_timer(stages, "upsert"):
        store.upsert(all_chunks, namespace=namespace)

    logger.info(
        "ingest completed",
        extra={
            "namespace": namespace,
            "documents": len(files),
            "chunks": len(all_chunks),
            "stages_ms": stages,
        },
    )

    return IngestResponse(documents=len(files), chunks=len(all_chunks), namespace=namespace)


@app.post("/query", response_model=QueryResponse)
def query(
    body: QueryRequest,
    store: PineconeStore = Depends(get_store),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> QueryResponse:
    top_k = body.top_k or settings.top_k
    stages: dict[str, float] = {}

    with stage_timer(stages, "embed_and_retrieve"):
        chunks = retrieve(body.question, store, top_k=top_k, namespace=body.namespace)

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant chunks found.")

    with stage_timer(stages, "generate"):
        result = generate(body.question, chunks, client, model=settings.generation_model)

    logger.info(
        "query completed",
        extra={
            "namespace": body.namespace,
            "top_k": top_k,
            "num_sources": len(chunks),
            "stages_ms": stages,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "estimated_cost_usd": estimate_cost_usd(
                settings.generation_model, result.input_tokens, result.output_tokens
            ),
        },
    )

    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceSchema(
                source=s.source,
                chunk_id=s.chunk_id,
                page_start=s.page_start,
                page_end=s.page_end,
                score=s.score,
            )
            for s in result.sources
        ],
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
