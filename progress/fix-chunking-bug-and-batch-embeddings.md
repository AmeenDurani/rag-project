# Fix Chunking Bug & Batch Embeddings

## The chunking bug

`chunk_documents` originally had signature `(text, source, overlap=50, chunk_size=500)` — two adjacent same-typed (`int`) parameters. The (commented-out, unused) call site in `main.py` passed `chunk_documents(text, source, 10, 20)`, which binds positionally to `overlap=10, chunk_size=20` — technically consistent with the signature, but exactly the kind of call that's easy to get backwards without noticing, since nothing about `10, 20` signals which is which.

**Fix:** made both parameters keyword-only:

```python
def chunk_documents(text, source, *, chunk_size: int = 500, overlap: int = 50) -> list:
```

The `*` forces `chunk_size=`/`overlap=` to be named at every call site — `chunk_documents(text, source, 20, 10)` now raises `TypeError` instead of silently binding to the wrong parameter. The real fix isn't "getting the order right," it's removing the possibility of a silent mixup: whenever two adjacent parameters share a type, positional-only calling is a latent bug waiting to happen.

## Batch embeddings

`embeddings.py` originally reloaded the `fastembed` model from scratch on every single call (`add_embedding` created a new `TextEmbedding()` per chunk). Replaced with:

- A module-level lazy-loaded singleton (`_model`, populated once by `_get_model()`), rather than a class — there's exactly one model, one process, no configuration variance, so a class would only add ceremony. (Would revisit if there were ever a need for multiple models, e.g. A/B testing embedding models.)
- Three functions instead of one, sharing that cached model:
  - `embed_texts(list[str]) -> list[list[float]]` — the actual primitive, batch in/batch out.
  - `embed_chunks(list[Chunk])` — thin wrapper for the ingestion path.
  - `embed_query(str)` — thin wrapper for the retrieval path (embeds one string, unwraps the single result).
- `EMBEDDING_DIM = 384` defined next to the model that produces it (fastembed's default model, BAAI/bge-small-en-v1.5) — needed later because Pinecone requires the index dimension to exactly match the embedding output, and duplicating that number in two files would be a silent-drift risk if the model ever changes.
- Embeddings converted to plain Python lists (`.tolist()`) at the point of creation, not later — Pinecone's API expects JSON-serializable values, not numpy arrays, so the conversion happens once at the boundary instead of awkwardly wherever the vector happens to be consumed.
