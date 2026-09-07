# Fix: Judge Eval Crashed When Claude Sonnet 5's Thinking Ate the Whole `max_tokens` Budget

Found while running the answer-quality eval for `token-aware-chunking-and-truncation-fix.md` - unrelated to chunking itself, a pre-existing bug in the eval harness that happened to get triggered during that run.

## What happened

`eval/run_answer_eval.py` crashed with a `JSONDecodeError` from `eval/judge.py::_parse_json_response` - the judge call returned an empty string instead of the expected `{"faithful": ..., "relevant": ..., "refused_to_answer": ...}` JSON.

## Diagnosis

Reproduced the exact call in isolation repeatedly rather than assuming it was transient. It wasn't consistent - most attempts returned valid JSON, but one attempt returned `stop_reason: "max_tokens"` with a single `thinking` content block and no `text` block at all. Checked against the Claude API reference: Claude Sonnet 5 runs adaptive thinking on by default even without requesting it, and thinking tokens count against `max_tokens`. `judge_answer()` calls with `max_tokens=256`, sized for a short JSON classification response - on the calls where the model decided to think first, thinking consumed the entire 256-token budget, leaving zero tokens for the actual answer.

## Fix

Added `thinking={"type": "disabled"}` to the `client.messages.create()` call in `eval/judge.py::judge_answer()`. Confirmed via the Claude API reference this is safe specifically for Sonnet 5 (unlike Opus 5, where disabling thinking has two documented failure modes - occasionally writing a tool call into visible text, or leaking thinking tags - neither of which applies to Sonnet 5, and this call doesn't use tools). This is a strict binary classification task with no need for reasoning depth, so disabling thinking is a correctness fix, not a quality trade-off.

## Verified

Re-ran the answer-quality eval after the fix; completed cleanly with no unparsable-output warnings.
