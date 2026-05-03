---
name: skill-monitor
description: Analyze observational skill-effectiveness signals across scanned sessions. Use for exploratory monitoring and recommendation triage, not as a release gate.
argument-hint: "[--skill NAME] [--improve] [--window 7d|30d|all] [--provider NAME]"
disable-model-invocation: true
---

# Skill Monitor

## Audience: Agents, Not Humans

Imperative-only. Exploratory — does NOT prove a skill is good or bad
on its own.

## Requirements

`.claude/session-metrics/metrics.jsonl` (from `/session-scan`).

## Trust Order

Before trusting the dashboard:

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `/docs-check` if Claude docs drift suspected
4. `/skill-monitor` — corroborating observational input

## Usage

| Command | Behavior |
|---|---|
| `/skill-monitor` | dashboard for all skills |
| `/skill-monitor --skill review` | scoped to one skill |
| `/skill-monitor --improve` | delegates to `skill-effectiveness-analyzer` |
| `/skill-monitor --window 30d` | broader window |
| `/skill-monitor --provider claude-code` | exact provider |

## Workflow

### 1. Parse Arguments

| Flag | Values |
|---|---|
| `--skill` | NAME |
| `--improve` | (no value, triggers analyzer mode) |
| `--window` | `7d` / `30d` / `all` |
| `--provider` | NAME |

### 2. Load Metrics

Read `.claude/session-metrics/metrics.jsonl`. Extract
`skill_effectiveness`.

No `skill_effectiveness` data → tell contributor to rescan with current
scorer.

`--provider` present → restrict dashboard to that provider.

### 3. Compute Observational Aggregates

Useful aggregates:

- total invocations
- sessions used in
- weighted action rate
- weighted avg post-errors
- weighted avg post-corrections
- dominant outcomes

Baseline comparison computed → present as heuristic context, NOT causal
effect estimate.

### 4. Display the Dashboard

Show:

- window + provider scope
- sample sizes
- per-skill aggregates
- low-confidence warnings for thin samples

Flagged skills are review candidates, NOT proven regressions.

### 5. Improvement Mode

`--improve` requested → delegate to `skill-effectiveness-analyzer`.

Analyzer requirements:

- use the improvement template
- cite session evidence
- list confounders
- look for corroboration in `lab/eval`, docs-check, previous session-analysis reports

### 6. Write Output

Write dashboard snapshots under `.claude/skill-metrics/`. Do NOT modify
historical snapshots.

## Iron Laws

1. All dashboard conclusions are observational.
2. Low-sample + mixed-provider results MUST be labeled clearly.
3. Corroborate strong claims with deterministic or manual evidence.
4. NEVER modify `metrics.jsonl` from this skill.

## Epistemic Posture

Explicit confidence on observational findings. Direct language for
HIGH-confidence (deterministic signals, large-N agreement across
providers). LOW-confidence MUST be labeled — do NOT promote noise into
confident findings via polite phrasing. Hedge qualifiers belong on
genuinely-uncertain claims, NOT scattered across the report. State
contradictions with contributor expectations directly.
