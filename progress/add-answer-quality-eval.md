# Add Answer-Quality Eval (LLM-as-Judge)

Milestone #3 of the Day 2 plan: score generated answers for faithfulness, relevance, and correct scope handling, completing the eval harness that milestone #4 (chunking upgrade) needs for a real before/after comparison.

## Binary pass/fail, not a 1-5 scale

Discussed and decided against a finer-grained Likert-style score: the whole point of this eval is diffing two runs (before/after chunking), and a 1-5 scale is more prone to run-to-run judge-calibration drift that could look like a quality change but is actually just judge noise. Binary pass/fail per dimension is coarser per-answer but far more reproducible in aggregate (e.g. "78% faithful, up from 65%"), which is what actually matters for a trustworthy before/after claim in the README.

## `eval/judge.py`

`judge_answer(question, generated_answer, retrieved_chunks, reference_answer, client, model)` — one combined judge call (per the earlier decision to score faithfulness+relevance together rather than as separate calls) returning `JudgeResult(faithful, relevant, refused_to_answer)`.

- **Faithfulness is checked against the actual retrieved context**, not the reference answer — the judge is given the same numbered context chunks that were fed to the generator (`_format_context`, mirroring `generation.py`'s own context formatting but including page numbers instead of chunk IDs). This matches what "faithful" operationally means for this system: no claims unsupported by what the model actually saw. `reference_answer` is passed too, but explicitly labeled non-authoritative — a completeness/relevance aid, not the faithfulness ground truth.
- **`refused_to_answer` is a separate, objective field**, not something the judge is asked to grade as "correct" or "incorrect" itself. The judge only reports what happened (did it decline to answer); Python code (`eval/answer_metrics.py::scope_correct`) combines that with the eval set's known `expected_answerable` to determine whether the refusal (or non-refusal) was actually correct. Keeps subjective judgment (faithful/relevant) separate from a deterministic ground-truth comparison (scope correctness) rather than asking the judge to reason about both at once.
- JSON parsing strips a markdown code fence if the model wraps its output in one, despite being told not to - cheap robustness, not a recovery path; a genuinely malformed response still raises and fails loud.

## `eval/answer_metrics.py`

- `scope_correct(expected_answerable, refused_to_answer)` — correct means: answerable questions get answered (not refused), out-of-scope questions get refused (not hallucinated). Catches both failure directions: hallucinating on an out-of-scope question, *and* wrongly refusing an answerable one (a false-negative refusal, which is just as much a bug as hallucination but easy to overlook).
- `summarize()` reports `scope_accuracy` overall **and** split by `scope_accuracy_answerable` / `scope_accuracy_out_of_scope` separately — a system could handle answerable questions fine while still hallucinating on every out-of-scope one (or vice versa), and a single blended accuracy number would hide that.

## `eval/run_answer_eval.py`

Composition-root runner, same lazy-import pattern as `run_retrieval_eval.py`/`main.py`. Runs the *full* `retrieve` → `generate` → `judge_answer` pipeline for **every** question, including out-of-scope ones (unlike the retrieval-only eval, which skips them since they have no `relevant_pages`). `--judge-model` defaults to `settings.generation_model` if not overridden — same-model judge has a known self-preference bias risk (already flagged in `PROJECT_PLAN.md`'s cons list as a post-4-day mitigation item), not solved here, just left overridable via CLI for whenever that mitigation happens. Writes to `eval/results/<label>_answers.json`, mirroring the `--label` convention from the retrieval eval so both halves of a given run (e.g. `baseline` vs `token_aware_chunking`) stay paired.

## Verified

- Compiles; `--help` succeeds with no `.env`.
- `scope_correct` checked against all four cases by hand (answerable+answered=correct, answerable+refused=incorrect, out-of-scope+refused=correct, out-of-scope+answered=incorrect).
- Markdown-fence-wrapped JSON parses correctly.
- `summarize()` aggregation checked against a small synthetic 2-question set.
- **Not yet run against live Pinecone/Anthropic** — same open blocker as everything since Day 1 (no `.env` / API keys).

## Still open

- Eval harness (milestones #1-3) is now feature-complete but entirely unverified end-to-end. First real run needs both API keys before any actual baseline numbers exist.
- Milestone #4 (token-aware chunking upgrade) is next, and needs a real `baseline` run from both eval scripts to compare against.
