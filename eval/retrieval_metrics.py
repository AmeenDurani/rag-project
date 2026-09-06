from src.vector_store import RetrievedChunk


def chunk_hits_pages(chunk: RetrievedChunk, relevant_pages: list[int]) -> bool:
    """A retrieved chunk counts as relevant if its page range overlaps any
    labeled page - not just full containment. Matches the ground-truth design:
    page numbers are stable across chunking runs, chunk boundaries aren't.
    """
    chunk_pages = set(range(chunk.page_start, chunk.page_end + 1))
    return bool(chunk_pages & set(relevant_pages))


def first_hit_rank(retrieved: list[RetrievedChunk], relevant_pages: list[int]) -> int | None:
    """1-indexed rank of the first retrieved chunk that hits, or None if none did."""
    for rank, chunk in enumerate(retrieved, start=1):
        if chunk_hits_pages(chunk, relevant_pages):
            return rank
    return None


def score_question(question: dict, retrieved: list[RetrievedChunk]) -> dict:
    """Per-question detail record, kept alongside the aggregate metrics so a
    failing question can be inspected directly rather than re-run.
    """
    rank = first_hit_rank(retrieved, question["relevant_pages"])
    return {
        "id": question["id"],
        "question": question["question"],
        "relevant_pages": question["relevant_pages"],
        "first_hit_rank": rank,
        "retrieved": [
            {
                "source": chunk.source,
                "chunk_id": chunk.chunk_id,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "score": chunk.score,
            }
            for chunk in retrieved
        ],
    }


def recall_at_k(scored_questions: list[dict], k: int) -> float:
    if not scored_questions:
        return 0.0
    hits = sum(
        1
        for q in scored_questions
        if q["first_hit_rank"] is not None and q["first_hit_rank"] <= k
    )
    return hits / len(scored_questions)


def mrr(scored_questions: list[dict]) -> float:
    if not scored_questions:
        return 0.0
    reciprocal_ranks = [
        1 / q["first_hit_rank"] if q["first_hit_rank"] else 0.0 for q in scored_questions
    ]
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def summarize(scored_questions: list[dict], max_k: int) -> dict:
    """recall@k for k in {1, 3, max_k} (deduped, capped at max_k) computed
    from the same top-max_k retrieval - no need to re-query per k since
    first_hit_rank <= k is equivalent to only looking at the top k results.
    """
    ks = sorted({k for k in (1, 3, max_k) if k <= max_k})
    return {
        "num_questions": len(scored_questions),
        **{f"recall@{k}": recall_at_k(scored_questions, k) for k in ks},
        "mrr": mrr(scored_questions),
    }
