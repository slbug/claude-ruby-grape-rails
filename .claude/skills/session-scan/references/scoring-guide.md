# Scoring Guide

## Audience: Agents, Not Humans

Imperative-only. NO LLM in scoring — pipeline is deterministic:
ccrider SQLite read → regex extraction + aggregation → one JSON line
per session.

## Read This First

| Use | Status |
|---|---|
| ranking sessions for deeper review | OK |
| spotting repeated friction patterns | OK |
| finding likely missed plugin-command opportunities | OK |
| claiming a plugin change definitely improved outcomes | NO |
| comparing mixed-provider datasets without segmentation | NO |
| treating one metric as a release gate | NO |

## Friction Score (0.0 - 1.0)

Measures visible resistance in a session.

### Formula

```text
raw = sum(signal_value * weight)
score = sigmoid(raw)
```

Parameters: `k = 3.0`, `midpoint = 1.5`.

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

Triage buckets, NOT calibrated truth.

## Session Fingerprint

Rule-based session classification. Current classes:

- `bug-fix`
- `feature`
- `exploration`
- `maintenance`
- `review`
- `refactoring`

Signals combined: intent keywords from early user messages, tool mix,
edit volume, dependency-management commands, review tooling commands.

Confidence = relative to other fingerprint scores in same session.

## Plugin Opportunity Score (0.0 - 1.0)

Rough signal for likely missed `/rb:` command use.

Heuristics:

- repeated command retries
- many tools with no planning
- repeated manual verification
- repeated GitHub PR commands
- many edits without a review pass

Use to inspect transcripts. NOT a roadmap input without corroboration.

## Skill-Effectiveness Hints

Per-skill signals emitted:

- invocation count
- post-skill edits
- post-skill reads
- post-skill test runs
- post-skill errors
- post-skill corrections
- dominant outcome

Observational hints. Always corroborate with `lab/eval`, manual
transcript review, or docs-check / plugin validation if claim implies
product defect.

## Tool Profile

Buckets:

| Bucket | Tools |
|---|---|
| `read_pct` | `Read` + `Glob` |
| `edit_pct` | `Edit` + `Write` + `NotebookEdit` (legacy `MultiEdit` aliased to edit-family in historical data) |
| `bash_pct` | `Bash` |
| `grep_pct` | `Grep` |
| `tidewave_pct` | MCP calls whose tool name starts with `mcp__tidewave` |
| `other_pct` | `Agent`, legacy `Task`, `Skill`, `AskUserQuestion`, `ExitPlanMode`, `KillShell`, `MCPSearch`, other MCP tools |

## Provider Scope

When comparing scans / trends:

1. Prefer single provider at a time.
2. Record provider filter used.
3. Do NOT compare mixed-provider windows as homogeneous.

## What This Guide Avoids

- fixed "healthy" adoption percentages
- strong causal claims from transcript-derived behavior
- unsupported chain-analysis claims
