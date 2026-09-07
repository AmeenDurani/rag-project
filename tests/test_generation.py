from src.generation import generate
from tests.conftest import (
    FakeAnthropicClient,
    FakeMessage,
    FakeTextBlock,
    FakeUsage,
    make_retrieved_chunk,
)


def test_generate_formats_context_and_returns_answer():
    client = FakeAnthropicClient(
        FakeMessage(
            content=[FakeTextBlock("the answer")],
            usage=FakeUsage(input_tokens=100, output_tokens=20),
        )
    )
    chunks = [make_retrieved_chunk(source="doc.pdf", chunk_id=0, text="chunk one text")]

    result = generate("what is x?", chunks, client, model="claude-sonnet-5")

    assert result.answer == "the answer"
    assert result.sources == chunks
    assert result.input_tokens == 100
    assert result.output_tokens == 20

    call_kwargs = client.messages.last_call_kwargs
    assert call_kwargs["model"] == "claude-sonnet-5"
    assert "chunk one text" in call_kwargs["messages"][0]["content"]
    assert "what is x?" in call_kwargs["messages"][0]["content"]


def test_generate_returns_empty_answer_when_no_text_block_present(caplog):
    # simulates the thinking-ate-the-budget failure mode diagnosed in
    # progress/fix-judge-thinking-token-budget-bug.md - no text block at all
    client = FakeAnthropicClient(FakeMessage(content=[], stop_reason="max_tokens"))
    chunks = [make_retrieved_chunk()]

    result = generate("q", chunks, client, model="claude-sonnet-5")

    assert result.answer == ""
