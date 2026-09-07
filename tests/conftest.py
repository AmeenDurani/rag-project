"""Shared test fixtures and fakes.

Two design choices worth naming (see progress/ for the full discussion):
- chunk_documents()/embed_*() take injectable dependencies (tokenizer,
  fastembed model) the same way retrieve() takes `store` - so tests never
  need to download or load the real embedding model.
- Fixture PDFs are built via pypdf's own writer object model rather than a
  rendering library - no new dependency just for test fixtures, and pypdf's
  writer handles xref/trailer bookkeeping so this doesn't need hand-computed
  byte offsets.
"""

import os

# src/config.py::Settings() is instantiated at import time and fails fast if
# real API keys aren't set - correct for production, but it means importing
# any module that transitively imports src.config (including src.api) would
# break in an environment with no real .env (e.g. CI) even though the tests
# below never make a real API call. setdefault only fills gaps, so a real
# .env (as in local dev right now) still loses to nothing - os.environ always
# wins over .env in pydantic-settings' precedence, so this guarantees the
# test suite never actually depends on real secrets, without touching a real
# environment that already has them. Must run before any src.* import below.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")

import io
from dataclasses import dataclass, field

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing

from src.vector_store import RetrievedChunk


def make_test_pdf(pages_text: list[str]) -> bytes:
    """Build a minimal real PDF with extractable text, one page per string."""
    writer = PdfWriter()

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font)

    for text in pages_text:
        page = writer.add_blank_page(width=400, height=400)

        resources = DictionaryObject()
        font_dict = DictionaryObject()
        font_dict[NameObject("/F1")] = font_ref
        resources[NameObject("/Font")] = font_dict
        page[NameObject("/Resources")] = resources

        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = DecodedStreamObject()
        content.set_data(f"BT /F1 12 Tf 20 300 Td ({escaped}) Tj ET".encode("latin-1"))
        content_ref = writer._add_object(content)
        page[NameObject("/Contents")] = content_ref

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_test_tokenizer() -> Tokenizer:
    """A tiny real tokenizer: one token per whitespace-separated word, plus
    [CLS]/[SEP]. Fast, no model download, but a real tokenizers.Tokenizer -
    it satisfies the exact interface chunk_documents() depends on (encode()
    returning offsets + special_tokens_mask, to_str()/from_str(),
    no_truncation()) without reimplementing that behavior in a hand-rolled
    fake.
    """
    vocab = {"[UNK]": 0, "[CLS]": 1, "[SEP]": 2}
    tokenizer = Tokenizer(WordLevel(vocab=vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]",
        special_tokens=[("[CLS]", 1), ("[SEP]", 2)],
    )
    return tokenizer


@pytest.fixture
def test_tokenizer() -> Tokenizer:
    return make_test_tokenizer()


@pytest.fixture
def test_pdf_bytes():
    return make_test_pdf


class FakeVectorStore:
    """In-memory VectorStore Protocol implementation for tests.

    query() returns pre-configured canned results rather than doing real
    similarity search - this fake exists to test the *glue* (retrieve(),
    API routes), not retrieval quality, which is what the eval harness is
    for.
    """

    def __init__(self, query_results: list[RetrievedChunk] | None = None):
        self.upserted: list[tuple[list, str]] = []
        self.query_results = query_results or []
        self.last_query: dict | None = None

    def upsert(self, chunks, namespace: str = "default") -> None:
        self.upserted.append((chunks, namespace))

    def query(self, query_embedding, top_k: int = 5, namespace: str = "default"):
        self.last_query = {
            "query_embedding": query_embedding,
            "top_k": top_k,
            "namespace": namespace,
        }
        return self.query_results[:top_k]


@pytest.fixture
def fake_store() -> FakeVectorStore:
    return FakeVectorStore()


def make_retrieved_chunk(
    source: str = "doc.pdf",
    chunk_id: int = 0,
    page_start: int = 1,
    page_end: int = 1,
    score: float = 0.9,
    text: str = "some chunk text",
) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        source=source,
        chunk_id=chunk_id,
        page_start=page_start,
        page_end=page_end,
        score=score,
    )


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeUsage:
    input_tokens: int = 10
    output_tokens: int = 5


@dataclass
class FakeMessage:
    content: list = field(default_factory=lambda: [FakeTextBlock("a fake answer")])
    stop_reason: str = "end_turn"
    usage: FakeUsage = field(default_factory=FakeUsage)


class FakeMessages:
    def __init__(self, response: FakeMessage):
        self.response = response
        self.last_call_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        return self.response


class FakeAnthropicClient:
    """Stand-in for anthropic.Anthropic - only implements .messages.create(),
    the only surface generate()/judge_answer() actually call.
    """

    def __init__(self, response: FakeMessage | None = None):
        self.messages = FakeMessages(response or FakeMessage())


@pytest.fixture
def fake_anthropic_client() -> FakeAnthropicClient:
    return FakeAnthropicClient()
