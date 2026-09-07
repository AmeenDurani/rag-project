from fastembed import TextEmbedding

from src.chunk import Chunk

# fastembed's default model (BAAI/bge-small-en-v1.5) outputs 384-dim vectors.
# Pinecone's index dimension must match this exactly - defined here, next to
# the model that produces it, so there's one place to update if it ever changes.
EMBEDDING_DIM = 384

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    """Lazily load and cache the embedding model so it's created once per process."""
    global _model
    if _model is None:
        _model = TextEmbedding()
    return _model


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    model = _get_model()
    return [embedding.tolist() for embedding in model.embed(texts, batch_size=batch_size)]


def embed_chunks(chunks: list[Chunk], batch_size: int = 32) -> list[Chunk]:
    """Embed chunks in batches, reusing one loaded model instead of reloading per chunk."""
    embeddings = embed_texts([chunk.chunk for chunk in chunks], batch_size=batch_size)

    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    return chunks


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def get_tokenizer():
    """Return the tokenizer already loaded inside the embedding model.

    Callers that need to count tokens (e.g. chunking) should use this rather
    than loading a tokenizer independently, so the count matches exactly what
    the embedding call itself sees - that's what actually determines
    truncation. Reaches into a private fastembed attribute path
    (model.model.tokenizer); if a fastembed upgrade breaks this, this is the
    one place to fix it.
    """
    return _get_model().model.tokenizer
