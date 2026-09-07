from unittest.mock import MagicMock

import pytest

from src.chunk import Chunk
from src.vector_store import PineconeStore


def make_fake_pinecone_client(existing_indexes=()):
    client = MagicMock()
    client.list_indexes.return_value.names.return_value = list(existing_indexes)
    return client


@pytest.fixture
def fake_pinecone_client():
    return make_fake_pinecone_client(existing_indexes=["rag-project"])


def build_store(mocker, client) -> PineconeStore:
    mocker.patch("src.vector_store.Pinecone", return_value=client)
    return PineconeStore(api_key="key", index_name="rag-project", cloud="aws", region="us-east-1")


def test_ensure_index_skips_creation_when_index_already_exists(mocker, fake_pinecone_client):
    build_store(mocker, fake_pinecone_client)

    fake_pinecone_client.create_index.assert_not_called()


def test_ensure_index_creates_when_missing(mocker):
    client = make_fake_pinecone_client(existing_indexes=[])

    build_store(mocker, client)

    client.create_index.assert_called_once()
    _, kwargs = client.create_index.call_args
    assert kwargs["name"] == "rag-project"
    assert kwargs["dimension"] == 384
    assert kwargs["metric"] == "cosine"


def test_upsert_builds_vectors_with_correct_id_and_metadata(mocker, fake_pinecone_client):
    store = build_store(mocker, fake_pinecone_client)
    index = fake_pinecone_client.Index.return_value

    chunks = [Chunk("some text", 0, "doc.pdf", 1, 2, embedding=[0.1, 0.2])]
    store.upsert(chunks, namespace="ns")

    index.upsert.assert_called_once()
    _, kwargs = index.upsert.call_args
    assert kwargs["namespace"] == "ns"

    vector = kwargs["vectors"][0]
    assert vector.id == "doc.pdf::0"
    assert vector.values == [0.1, 0.2]
    assert vector.metadata["text"] == "some text"
    assert vector.metadata["source"] == "doc.pdf"
    assert vector.metadata["chunk_id"] == 0
    assert vector.metadata["page_start"] == 1
    assert vector.metadata["page_end"] == 2


def test_query_parses_matches_into_retrieved_chunks(mocker, fake_pinecone_client):
    store = build_store(mocker, fake_pinecone_client)
    index = fake_pinecone_client.Index.return_value

    match = MagicMock()
    match.metadata = {
        "text": "chunk text",
        "source": "doc.pdf",
        "chunk_id": 3,
        "page_start": 5,
        "page_end": 6,
    }
    match.score = 0.87
    index.query.return_value.matches = [match]

    results = store.query([0.1, 0.2], top_k=5, namespace="ns")

    assert len(results) == 1
    result = results[0]
    assert result.text == "chunk text"
    assert result.source == "doc.pdf"
    assert result.chunk_id == 3
    assert result.page_start == 5
    assert result.page_end == 6
    assert result.score == 0.87

    _, kwargs = index.query.call_args
    assert kwargs["top_k"] == 5
    assert kwargs["namespace"] == "ns"
    assert kwargs["include_metadata"] is True
