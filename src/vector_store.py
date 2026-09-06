from dataclasses import dataclass
from typing import Protocol

from pinecone import Pinecone, ServerlessSpec, Vector

from src.chunk import Chunk
from src.embeddings import EMBEDDING_DIM


@dataclass
class RetrievedChunk:
    text: str
    source: str
    chunk_id: int
    page_start: int
    page_end: int
    score: float


class VectorStore(Protocol):
    """What RAG needs from a vector store - independent of which one we use."""

    def upsert(self, chunks: list[Chunk], namespace: str = "default") -> None: ...

    def query(
        self, query_embedding: list[float], top_k: int, namespace: str = "default"
    ) -> list[RetrievedChunk]: ...


class PineconeStore:
    """Pinecone-backed VectorStore. Uses the legacy create_index() shim rather
    than the newer schema/deployment API - we only need plain dense-vector
    similarity search, and the shim is officially preserved for that case.
    """

    def __init__(self, api_key: str, index_name: str, cloud: str, region: str) -> None:
        self._client = Pinecone(api_key=api_key)
        self._index_name = index_name
        self._cloud = cloud
        self._region = region
        self._ensure_index()
        self._index = self._client.Index(index_name)

    def _ensure_index(self) -> None:
        if self._index_name not in self._client.list_indexes().names():
            self._client.create_index(
                name=self._index_name,
                dimension=EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud=self._cloud, region=self._region),
            )

    def upsert(self, chunks: list[Chunk], namespace: str = "default") -> None:
        vectors = [
            Vector(
                id=f"{chunk.source}::{chunk.chunk_id}",
                values=chunk.embedding,
                metadata={
                    "text": chunk.chunk,
                    "source": chunk.source,
                    "chunk_id": chunk.chunk_id,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                },
            )
            for chunk in chunks
        ]
        self._index.upsert(vectors=vectors, namespace=namespace)

    def query(
        self, query_embedding: list[float], top_k: int = 5, namespace: str = "default"
    ) -> list[RetrievedChunk]:
        response = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True,
        )
        return [
            RetrievedChunk(
                text=match.metadata["text"],
                source=match.metadata["source"],
                chunk_id=match.metadata["chunk_id"],
                page_start=match.metadata["page_start"],
                page_end=match.metadata["page_end"],
                score=match.score,
            )
            for match in response.matches
        ]
