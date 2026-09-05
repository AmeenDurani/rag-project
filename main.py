import anthropic
import typer

from src.embeddings import embed_chunks
from src.generation import generate
from src.ingestion import chunk_documents, load_documents
from src.retrieval import retrieve
from src.vector_store import PineconeStore

app = typer.Typer()


def _build_store() -> PineconeStore:
    from src.config import settings

    return PineconeStore(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
    )


@app.command()
def ingest(namespace: str = "default") -> None:
    """Load PDFs from data/, chunk, embed, and upsert into Pinecone."""
    documents = load_documents()
    if not documents:
        typer.echo("No PDFs found in data/.")
        raise typer.Exit(code=1)

    all_chunks = []
    for document in documents:
        chunks = chunk_documents(document["text"], document["source"])
        all_chunks.extend(chunks)

    typer.echo(f"Loaded {len(documents)} document(s), {len(all_chunks)} chunk(s). Embedding...")
    embed_chunks(all_chunks)

    store = _build_store()
    store.upsert(all_chunks, namespace=namespace)
    typer.echo(f"Upserted {len(all_chunks)} chunk(s) into namespace '{namespace}'.")


@app.command()
def ask(question: str, namespace: str = "default") -> None:
    """Retrieve relevant chunks and generate an answer to `question`."""
    from src.config import settings

    store = _build_store()
    chunks = retrieve(question, store, top_k=settings.top_k, namespace=namespace)

    if not chunks:
        typer.echo("No relevant chunks found.")
        raise typer.Exit(code=1)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    result = generate(question, chunks, client, model=settings.generation_model)

    typer.echo(f"\n{result.answer}\n")
    typer.echo("Sources:")
    for i, source in enumerate(result.sources, start=1):
        typer.echo(f"  [{i}] {source.source} (chunk {source.chunk_id}, score {source.score:.3f})")
    typer.echo(f"\n(tokens: {result.input_tokens} in / {result.output_tokens} out)")


if __name__ == "__main__":
    app()
