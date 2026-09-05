# Collaboration Rules

How work gets done on this repo, between the project owner and whoever (human or AI) is implementing. These aren't code style rules — see `PROJECT_PLAN.md` for the plan and `progress/` for the build log.

## 1. Explain architecture/design choices before coding them up

Before implementing a non-trivial design decision — a new abstraction, a library choice, an interface boundary, a data structure, a config/error-handling pattern — explain the reasoning and trade-offs first, and make sure it's actually understood, not just stated. Don't silently implement and explain afterward as a recap.

**Why:** this project exists to build both a working system *and* the ability to defend its design decisions in an internship interview. Code that works but isn't understood doesn't serve that goal. "Understood" means the owner can restate the trade-off, not just nod at an explanation.

**Doesn't apply to:** trivial, non-decisional changes (a straightforward rename, an obvious one-line fix) — reserve this for things that reflect a genuine choice among alternatives.

## 2. Be inquisitive — never assume implementation details

When a design or scope question has more than one reasonable answer, ask rather than picking one and moving forward. This includes things that feel small (file naming, folder structure, whether to split one file into several) as much as things that feel large (which library, which architecture pattern).

**Why:** guessed-and-wrong decisions cost more to unwind than a short question would have cost to ask, and this project is explicitly meant to reflect the owner's actual decisions, not defaults picked on their behalf.

## 3. Document after major changes, in `progress/`

After a meaningful unit of work (a refactor, a new integration, a bug fixed and understood, a design decision made), add an entry to `progress/`.

**Convention:**
- One file per topic/change, not per calendar day — e.g. `add-pinecone-vector-store.md`, `fix-chunking-bug-and-batch-embeddings.md`. An entry should be self-contained regardless of when the work happened.
- The folder's own index file is `progress/progress-log-overview.md` — not `README.md`.
- Each entry documents what changed, why, and any trade-offs/alternatives considered — process, not just a feature list.

## 4. Naming: avoid generic names, prefer content-descriptive ones

Don't default to `README.md`/`index.md`/`notes.md` for files whose purpose is to summarize or index something. Name the file after what it actually contains.
