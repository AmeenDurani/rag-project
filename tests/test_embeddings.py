import numpy as np
import pytest

from src import embeddings as embeddings_module
from src.chunk import Chunk


class FakeEmbeddingModel:
    """Stand-in for fastembed.TextEmbedding - .embed() is the only surface
    embed_texts()/embed_chunks() actually call. Yields numpy arrays (not
    plain lists) since embed_texts() calls .tolist() on each result, same as
    the real fastembed model's output type.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.embed_calls: list[dict] = []

    def embed(self, texts, batch_size: int = 32):
        texts = list(texts)
        self.embed_calls.append({"texts": texts, "batch_size": batch_size})
        for _ in texts:
            yield np.zeros(self.dim)


@pytest.fixture(autouse=True)
def reset_embedding_singleton():
    """embed_texts()/embed_chunks() lazily cache the loaded model at module
    scope - reset it around every test so each test's mock actually gets
    exercised instead of a previous test's cached (real or fake) instance.
    """
    embeddings_module._model = None
    yield
    embeddings_module._model = None


def test_embed_texts_returns_one_vector_per_input_and_passes_batch_size(mocker):
    fake_model = FakeEmbeddingModel()
    mocker.patch.object(embeddings_module, "TextEmbedding", return_value=fake_model)

    result = embeddings_module.embed_texts(["a", "b", "c"], batch_size=2)

    assert len(result) == 3
    assert all(len(vec) == 384 for vec in result)
    assert fake_model.embed_calls[0]["batch_size"] == 2
    assert fake_model.embed_calls[0]["texts"] == ["a", "b", "c"]


def test_embed_chunks_assigns_embeddings_back_to_correct_chunks(mocker):
    fake_model = FakeEmbeddingModel()
    mocker.patch.object(embeddings_module, "TextEmbedding", return_value=fake_model)

    chunks = [Chunk(f"text {i}", i, "doc.pdf", 1, 1) for i in range(3)]

    result = embeddings_module.embed_chunks(chunks, batch_size=32)

    assert result is chunks
    assert all(c.embedding is not None for c in chunks)
    assert fake_model.embed_calls[0]["texts"] == ["text 0", "text 1", "text 2"]


def test_model_is_loaded_once_across_multiple_calls(mocker):
    ctor = mocker.patch.object(
        embeddings_module, "TextEmbedding", return_value=FakeEmbeddingModel()
    )

    embeddings_module.embed_texts(["a"])
    embeddings_module.embed_texts(["b"])

    ctor.assert_called_once()
