"""Run retrieval (recall@k, MRR) against eval/nasa_handbook_qa_set.json.

Invoke as `python -m eval.run_retrieval_eval` from the repo root - needed
(rather than `python eval/run_retrieval_eval.py`) so both `src.*` and
`eval.*` imports resolve without fiddling with sys.path.

Only expected_answerable=true questions are scored here: out-of-scope
questions have no relevant_pages to hit against, so they'd always register
as a miss for the wrong reason. They're scored later, in the answer-quality
eval, where "correctly said I don't know" is the actual thing being measured.
"""

import json
from pathlib import Path

import typer

from eval.retrieval_metrics import score_question, summarize
from src.retrieval import retrieve

app = typer.Typer()

EVAL_SET_PATH = Path("eval/nasa_handbook_qa_set.json")
RESULTS_DIR = Path("eval/results")


@app.command()
def main(
    namespace: str = "default",
    top_k: int = 5,
    label: str = "baseline",
) -> None:
    """Score retrieval against the eval set and write results to eval/results/<label>.json."""
    from src.config import settings
    from src.vector_store import PineconeStore

    store = PineconeStore(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
    )

    eval_set = json.loads(EVAL_SET_PATH.read_text())
    questions = [q for q in eval_set["questions"] if q["expected_answerable"]]
    skipped = len(eval_set["questions"]) - len(questions)

    scored = []
    for question in questions:
        retrieved = retrieve(question["question"], store, top_k=top_k, namespace=namespace)
        scored.append(score_question(question, retrieved))

    summary = summarize(scored, max_k=top_k)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{label}.json"
    out_path.write_text(json.dumps({"summary": summary, "per_question": scored}, indent=2))

    typer.echo(f"Scored {len(questions)} answerable question(s), skipped {skipped} out-of-scope.")
    typer.echo(json.dumps(summary, indent=2))
    typer.echo(f"\nWrote full results to {out_path}")


if __name__ == "__main__":
    app()
