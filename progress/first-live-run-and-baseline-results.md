# First Live Run: End-to-End Verification and Baseline Eval Results

Every prior entry since Day 1 has been "code-complete, unverified end-to-end" — this is the session where API keys finally existed and the whole pipeline ran against real Pinecone/Anthropic for the first time.

## What ran, in order

1. `python main.py ingest` — loaded the NASA handbook PDF, produced 16 chunks, embedded and upserted them into Pinecone. Succeeded on the first attempt, no bugs surfaced.
2. `python main.py ask "..."` — one manual sanity question, to see a real answer before spending eval-set API calls. Correct answer, properly cited, matched expectations.
3. `python -m eval.run_retrieval_eval --label baseline` — scored all 18 answerable questions.
4. `python -m eval.run_answer_eval --label baseline` — scored all 22 questions (including out-of-scope) through the full retrieve → generate → judge pipeline.

No bugs found in any of the eval harness code written across the last several sessions - the offline/synthetic verification done at each step (chunking math, scope_correct logic, JSON-fence parsing) held up against the real thing.

## Results

**Retrieval** (`eval/results/baseline.json`):
- recall@1: 0.778
- recall@3: 0.944
- recall@5: 1.0
- MRR: 0.863

**Answer quality** (`eval/results/baseline_answers.json`):
- faithfulness_rate: 1.0
- relevance_rate: 1.0
- scope_accuracy: 1.0 (both the answerable and out-of-scope subsets individually)

## Why the perfect answer-quality scores were treated as suspicious, not just accepted

A judge eval that returns 100% on every dimension is exactly the shape a broken/rubber-stamping judge would also produce - a judge always returning `true` looks identical in the aggregate. Before trusting the summary, manually inspected the underlying per-question records for the four out-of-scope questions (`eval/results/baseline_answers.json::per_question`), especially the two adversarial ones (oos02: Technical Risk Management steps from Section 6.4; oos04: HSI domains from Section 2.6) that were specifically designed to tempt hallucination by naming real section numbers the model could see referenced in the table of contents.

In both adversarial cases, the model's retrieved context included TOC-adjacent fragments (figure names like "Risk Scenario Development," headings like "HSI Domains") but it correctly declined to fabricate the actual section content those names hint at, instead stating the context doesn't contain it. Also spot-checked three multi-page answerable questions (q08-q10, the process-list questions spanning two pages) against their reference answers - all three matched exactly. This is a small, 20-page corpus with well-scoped questions, so a genuinely perfect score is plausible here; the point of the spot-check wasn't to distrust the result by default, but to not take an eval's own self-report at face value before relying on it for a future before/after comparison.

## Housekeeping fixed alongside this

- Removed a stale `eval_results/` entry from `.gitignore` (dead - didn't match the actual `eval/results/` path used by the eval scripts). `eval/results/*.json` is committed intentionally, to preserve the before/after comparison trail for milestone 4.

## Status

Day 1 and Day 2 milestones 1-3 are now genuinely verified end-to-end, not just code-complete. This `baseline` result is what milestone 4 (token-aware chunking upgrade) will tune against and compare to.
