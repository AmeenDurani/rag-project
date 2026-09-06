from eval.judge import JudgeResult


def scope_correct(expected_answerable: bool, refused_to_answer: bool) -> bool:
    """Correct scope handling means: answerable questions get answered
    (not refused), out-of-scope questions get refused (not hallucinated).
    """
    return refused_to_answer == (not expected_answerable)


def score_question(question: dict, generated_answer: str, judge_result: JudgeResult) -> dict:
    return {
        "id": question["id"],
        "question": question["question"],
        "expected_answerable": question["expected_answerable"],
        "generated_answer": generated_answer,
        "faithful": judge_result.faithful,
        "relevant": judge_result.relevant,
        "refused_to_answer": judge_result.refused_to_answer,
        "scope_correct": scope_correct(question["expected_answerable"], judge_result.refused_to_answer),
    }


def _rate(key: str, pool: list[dict]) -> float | None:
    if not pool:
        return None
    return sum(1 for q in pool if q[key]) / len(pool)


def summarize(scored_questions: list[dict]) -> dict:
    answerable = [q for q in scored_questions if q["expected_answerable"]]
    out_of_scope = [q for q in scored_questions if not q["expected_answerable"]]

    return {
        "num_questions": len(scored_questions),
        "faithfulness_rate": _rate("faithful", scored_questions),
        "relevance_rate": _rate("relevant", scored_questions),
        "scope_accuracy": _rate("scope_correct", scored_questions),
        "scope_accuracy_answerable": _rate("scope_correct", answerable),
        "scope_accuracy_out_of_scope": _rate("scope_correct", out_of_scope),
    }
