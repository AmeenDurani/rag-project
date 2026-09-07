"""API tests patch what dependencies.lifespan() constructs (PineconeStore,
anthropic.Anthropic) rather than using FastAPI's dependency_overrides -
overrides only replace Depends() callables, but lifespan runs unconditionally
on every TestClient startup and would otherwise try to build a real
PineconeStore (a real list_indexes() call) before any override took effect.
Patching the constructors lifespan calls means get_store()/get_anthropic_client()
naturally return the fakes via app.state, with no other code path changed.
"""

from fastapi.testclient import TestClient

from tests.conftest import FakeMessage, FakeTextBlock, make_retrieved_chunk


def make_client(mocker, fake_store, fake_anthropic_client) -> TestClient:
    mocker.patch("src.api.dependencies.PineconeStore", return_value=fake_store)
    mocker.patch("src.api.dependencies.anthropic.Anthropic", return_value=fake_anthropic_client)

    from src.api import app

    return TestClient(app)


def test_health(mocker, fake_store, fake_anthropic_client):
    client = make_client(mocker, fake_store, fake_anthropic_client)

    with client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_returns_answer_and_sources(mocker, fake_store, fake_anthropic_client):
    fake_store.query_results = [make_retrieved_chunk(source="doc.pdf", chunk_id=0, score=0.9)]
    fake_anthropic_client.messages.response = FakeMessage(content=[FakeTextBlock("the answer")])
    client = make_client(mocker, fake_store, fake_anthropic_client)

    with client:
        response = client.post("/query", json={"question": "what is x?", "namespace": "ns"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "the answer"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["source"] == "doc.pdf"
    assert fake_store.last_query["namespace"] == "ns"


def test_query_returns_404_when_no_chunks_retrieved(mocker, fake_store, fake_anthropic_client):
    fake_store.query_results = []
    client = make_client(mocker, fake_store, fake_anthropic_client)

    with client:
        response = client.post("/query", json={"question": "anything", "namespace": "empty"})

    assert response.status_code == 404


def _fake_embed_chunks(chunks, batch_size: int = 32):
    for c in chunks:
        c.embedding = [0.0] * 384
    return chunks


def test_ingest_persists_upload_and_returns_chunk_count(
    mocker, fake_store, fake_anthropic_client, test_pdf_bytes, test_tokenizer, tmp_path
):
    mocker.patch("src.api.routes.DATA_DIR", tmp_path)
    # /ingest doesn't pass a tokenizer explicitly, so chunk_documents() falls
    # back to get_tokenizer() (the real, slow-to-load model) - patch it at
    # its point of use in src.ingestion so the fake tokenizer is used instead.
    mocker.patch("src.ingestion.get_tokenizer", return_value=test_tokenizer)
    # embed_chunks() would otherwise load the real fastembed model too.
    mocker.patch("src.api.routes.embed_chunks", side_effect=_fake_embed_chunks)
    client = make_client(mocker, fake_store, fake_anthropic_client)

    pdf_bytes = test_pdf_bytes(["one two three four five six seven eight nine ten"])

    with client:
        response = client.post(
            "/ingest",
            params={"namespace": "ns", "chunk_size": 4, "overlap": 1},
            files=[("files", ("doc.pdf", pdf_bytes, "application/pdf"))],
        )

    assert response.status_code == 200
    body = response.json()
    assert body["documents"] == 1
    assert body["namespace"] == "ns"
    assert body["chunks"] > 0
    assert (tmp_path / "doc.pdf").exists()
    assert len(fake_store.upserted) == 1


def test_ingest_rejects_non_pdf_content_type(mocker, fake_store, fake_anthropic_client, tmp_path):
    mocker.patch("src.api.routes.DATA_DIR", tmp_path)
    client = make_client(mocker, fake_store, fake_anthropic_client)

    with client:
        response = client.post(
            "/ingest",
            files=[("files", ("not_a_pdf.txt", b"hello", "text/plain"))],
        )

    assert response.status_code == 415
