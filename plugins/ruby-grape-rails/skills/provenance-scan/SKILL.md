---
name: rb:provenance-scan
description: "Use when auditing existing research/review `*.provenance.md` sidecars under `.claude/`. Classifies each by `trust_state` (clean / weak / conflicted / missing) and writes a dated Markdown report of the distribution and per-file breakdown."
when_to_use: "Triggers: \"scan provenance\", \"audit research quality\", \"check trust states\", \"provenance distribution\", \"how clean is my research\". Pure post-hoc analysis of artifacts already on disk; no model calls, no network. Does NOT handle: producing sidecars (use `/rb:research` / `/rb:review`), fixing weak claims (re-run the producing skill), grading code or factual accuracy of claims."
argument-hint: "[--root PATH]"
effort: low
user-invocable: true
---

# Provenance Scan

Self-audit for the project's research and review provenance sidecars.
Outputs a per-state count plus a per-file list so the user can decide
whether upcoming `/rb:plan --existing`, `/rb:work`, or `/rb:review`
runs are relying on solid evidence or single-source claims.

Schema reference:

- `${CLAUDE_PLUGIN_ROOT}/references/output-verification/trust-states.md`
- `${CLAUDE_PLUGIN_ROOT}/references/output-verification/provenance-template.md`

## Iron Laws

1. **Never invent or edit claims, sources, or conflicts to change a
   state.** A `weak` / `missing` state is a diagnostic; rewriting the
   sidecar to silence it defeats every workflow that reads
   `trust_state`. If a state is wrong, fix the underlying research,
   not the sidecar.
2. **Never auto-fix sidecars.** Remediation belongs to the producing
   skill (`/rb:research`, `/rb:review`). This skill reports only.
3. **Never re-use a stale report.** If any `*.provenance.md` changed
   since the last run, re-run the scan before acting on it.
4. **Read only the sidecar frontmatter, not the raw artifact alongside
   each `.provenance.md`.** The scan reports on evidence shape, not on
   the artifact's content. Pulling the raw body into the report
   bloats it without changing the trust-state classification, and any
   subsequent modify-the-artifact follow-up is out of scope (Iron
   Law #2 covers auto-fix prohibition).
5. **`weak` is not a blocker; `conflicted` is.** Only `conflicted`
   should halt a downstream `/rb:plan --existing` or `/rb:work` step.
   `weak` and `missing` warn but proceed.

## How to run

```
${CLAUDE_PLUGIN_ROOT}/bin/provenance-scan
```

Optional `--root PATH` points at a project other than the current
directory. Exit code is `0` whether the distribution is all-clean or
all-conflicted — the report file is the contract, not the exit code.

## Where it looks

- `.claude/research/**/*.provenance.md`
- `.claude/reviews/**/*.provenance.md`
- `.claude/audit/**/*.provenance.md`
- `.claude/plans/<slug>/{research,reviews}/**/*.provenance.md`

## State meanings

- `clean` — every claim has ≥2 independent sources, no conflicts
- `weak` — at least one claim single-sourced, or every source is
  `tool-output` (no primary / secondary evidence)
- `conflicted` — sources disagree on a claim (`conflicts:` list
  non-empty)
- `missing` — no frontmatter, malformed YAML, or off-spec schema

## Reading the report

Report path: `.claude/provenance-scan/report-<YYYY-MM-DD>.md`.

- `## Distribution` — count per state across the scanned tree.
- `## Per-file` — every sidecar with its state, ordered with
  `conflicted` first, then `missing`, `weak`, and `clean` last so the
  most urgent entries are at the top.

## Acting on results

- `conflicted > 0` → resolve before any `/rb:plan --existing` cites
  the affected research. Pull the sidecar's `conflicts[]` list, decide
  which source wins, re-run `/rb:research`.
- `missing > 0` → either the schema is malformed or the artifact lacks
  a sidecar entirely. Re-author the sidecar from
  `provenance-template.md`.
- `weak > 0` → tolerated but tracked. Re-run `/rb:research` for any
  claim that is decisive for an upcoming `/rb:plan` or `/rb:review`.
- `clean` only → no action required.

## Privacy

The report stays local. There is no upload, share-back, or telemetry
mode. If a finding is worth filing upstream, the user copies the
report manually.

## What it does NOT do

- Does NOT verify the **factual accuracy** of claims — only the schema
  and source-structure shape. A sidecar can be `clean` and still wrong
  about the world.
- Does NOT garbage-collect old report files. The user owns
  `.claude/provenance-scan/`.
