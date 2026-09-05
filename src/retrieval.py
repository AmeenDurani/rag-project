from src.embeddings import embed_query
from src.vector_store import RetrievedChunk, VectorStore


def retrieve(
    query: str, store: VectorStore, top_k: int = 5, namespace: str = "default"
) -> list[RetrievedChunk]:
    """Embed the query and fetch the top-k most similar chunks.

    Takes `store` as a parameter rather than constructing one internally so
    this stays importable/testable without live Pinecone credentials - a
    test passes a fake VectorStore, real usage passes a PineconeStore built
    at the composition root (the CLI/API entry point).
    """
    query_embedding = embed_query(query)
    return store.query(query_embedding, top_k=top_k, namespace=namespace)
