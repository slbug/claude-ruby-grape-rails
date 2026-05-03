---
name: session-trends
description: Analyze exploratory trends across the session metrics ledger. Use for provider-scoped comparisons and broad monitoring, not for release-grade conclusions.
argument-hint: "[--window 7d|30d|all] [--project NAME] [--provider NAME] [--compare PATH]"
disable-model-invocation: true
---

# Session Trends

## Audience: Agents, Not Humans

Imperative-only. Output is monitoring + prioritization signal — NOT
causal proof of plugin impact.

## Requirements

`.claude/session-metrics/metrics.jsonl` (from `/session-scan`).

## Usage

| Command | Behavior |
|---|---|
| `/session-trends` | default 7-day window |
| `/session-trends --window 30d` | broader window |
| `/session-trends --project myapp` | substring on `project_path` |
| `/session-trends --provider claude-code` | exact provider |
| `/session-trends --compare .claude/session-analysis/insights-2026-03-20.md` | comparison reference |

## Workflow

### 1. Parse Arguments

| Flag | Values |
|---|---|
| `--window` | `7d` / `30d` / `all` |
| `--project` | NAME |
| `--provider` | NAME |
| `--compare` | PATH |

### 2. Read the Metrics Ledger

Read `.claude/session-metrics/metrics.jsonl`. Missing or empty → stop;
tell contributor to run `/session-scan` first.

### 3. Compute Windowed Aggregates

Run `python3 ${CLAUDE_SKILL_DIR}/../session-scan/references/compute-metrics.py --trends .claude/session-metrics/metrics.jsonl`.

Add `--project "$PROJECT_FILTER"` or `--provider "$PROVIDER_FILTER"`
only when the contributor requested those filters.

### 4. Read Comparison Notes Separately

`--compare PATH` provided → read separately, compare cautiously against
computed aggregates. Do NOT rely on `MEMORY.md` as a required baseline.

### 5. Present a Readable Report

Show:

- top-level `time_series_signal`
- distinct dates represented in ledger
- total sessions in each window
- average friction
- average opportunity
- fingerprint distribution
- Tier 2 eligible percentage
- plugin adoption rate
- provider distribution

Provider filter not used + ledger mixes providers → state explicitly
before interpreting trends.

Brand-new ledger or fewer than 10 sessions:

- state explicitly: little or no time-series signal yet
- note when `7d`, `30d`, `all` are effectively the same dataset
- treat output as early snapshot, NOT a trend

### 6. Suggest Next Actions Carefully

| Trend | Suggestion |
|---|---|
| rising friction | `/session-deep-dive` on recent high-friction sessions |
| growing missed opportunities | inspect whether docs / workflow guidance is stale |
| mixed-provider ledger | re-run with `--provider` |

## Iron Laws

1. Trend output is observational.
2. Prefer provider-scoped comparisons over mixed-provider windows.
3. Do NOT depend on missing local artifacts.
4. Keep raw ledger read-only.

## Epistemic Posture

Direct language for trend findings. Real drift pattern → direct
statement with ledger evidence. Do NOT soften into "trends might be
shifting". Mixed-provider windows → explicit caveat, NOT a hedge that
obscures the signal. No apology cascades, no hedge chains.
