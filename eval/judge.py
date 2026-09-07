import json
import logging
from dataclasses import dataclass

import anthropic

from src.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)

# Binary pass/fail per dimension, not a 1-5 scale: this eval exists to produce
# a before/after comparison (pre/post chunking upgrade), and a finer-grained
# scale is more prone to run-to-run judge-calibration noise that could be
# mistaken for a real quality change. Coarser but more reproducible.
JUDGE_SYSTEM_PROMPT = (
    "You are evaluating one answer produced by a RAG (retrieval-augmented generation) "
    "system. You will be given the question, the exact context chunks that were "
    "retrieved and given to the system, the system's generated answer, and a "
    "human-written reference answer (for context only - not authoritative wording, "
    "the system's own context may phrase things differently).\n\n"
    "Judge two things, each a strict true/false with no partial credit:\n"
    "- faithful: does the answer avoid making any claim that is NOT supported by the "
    "provided context? An answer that correctly declines to answer is always faithful, "
    "since it makes no unsupported claims.\n"
    "- relevant: does the answer actually address what the question asked, on-topic?\n\n"
    "Also report:\n"
    "- refused_to_answer: did the system decline to answer / say it doesn't know, "
    "rather than provide a substantive answer?\n\n"
    "Respond with ONLY a JSON object, no other text: "
    '{"faithful": true|false, "relevant": true|false, "refused_to_answer": true|false}'
)


@dataclass
class JudgeResult:
    faithful: bool
    relevant: bool
    refused_to_answer: bool


def _format_context(retrieved_chunks: list[RetrievedChunk]) -> str:
    entries = [
        f"[{i}] (source: {chunk.source}, pages {chunk.page_start}-{chunk.page_end})\n{chunk.text}"
        for i, chunk in enumerate(retrieved_chunks, start=1)
    ]
    return "\n\n".join(entries)


def _parse_json_response(text: str) -> dict:
    """Strip a markdown code fence if the model wrapped the JSON in one
    despite being told not to - cheap robustness, not a recovery path.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return json.loads(stripped)


def judge_answer(
    question: str,
    generated_answer: str,
    retrieved_chunks: list[RetrievedChunk],
    reference_answer: str,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int = 256,
) -> JudgeResult:
    context = _format_context(retrieved_chunks)
    user_message = (
        f"Question: {question}\n\n"
        f"Retrieved context given to the system:\n{context}\n\n"
        f"System's generated answer:\n{generated_answer}\n\n"
        f"Reference answer (for context only, not authoritative):\n{reference_answer}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        # Sonnet 5 runs adaptive thinking on by default, and thinking tokens
        # count against max_tokens - with a small max_tokens for this
        # classification-only call, the model could occasionally spend the
        # whole budget thinking and leave no room for the JSON text output.
        thinking={"type": "disabled"},
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = next((block.text for block in response.content if block.type == "text"), "")

    try:
        parsed = _parse_json_response(text)
        return JudgeResult(
            faithful=bool(parsed["faithful"]),
            relevant=bool(parsed["relevant"]),
            refused_to_answer=bool(parsed["refused_to_answer"]),
        )
    except (json.JSONDecodeError, KeyError):
        logger.warning("Judge returned unparsable output for query=%r: %r", question, text)
        raise
