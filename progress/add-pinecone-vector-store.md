# Add Pinecone Vector Store

Nothing existed yet to persist or search embeddings. Added a `VectorStore` abstraction plus a Pinecone-backed implementation.

## Why abstract at all, given we're only ever using Pinecone

Two concrete reasons, not hypothetical ones:

1. Day 3 of the plan requires unit-testing retrieval logic with the vector store mocked. Code that calls the Pinecone SDK directly would force tests to either hit a live index or mock Pinecone's own SDK shape — brittle, since that pins tests to a third party's method signatures instead of ours.
2. It's dependency inversion / the "ports and adapters" pattern for third-party integrations: core RAG logic (chunk → embed → retrieve → generate) shouldn't know which vector database it's talking to. Only the adapter does.

Explicitly *not* over-engineering this: the interface only has the two methods RAG actually needs (`upsert`, `query`), not a mirror of everything Pinecone's SDK offers — a 1:1 rename of Pinecone's own API would be a "leaky abstraction" that adds indirection without real decoupling.

## Design decisions made (discussed before implementing)

- **`typing.Protocol` over `abc.ABC`.** Structural typing: a test fake just needs matching method names, no inheritance required. With `ABC` the fake would have to explicitly subclass `VectorStore`.
- **`RetrievedChunk` dataclass** (`text`, `source`, `chunk_id`, `score`) returned by `query()`, instead of Pinecone's raw match object — downstream code (prompt building, later eval scoring) depends on our shape, not Pinecone's response format. `score` is included now (not strictly needed by Day 1) because Day 2's "say I don't know" behavior needs a confidence signal, and that signal is the top match's score.
- **Deterministic chunk IDs**: `f"{source}::{chunk_id}"`. Re-ingesting the same document produces the same IDs, so Pinecone's upsert overwrites rather than duplicates — ingestion is idempotent by construction, not by remembering to delete first.
- **Namespace parameter added now**, not deferred: `namespace: str = "default"` on both methods. We only have one document today, but this is the natural partition boundary for "multiple documents" (a known near-term item), and it costs one optional parameter now vs. a harder migration later.
- **Index creation as a constructor side effect.** `PineconeStore.__init__` checks whether the configured index exists and creates it if not — idempotent, cheap (one list-indexes call). Chosen over a separate explicit `ensure_index()` step so the store "just works" the moment it's constructed. This is only comfortable *because* of the `Protocol`: nothing in retrieval/generation code ever constructs a `PineconeStore` directly in tests, they take a `VectorStore` and a test passes a fake — so the network-call-on-construct behavior never leaks into test runs.
- **Deferred (flagged as cuttable, not forgotten):** wrapping Pinecone-specific exceptions in a custom `VectorStoreError` at the boundary. Good practice, genuinely skippable for a 4-day scope — Pinecone's own exceptions propagate for now.

## A live SDK-drift finding, verified rather than assumed

Checked the installed `pinecone` SDK (v10.0.0) instead of relying on training-data memory, and it's changed substantially: there's now a schema-based `pc.indexes.create(schema={...})` API where index fields (`dense_vector`, `sparse_vector`, `string`) are declared explicitly, and `ServerlessSpec` is documented as "deprecated sugar" for it.

Deliberately used the simpler, officially-preserved legacy shim instead (`pc.create_index(name=, dimension=, metric=, spec=ServerlessSpec(cloud=, region=))`) — its docstring confirms it's kept specifically "to ease migration," not scheduled for removal. Our use case is plain dense-vector similarity search with metadata-only fields (text/source/chunk_id don't need schema declaration — Pinecone indexes metadata automatically on first upsert). The schema API's real benefit — hybrid sparse+dense fields, full-text search — is out of scope for this pipeline right now, but is the natural place to look if hybrid search (from the "make this better" list) gets built later.

## Files

- `src/vector_store.py` — `RetrievedChunk`, `VectorStore` Protocol, `PineconeStore` implementation.
- `src/embeddings.py` — added `EMBEDDING_DIM` constant, imported by `vector_store.py` so the Pinecone index dimension and the embedding model's output can't silently drift apart.
