# Add Technical Whitepaper (Hosted), Rewrite README as a Landing Page

Mid-Day-4 scope change (`PROJECT_PLAN.md`). Original Day 4 plan had README carry
architecture, design decisions, and the eval table directly. Decided instead to
split: README stays setup-only, and a separate hosted whitepaper carries the deep
technical narrative with real charts - explicitly to stress design-decision
reasoning and eval-driven iteration for an ML engineering internship audience,
per direct request.

## Design decisions made explicitly before coding

Three genuine forks, discussed and decided before writing any content:

1. **Plain static HTML/CSS, no build tooling** (not Astro, not Next.js). The
   audience cares about the eval story and design reasoning, not the frontend
   stack - a build toolchain would be scope creep relative to what a
   long-form document with charts actually needs. Trade-off named explicitly:
   less structure/reuse than a framework would give for multi-page docs, but
   this is one page.
2. **Subdirectory in this repo** (`whitepaper/`), not a separate repo - one
   source of truth, Vercel points at it via "Root Directory" in project
   settings. Keeps the whitepaper's numbers trivially in sync with
   `eval/results/*.json` since both live in the same checkout.
3. **README becomes a short landing page** (setup/run/Docker instructions, CI
   badge, a link out) rather than a full duplicate of the whitepaper's
   content - avoids maintaining the same design-decisions narrative in two
   places that could drift out of sync.

A fourth, revisited mid-conversation: the architecture diagram was originally
scoped as ASCII (matching the plain-README decision from earlier in Day 4).
Once the destination became a designed, hosted page rather than a
GitHub-rendered README, re-decided in favor of an actual rendered SVG diagram -
ASCII would have looked out of place next to real charts elsewhere on the page.

## Content: not invented, pulled from source

Every number in the whitepaper was pulled directly from
`eval/results/{baseline,small_chunks,token_aware}.json` and
`eval/results/*_answers.json` - not paraphrased from the progress docs'
prose summaries. This surfaced one thing more precisely than the prose ever
stated: the three answerable questions that fail scope accuracy after the
token-aware fix (q08/q09/q10) all ground-truth to pages 15-16, and their
`retrieved` chunk page-spans in `token_aware.json` (3, 14-15, 16-17, 17-18, 20)
confirm the fragmentation mechanism directly, rather than inferring it. Also
pulled the exact smaller-chunk-experiment parameters (`chunk_size=150,
overlap=15`, not the `~250` guessed initially) from
`experiment-smaller-chunk-size.md` before writing the comparison table, and the
per-question detail on q12 (AS9100 dilution failure, `first_hit_rank: null` in
`small_chunks.json` vs. rank 1 in `baseline.json`) confirming the "smaller isn't
strictly more precise" claim rather than asserting it from memory.

## Charts: built to the dataviz skill's spec, not eyeballed

Two grouped bar charts (retrieval metrics and answer-quality metrics, each
across the three chunking iterations), hand-rolled in SVG (`whitepaper/js/charts.js`)
rather than a charting library, to get exact control over the skill's mark
specs (4px rounded top / square baseline, capped bar width, a hover/focus
tooltip per bar, a table-view toggle as the WCAG-clean twin of each chart).

- **Palette validated, not assumed.** Ran `validate_palette.js` against both
  the 4-slot subset (retrieval chart: blue/orange/aqua/yellow) and the 3-slot
  subset (quality chart: blue/orange/aqua) of the documented default palette.
  Both pass every hard check; both get a WARN on contrast-vs-surface for the
  aqua/yellow slots (expected, documented in `palette.md`) - the relief rule
  applies, satisfied by shipping mandatory direct labels *and* a table-view
  toggle on every chart, not just one.
- **A real label-collision bug was found and fixed by actually looking at the
  render**, not just reading the code. The first version stacked a direct
  label per bar; wherever two adjacent bars in a group rounded to the same
  displayed value (e.g. Recall@3 and Recall@5 both at 94.4% in the
  "Smaller chunks" group), their labels overlapped into an illegible merged
  string. Worse, a first attempted fix (stack colliding labels upward,
  cumulatively) overflowed into the legend row above the chart when three
  series tied at once (Faithfulness/Relevance/Scope accuracy all at 100% in
  the Baseline group). Final fix: detect runs of consecutive bars with an
  identical rendered label and draw exactly one shared label centered over
  the run, instead of one label per bar or an unbounded stack.
- **Colors are literal hex in `js/init.js`**, not `fill="var(--series-1)"` -
  SVG presentation attributes don't reliably resolve CSS custom properties the
  way a `style` declaration would; using the literal values (matching
  `css/style.css`'s tokens exactly, noted in a comment) avoided a
  cross-browser gamble rather than discovering it later.
- **Dark mode explicitly out of scope**, not silently missing. The dataviz
  skill treats dark mode as a selected, separately-validated mode, not an
  automatic `prefers-color-scheme` flip - implementing it properly for two
  charts on a single content page was judged disproportionate to this
  project's scope, so the page ships one fixed, validated light theme only.

## Verified with a headless browser, not just read back

Playwright (Chromium) wasn't installed; installed it, served `whitepaper/`
locally, and actually exercised the page rather than trusting the source:

- Bar counts match expectations (12 bars in the 4-series retrieval chart, 9 in
  the 3-series quality chart), legend key counts correct, zero console errors.
- Hovering a bar produces the correct tooltip content (value + series +
  category); clicking "View as table" reveals an accessible table with the
  right row count; clicking a TOC anchor actually scrolls the page.
- Full-page and per-component screenshots at desktop (1280px) and mobile
  (390px) widths, inspected directly - this is what caught the label-collision
  bug above; it would not have been visible from reading the SVG-generation
  code alone.
- Re-verified after each fix (initial stacked-label attempt, then the
  run-collapsing fix) rather than assuming the second attempt worked.

## Deployed

Live at `https://rag-project-tawny.vercel.app/` (repo owner connected the
GitHub repo via the Vercel dashboard with Root Directory = `whitepaper`, no
build command - exactly the zero-config path `vercel.json` was prepared for).
Re-verified everything against the live URL with the same Playwright checks
run against the local copy - correct bar/legend counts (12 and 9 bars), a
working hover tooltip with correct content, the table-view toggle, and zero
console errors - rather than assuming a successful local render implies a
successful deployment. README's whitepaper link updated from the
`YOUR-VERCEL-PROJECT.vercel.app` placeholder to the real URL.

## Not done yet

Stretch UI is the only remaining Day 4 item after this.
