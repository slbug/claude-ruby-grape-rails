---
name: session-scan
description: Compute exploratory metrics for recent Claude sessions. Use for broad session triage, provider-scoped scans, and identifying transcripts worth deeper review.
argument-hint: "[--since DATE] [--project NAME] [--provider NAME] [--limit N] [--list] [--rescan]"
disable-model-invocation: true
---

# Session Scan (Tier 1)

Compute deterministic-but-heuristic session metrics from ccrider-discovered
sessions. This is contributor analytics, not release gating.

## Requirements

Interactive session discovery requires `ccrider` MCP. If it is unavailable:

> ccrider MCP is unavailable. You can still run
> `references/compute-metrics.py` manually on local transcript exports, but
> this skill cannot discover sessions automatically without ccrider.

## Important Caveat

Session-scan results are exploratory. Use them to decide what to inspect next,
not as proof that a plugin change helped or hurt.

Prefer a single provider when analyzing trends. Mixed Claude Code and Codex
sessions can produce misleading comparisons.

## Usage

```text
/session-scan
/session-scan --since 2026-02-01
/session-scan --project myapp
/session-scan --provider claude-code
/session-scan --limit 20
/session-scan --list
/session-scan --rescan
```

If your installed `ccrider` uses a different provider label, pass that exact
label to `--provider`.

## Main-Context Workflow

### 1. Parse Arguments

Supported flags:

- `--since DATE`
- `--project NAME`
- `--provider NAME`
- `--limit N`
- `--list`
- `--rescan`

Defaults:

- `--since`: 7 days ago
- `--limit`: 50
- `--provider`: unset unless the contributor asks for it

### 2. Discover Candidate Sessions

Use the lightweight ccrider listing call first.

If your ccrider MCP exposes provider filtering, pass the contributor's
`--provider` through to discovery. Otherwise:

1. list recent sessions normally
2. inspect provider metadata in the returned session summaries
3. keep only the requested provider before scoring

If `--list` is present, stop after showing the filtered candidate table.

### 3. Deduplicate Against the Ledger

Read `.claude/session-metrics/metrics.jsonl` if present.

- skip sessions already scanned unless `--rescan` is set
- preserve append-only history
- report how many sessions were new vs already present

### 4. Resolve the Canonical Scorer

Locate:

```text
${CLAUDE_SKILL_DIR}/references/compute-metrics.py
```

This script is the canonical scorer for contributor analytics. Do not
re-implement the metric formulas inline in the prompt.

### 5. Spawn One Subagent Per Session

Use one lightweight subagent per session. Main context must not fetch large
session transcripts directly.

Use `Agent(...)`, not legacy `Task(...)`, in contributor guidance.

Each scoring subagent should:

1. fetch one session transcript from ccrider
2. write the transcript JSON to a temp file under `.claude/session-metrics/`
3. run `compute-metrics.py` once for that session
4. include `--provider NAME` when the provider is known
5. write the score to a temp result file
6. delete its temp transcript file

### 6. Collect Results

Append each `_result_*.json` entry into
`.claude/session-metrics/metrics.jsonl`, then remove the temp result files.

### 7. Display a Triage Table

Show a concise table sorted by friction descending, for example:

```text
| ID       | Provider    | Project | Date       | Fingerprint | Friction | Opportunity | Tier2? |
|----------|-------------|---------|------------|-------------|----------|-------------|--------|
| ffa155ee | claude-code | myapp   | 2026-02-18 | bug-fix     | 0.42     | 0.65        | Yes    |
| 90a74843 | claude-code | myapp   | 2026-02-17 | feature     | 0.15     | 0.20        | No     |
```

If high-signal sessions exist, suggest `/session-deep-dive`.

### 8. Write Scan Metadata

Update `.claude/session-metrics/latest-scan.json` with:

- scan time
- provider filter used
- sessions discovered
- sessions scanned
- sessions skipped
- Tier 2 eligible count

## Scoring Reference

See `references/scoring-guide.md`.

Core outputs:

- friction score
- fingerprint
- plugin opportunity score
- tool profile
- skill-effectiveness hints

These metrics are intentionally directional, not decision-grade.

## Iron Laws

1. Do not fetch large transcripts in main context.
2. Use one subagent per scored session.
3. Keep provider scope explicit when the contributor cares about trends.
4. Use the canonical scorer script instead of hand-recomputing formulas.
5. Keep the metrics ledger append-only.
6. Treat scan output as triage input, not release proof.

## Epistemic Posture

Scan output is triage signal, not decision-grade. Report what the
scorer actually produced with direct language; do not dress up raw
heuristics in confident framing. Low-sample sessions remain low-
confidence in the output. Apology cascades and hedge chains have no
place in a scan summary.
