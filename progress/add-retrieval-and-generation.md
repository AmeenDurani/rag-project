# Add Retrieval & Generation

Added the last two pipeline stages: `src/retrieval.py` and `src/generation.py`. Both written and syntax-checked; not yet run live (no Pinecone/Anthropic API keys available yet — deferred until keys exist, tracked as the actual hard blocker rather than stopping design/implementation work).

## Retrieval (`src/retrieval.py`)

`retrieve(query, store: VectorStore, top_k, namespace)` — embeds the query and delegates to `store.query(...)`. Takes `store` as a parameter rather than constructing a `PineconeStore` internally, for the same reason `VectorStore` was made a `Protocol` in the first place: constructing a real `PineconeStore` triggers a network call (index existence check), so anything that constructs one at import time becomes untestable without live credentials. This established the **composition root** pattern for the rest of the project: only the outermost entry point (the CLI, later the API) reads `settings` and builds concrete objects (`PineconeStore()`, the Anthropic client); every internal module takes what it needs as parameters and stays config-agnostic/testable in isolation.

## Generation (`src/generation.py`)

`generate(query, chunks, client: anthropic.Anthropic, model, max_tokens)` — same dependency-injection pattern as retrieval: takes the Anthropic client as a parameter.

Design decisions:
- **System vs. user message split**: static instructions (answer only from context, say "I don't know" if absent, cite as `[1]`/`[2]`) live in the system prompt since they're identical across every request — the only real candidate for prompt caching later. Retrieved context + the question go in the user message since they vary per query. Caching (`cache_control`) deliberately not turned on yet — the system prompt is well under the minimum cacheable-prefix length (~512-4096 tokens depending on model), so it would be a no-op today; revisit if the system prompt grows or if frequently-repeated chunks become worth caching.
- **Numbered citations built into the context format now** (`[1] (source: ..., chunk N)\n<text>`), even though citation *parsing* is a Day 2 item — deciding the reference scheme now means Day 2 only needs to parse which numbers appear in the answer and map back to `RetrievedChunk`s, not redesign how context is built.
- **`GenerationResult` dataclass** (`answer`, `sources`, `input_tokens`, `output_tokens`) returned instead of a bare string or the raw SDK response — same boundary-translation pattern used for `RetrievedChunk`: downstream code (Day 2 eval scoring, Day 3 cost logging) depends on our shape, not Anthropic's response format. Token counts captured now since they're free to grab off the response and Day 3 wants per-request cost tracking.
- **`max_tokens=1024`**, not the SDK's general-purpose 16k-default recommendation — answers here are grounded, bounded-length responses over a handbook, not open-ended generation.
- **Thinking/effort left unset for now** rather than tuned up front — Sonnet 5 runs adaptive thinking by default regardless. Tuning effort down (cheaper/faster) is exactly the kind of change Day 2's eval harness should justify with a measured quality delta, not a guess made before any evaluation exists.
- **`stop_reason` checked with a log warning, not a full recovery path** — flags truncation or (very unlikely here) a safety refusal without building retry/recovery logic, which is out of scope for a 4-day build.
- Verified `anthropic.types.Usage`'s actual field names (`input_tokens`, `output_tokens`) against the installed SDK before using them, rather than assuming from memory — consistent with the Pinecone SDK-drift check earlier in the project.

## Still open

- `main.py` CLI wiring (the composition root itself) — the last piece of naive RAG.
- Nothing in this entry has been run against live Pinecone/Anthropic - `.env` still needs real API keys before any of this can be verified end-to-end.
