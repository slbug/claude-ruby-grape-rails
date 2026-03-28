---
name: session-trends
description: Analyze exploratory trends across the session metrics ledger. Use for provider-scoped comparisons and broad monitoring, not for release-grade conclusions.
argument-hint: "[--window 7d|30d|all] [--project NAME] [--provider NAME] [--compare PATH]"
disable-model-invocation: true
---

# Session Trends

Summarize `metrics.jsonl` over time windows.

This skill is for monitoring and prioritization. It should not be treated as
causal proof that a plugin change helped or hurt.

## Requirements

Requires `.claude/session-metrics/metrics.jsonl` from `/session-scan`.

## Usage

```text
/session-trends
/session-trends --window 30d
/session-trends --project myapp
/session-trends --provider claude-code
/session-trends --compare .claude/session-analysis/insights-2026-03-20.md
```

## Workflow

### 1. Parse Arguments

Supported flags:

- `--window 7d|30d|all`
- `--project NAME`
- `--provider NAME`
- `--compare PATH`

### 2. Read the Metrics Ledger

Read `.claude/session-metrics/metrics.jsonl`.

If it is missing or empty, stop and tell the contributor to run
`/session-scan` first.

### 3. Compute Windowed Aggregates with the Canonical Script

Use:

```bash
python3 ${CLAUDE_SKILL_DIR}/../session-scan/references/compute-metrics.py \
  --trends .claude/session-metrics/metrics.jsonl \
  --project "$PROJECT_FILTER" \
  --provider "$PROVIDER_FILTER"
```

Only pass `--project` or `--provider` when the contributor requested them.

### 4. Read Comparison Notes Separately

If `--compare PATH` is provided, read that file separately and compare it
cautiously against the computed aggregates.

Do not rely on `MEMORY.md` as a required baseline.

### 5. Present a Readable Report

Show:

- top-level `time_series_signal`
- distinct dates represented in the ledger
- total sessions in each window
- average friction
- average opportunity
- fingerprint distribution
- Tier 2 eligible percentage
- plugin adoption rate
- provider distribution

If a provider filter was not used and the ledger mixes providers, say so
explicitly before interpreting the trends.

If the ledger is brand new or has fewer than 10 sessions:

- say explicitly that there is little or no time-series signal yet
- note when `7d`, `30d`, and `all` are effectively the same dataset
- treat the output as an early snapshot, not a trend

### 6. Suggest Next Actions Carefully

Examples:

- rising friction -> run `/session-deep-dive` on recent high-friction sessions
- growing missed opportunities -> inspect whether docs or workflow guidance is stale
- mixed-provider ledger -> re-run with `--provider`

## Iron Laws

1. Treat trend output as observational.
2. Prefer provider-scoped comparisons over mixed-provider windows.
3. Do not depend on missing local artifacts.
4. Keep the raw ledger read-only.
