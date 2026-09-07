from pathlib import Path

import anthropic
import pinecone.exceptions
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from src.api.dependencies import get_anthropic_client, get_store, lifespan
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

DATA_DIR = Path("data")


@app.exception_handler(anthropic.APIError)
async def anthropic_error_handler(request: Request, exc: anthropic.APIError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": f"Anthropic API error: {exc}"})


@app.exception_handler(pinecone.exceptions.PineconeException)
async def pinecone_error_handler(
    request: Request, exc: pinecone.exceptions.PineconeException
) -> JSONResponse:
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

    for file in files:
        dest = DATA_DIR / file.filename
        dest.write_bytes(await file.read())

        pages = extract_pages(dest)
        all_chunks.extend(
            chunk_documents(pages, file.filename, chunk_size=chunk_size, overlap=overlap)
        )

    embed_chunks(all_chunks)
    store.upsert(all_chunks, namespace=namespace)

    return IngestResponse(documents=len(files), chunks=len(all_chunks), namespace=namespace)


@app.post("/query", response_model=QueryResponse)
def query(
    body: QueryRequest,
    store: PineconeStore = Depends(get_store),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> QueryResponse:
    top_k = body.top_k or settings.top_k
    chunks = retrieve(body.question, store, top_k=top_k, namespace=body.namespace)

    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant chunks found.")

    result = generate(body.question, chunks, client, model=settings.generation_model)

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
