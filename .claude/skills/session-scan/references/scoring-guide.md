# Scoring Guide

Reference documentation for all session metrics algorithms, weights,
thresholds, and fingerprint rules used by `compute-metrics.py`.

## Friction Score (0.0 - 1.0)

Measures how much resistance/struggle occurred in a session.

### Formula

```
raw = Σ (signal_value × weight)
score = sigmoid(raw) = 1 / (1 + e^(-k × (raw - midpoint)))
```

Parameters: `k = 3.0`, `midpoint = 1.5`

### Signal Weights

| Signal | Weight | Detection Method |
|--------|--------|------------------|
| `error_tool_ratio` | 2.0 | `error_count / tool_count` |
| `retry_loops` | 3.0 | Same Bash command prefix 3+ consecutive times |
| `user_corrections` | 2.5 | Messages matching correction patterns |
| `approach_changes` | 2.0 | Dominant tool shifts between session quarters |
| `context_compactions` | 1.5 | System messages about context compaction |
| `interrupted_requests` | 1.0 | `[Request interrupted by user]` occurrences |

### Correction Patterns

Regex for detecting user corrections:

```
\b(no[,.]?\s|wrong|instead|actually|that's not|not what I|
I meant|I said|please don't|stop|undo|revert)\b
```

Applied to first 500 chars of each user message.

### Approach Change Detection

1. Split tool call sequence into 4 equal chunks
2. Find dominant tool in each chunk
3. Count transitions between different dominant tools

### Interpretation

| Score Range | Meaning |
|-------------|---------|
| 0.00 - 0.15 | Smooth session, minimal friction |
| 0.15 - 0.35 | Some friction, 1-2 stuck points |
| 0.35 - 0.60 | High friction, multiple issues |
| 0.60 - 1.00 | Severe friction, likely abandoned approaches |

## Session Fingerprint

Rule-based classifier that identifies session type.

### Keyword Scores (applied to first 10 user messages)

| Type | Keywords (×2.0 each) |
|------|---------------------|
| `bug-fix` | fix, bug, broken, error, issue, crash, fail, debug, wrong |
| `feature` | add, implement, build, create, new feature, scaffold |
| `exploration` | explore, understand, how does, what is, explain, look at |
| `maintenance` | deps, update, upgrade, bump, version, migrate |
| `review` | review, PR, pull request, code review, feedback |
| `refactoring` | refactor, extract, rename, move, reorganize, clean up |

### Tool Profile Bonuses

| Condition | Type | Bonus |
|-----------|------|-------|
| Read+Grep > 50% AND Edit < 10% | `exploration` | +3.0 |
| Edit > 30% | `feature` | +2.0 |
| Bash > 30% | `bug-fix` | +2.0 |
| Files edited > 10 | `refactoring` | +2.0 |
| Files edited > 5 | `feature` | +1.0 |
| runtime tooling calls > 0 | `bug-fix` | +1.5 |
| `bundle install/update` commands | `maintenance` | +3.0 |
| `gh pr` commands | `review` | +3.0 |

### Confidence

```
confidence = best_type_score / total_all_scores
```

Range: 0.0 - 1.0. Higher = more certain classification.

## Plugin Opportunity Score (0.0 - 1.0)

Detects missed plugin command opportunities.

### Signal Detection

| Signal | Missed Command | Condition |
|--------|---------------|-----------|
| Retry loops (3+ same cmd) | `/rb:investigate` | Consecutive similar Bash commands |
| 50+ tools, no plan | `/rb:plan` | High tool count without planning |
| 3+ test/zeitwerk runs | `/rb:verify` | Repeated manual verification |
| 2+ `gh pr` commands | `/rb:pr-review` | Manual PR workflow |
| 10+ edits, no review | `/rb:review` | Many changes without quality check |

### Formula

```
score = min(missed_opportunities × 0.2, 1.0)
```

Commands already used in the session are excluded from missed opportunities.

## Tier 2 Eligibility

A session is eligible for deep qualitative analysis if ANY of:

| Condition | Rationale |
|-----------|-----------|
| `friction_score > 0.35` | High friction worth investigating |
| `plugin_opportunity_score > 0.5` | Multiple missed opportunities |
| Plugin commands used | Learn from actual plugin usage |
| `message_count > 50` | Long sessions often have patterns |

## Tool Profile

Percentage breakdown of tool usage:

- `read_pct`: Read + Glob
- `edit_pct`: Edit + Write
- `bash_pct`: Bash
- `grep_pct`: Grep
- `tidewave_pct`: All `mcp__tidewave*` tools
- `other_pct`: Everything else (Task, Skill, other MCP)

## Tuning Guide

### Adjusting Friction Sensitivity

To make friction scores **more sensitive** (flag more sessions):

- Decrease `FRICTION_SIGMOID_MIDPOINT` (e.g., 1.0 instead of 1.5)
- Increase individual signal weights

To make friction scores **less sensitive** (fewer false positives):

- Increase `FRICTION_SIGMOID_MIDPOINT` (e.g., 2.0)
- Decrease weights on noisy signals (e.g., `user_corrections`)

### Adjusting Tier 2 Thresholds

- Lower `friction > 0.35` to catch more sessions
- Lower `opportunity > 0.5` to flag sessions with fewer missed commands
- Remove `message_count > 50` if long sessions aren't interesting

### Adding New Fingerprint Types

1. Add keyword regex to `FINGERPRINT_KEYWORDS`
2. Add tool profile bonuses in `compute_fingerprint()`
3. Update this guide
