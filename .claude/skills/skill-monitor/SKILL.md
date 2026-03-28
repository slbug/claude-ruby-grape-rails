---
name: skill-monitor
description: Analyze observational skill-effectiveness signals across scanned sessions. Use for exploratory monitoring and recommendation triage, not as a release gate.
argument-hint: "[--skill NAME] [--improve] [--window 7d|30d|all] [--provider NAME]"
disable-model-invocation: true
---

# Skill Monitor

Summarize transcript-derived skill-use signals from `.claude/session-metrics/`.

This workflow is exploratory. It helps contributors decide where to inspect
transcripts or prompts next. It does not prove a skill is good or bad on its
own.

## Requirements

Requires `.claude/session-metrics/metrics.jsonl` from `/session-scan`.

## Before You Trust the Dashboard

Prefer this order:

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `/docs-check` if Claude docs drift is suspected
4. `/skill-monitor` as corroborating observational input

## Usage

```text
/skill-monitor
/skill-monitor --skill review
/skill-monitor --improve
/skill-monitor --window 30d
/skill-monitor --provider claude-code
```

## Workflow

### 1. Parse Arguments

Supported flags:

- `--skill NAME`
- `--improve`
- `--window 7d|30d|all`
- `--provider NAME`

### 2. Load Metrics

Read `.claude/session-metrics/metrics.jsonl` and extract
`skill_effectiveness`.

If the ledger has no `skill_effectiveness` data, tell the contributor to rescan
with the current scorer.

If `--provider` is present, restrict the dashboard to that provider.

### 3. Compute Observational Aggregates

Useful aggregates include:

- total invocations
- sessions used in
- weighted action rate
- weighted average post-errors
- weighted average post-corrections
- dominant outcomes

If you compute a baseline comparison, present it as heuristic context, not as a
causal effect estimate.

### 4. Display the Dashboard

The dashboard should show:

- window and provider scope
- sample sizes
- per-skill aggregates
- low-confidence warnings for thin samples

Flagged skills are review candidates, not proven regressions.

### 5. Improvement Mode

If `--improve` is requested, delegate to `skill-effectiveness-analyzer`.

The analyzer must:

- use the improvement template
- cite session evidence
- list confounders
- look for corroboration in:
  - `lab/eval`
  - docs-check
  - previous session-analysis reports

### 6. Write Output

Write dashboard snapshots under `.claude/skill-metrics/` without modifying
historical snapshots.

## Iron Laws

1. Treat all dashboard conclusions as observational.
2. Low-sample and mixed-provider results must be labeled clearly.
3. Corroborate strong claims with deterministic or manual evidence.
4. Never modify `metrics.jsonl` from this skill.
