"""Run answer-quality eval (LLM-as-judge: faithfulness, relevance, scope
handling) against eval/nasa_handbook_qa_set.json.

Invoke as `python -m eval.run_answer_eval` from the repo root, same reason
as run_retrieval_eval.py - both `src.*` and `eval.*` imports need the repo
root on sys.path, which direct script execution wouldn't give.

Unlike run_retrieval_eval.py, every question is scored here, including
out-of-scope ones: "did it correctly refuse instead of hallucinate" is
exactly what this eval measures for those, which recall@k/MRR can't.
"""

import json
from pathlib import Path

import anthropic
import typer

from eval.answer_metrics import score_question, summarize
from eval.judge import judge_answer
from src.generation import generate
from src.retrieval import retrieve

app = typer.Typer()

EVAL_SET_PATH = Path("eval/nasa_handbook_qa_set.json")
RESULTS_DIR = Path("eval/results")


@app.command()
def main(
    namespace: str = "default",
    top_k: int = 5,
    label: str = "baseline",
    judge_model: str = typer.Option(
        None, help="Judge model to use. Defaults to settings.generation_model if unset."
    ),
) -> None:
    """Run retrieve -> generate -> judge for every eval question, write results
    to eval/results/<label>_answers.json.
    """
    from src.config import settings
    from src.vector_store import PineconeStore

    store = PineconeStore(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    judge_model = judge_model or settings.generation_model

    eval_set = json.loads(EVAL_SET_PATH.read_text())
    questions = eval_set["questions"]

    scored = []
    for question in questions:
        retrieved = retrieve(question["question"], store, top_k=top_k, namespace=namespace)
        result = generate(question["question"], retrieved, client, model=settings.generation_model)
        judged = judge_answer(
            question["question"],
            result.answer,
            retrieved,
            question["reference_answer"],
            client,
            model=judge_model,
        )
        scored.append(score_question(question, result.answer, judged))

    summary = summarize(scored)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{label}_answers.json"
    out_path.write_text(json.dumps({"summary": summary, "per_question": scored}, indent=2))

    typer.echo(f"Scored {len(questions)} question(s).")
    typer.echo(json.dumps(summary, indent=2))
    typer.echo(f"\nWrote full results to {out_path}")


if __name__ == "__main__":
    app()
