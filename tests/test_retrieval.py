from src.retrieval import retrieve
from tests.conftest import make_retrieved_chunk


def test_retrieve_embeds_query_and_delegates_to_store(mocker, fake_store):
    mocker.patch("src.retrieval.embed_query", return_value=[0.1, 0.2, 0.3])
    fake_store.query_results = [make_retrieved_chunk(chunk_id=1), make_retrieved_chunk(chunk_id=2)]

    results = retrieve("what is x?", fake_store, top_k=2, namespace="ns")

    assert [r.chunk_id for r in results] == [1, 2]
    assert fake_store.last_query["query_embedding"] == [0.1, 0.2, 0.3]
    assert fake_store.last_query["top_k"] == 2
    assert fake_store.last_query["namespace"] == "ns"


def test_retrieve_uses_default_namespace_and_top_k(mocker, fake_store):
    mocker.patch("src.retrieval.embed_query", return_value=[0.0])

    retrieve("q", fake_store)

    assert fake_store.last_query["namespace"] == "default"
    assert fake_store.last_query["top_k"] == 5
