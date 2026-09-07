from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, Request

from src.config import settings
from src.vector_store import PineconeStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the Pinecone/Anthropic clients once at startup, not per-request.

    Reused across all requests via app.state - avoids re-running
    PineconeStore's index-existence check (a list_indexes() call) on every
    single request, mirroring the composition-root pattern main.py already
    uses for the CLI.
    """
    app.state.store = PineconeStore(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
    )
    app.state.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    yield


def get_store(request: Request) -> PineconeStore:
    return request.app.state.store


def get_anthropic_client(request: Request) -> anthropic.Anthropic:
    return request.app.state.anthropic_client
