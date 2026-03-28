# Scoring Guide

Reference for the exploratory metrics produced by
`references/compute-metrics.py`.

## Read This First

These scores are useful for triage, not for proving causality.

Good uses:

- ranking sessions for deeper review
- spotting repeated friction patterns
- finding likely missed plugin-command opportunities

Bad uses:

- claiming a plugin change definitely improved outcomes
- comparing mixed-provider datasets without segmentation
- treating one metric as a release gate

## Friction Score (0.0 - 1.0)

Measures how much visible resistance occurred in a session.

### Formula

```text
raw = sum(signal_value * weight)
score = sigmoid(raw)
```

Parameters:

- `k = 3.0`
- `midpoint = 1.5`

### Signals

| Signal | Weight | Detection |
|--------|--------|-----------|
| `error_tool_ratio` | 2.0 | `error_count / tool_count` |
| `retry_loops` | 3.0 | repeated Bash command prefixes |
| `user_corrections` | 2.5 | user redirection language |
| `approach_changes` | 2.0 | dominant tool shifts across the session |
| `context_compactions` | 1.5 | compaction mentions |
| `interrupted_requests` | 1.0 | explicit interrupted-request markers |

### Interpretation

| Range | Meaning |
|-------|---------|
| `0.00-0.15` | smooth |
| `0.15-0.35` | some friction |
| `0.35-0.60` | high friction |
| `0.60-1.00` | severe friction |

Treat these as triage buckets, not calibrated truth.

## Session Fingerprint

Rule-based session classification.

Current classes:

- `bug-fix`
- `feature`
- `exploration`
- `maintenance`
- `review`
- `refactoring`

Signals combine:

- intent keywords from early user messages
- tool mix
- edit volume
- dependency-management commands
- review tooling commands

Confidence is only relative to the other fingerprint scores in that same
session.

## Plugin Opportunity Score (0.0 - 1.0)

A rough signal for likely missed `/rb:` command use.

Current opportunity heuristics include:

- repeated command retries
- many tools with no planning
- repeated manual verification
- repeated GitHub PR commands
- many edits without a review pass

This score tells you where to inspect transcripts, not which feature to build
next without corroboration.

## Skill-Effectiveness Hints

The scorer emits per-skill signals such as:

- invocation count
- post-skill edits
- post-skill reads
- post-skill test runs
- post-skill errors
- post-skill corrections
- dominant outcome

Use these as observational hints. Always corroborate with:

- `lab/eval`
- manual transcript review
- docs-check / plugin validation if the claim implies a product defect

## Tool Profile

The current profile buckets are:

- `read_pct`: `Read` + `Glob`
- `edit_pct`: `Edit` + `Write` + `MultiEdit` + `NotebookEdit`
- `bash_pct`: `Bash`
- `grep_pct`: `Grep`
- `tidewave_pct`: MCP calls whose tool name starts with `mcp__tidewave`
- `other_pct`: everything else, including:
  - `Agent`
  - `Task` legacy alias
  - `Skill`
  - `AskUserQuestion`
  - `ExitPlanMode`
  - `KillShell`
  - `MCPSearch`
  - other MCP tools

## Provider Scope

When comparing scans or trends:

1. prefer a single provider at a time
2. record the provider filter used
3. do not compare mixed-provider windows as if they were homogeneous

## What This Guide Deliberately Avoids

- fixed "healthy" adoption percentages
- strong causal claims from transcript-derived behavior
- unsupported chain-analysis claims
