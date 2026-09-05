import logging
from dataclasses import dataclass

import anthropic

from src.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using only the provided "
    "context. If the context does not contain the answer, say you don't know - "
    "do not use outside knowledge. Cite the context you use with bracketed "
    "numbers like [1], [2], matching the numbered context entries."
)


@dataclass
class GenerationResult:
    answer: str
    sources: list[RetrievedChunk]
    input_tokens: int
    output_tokens: int


def _format_context(chunks: list[RetrievedChunk]) -> str:
    entries = [
        f"[{i}] (source: {chunk.source}, chunk {chunk.chunk_id})\n{chunk.text}"
        for i, chunk in enumerate(chunks, start=1)
    ]
    return "\n\n".join(entries)


def generate(
    query: str,
    chunks: list[RetrievedChunk],
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int = 1024,
) -> GenerationResult:
    context = _format_context(chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    if response.stop_reason != "end_turn":
        logger.warning("Unexpected stop_reason=%s for query=%r", response.stop_reason, query)

    answer = next((block.text for block in response.content if block.type == "text"), "")

    return GenerationResult(
        answer=answer,
        sources=chunks,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
