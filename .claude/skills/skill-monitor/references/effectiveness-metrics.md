# Skill Effectiveness Metrics

Defines the measurement framework for evaluating plugin skill
effectiveness across sessions.

## Core Principle

The OpenHands feedback loop: **deploy - monitor - evaluate - improve**.

The "correctness" signal comes from user behavior — not explicit
ratings. When a skill produces useful output, the developer acts
on it (edits files, runs tests). When it doesn't help, the
developer corrects, ignores, or abandons the approach.

## Per-Session Skill Signals

Extracted by `compute-metrics.py` in the `skill_effectiveness` field:

### Raw Signals

| Signal | Source | Meaning |
|--------|--------|---------|
| `invocation_count` | User messages | How many times skill was invoked |
| `total_post_edits` | Tool calls after invocation | Edits made following skill |
| `total_post_reads` | Tool calls after invocation | Research following skill |
| `total_post_test_runs` | Bash calls with `rspec`/`minitest` | Verification after skill |
| `total_post_errors` | Error patterns in messages | Failures after skill |
| `total_post_corrections` | Correction patterns in user messages | User redirections |
| `led_to_action_count` | post_edits > 0 or post_test_runs > 0 | Skill produced action |

### Computed Signals

| Signal | Formula | Range | Good |
|--------|---------|-------|------|
| `action_rate` | led_to_action_count / invocation_count | 0-1 | > 0.7 |
| `avg_post_errors` | total_post_errors / invocation_count | 0+ | < 1.0 |
| `avg_post_corrections` | total_post_corrections / invocation_count | 0+ | < 0.5 |
| `dominant_outcome` | Most common outcome classification | enum | "effective" |

### Outcome Classification

Each invocation is classified into one of:

| Outcome | Criteria | Interpretation |
|---------|----------|----------------|
| `effective` | No errors, no corrections, led to action | Skill worked well |
| `friction` | Corrections > 0 or errors > 3 | Skill caused problems |
| `no_action` | No edits, no test runs | Skill output was ignored |
| `mixed` | Some errors but also action | Partial success |

## Cross-Session Aggregates

The `/skill-monitor` command computes these from metrics.jsonl:

### Per-Skill Metrics

| Aggregate | Computation | Threshold |
|-----------|-------------|-----------|
| Total invocations | Sum across sessions | Informational |
| Session count | Distinct sessions | Informational |
| Weighted action rate | Σ(action_rate × n) / Σ(n) | Flag if < 0.5 |
| Weighted avg errors | Σ(avg_errors × n) / Σ(n) | Flag if > 2.0 |
| Weighted avg corrections | Σ(avg_corr × n) / Σ(n) | Flag if > 1.0 |
| Outcome distribution | Counts of each outcome type | Flag if friction > 30% |
| Effectiveness score | action_rate - (0.3 × corrections) | Flag if < 0.5 |

### Baseline Comparison

Critical for meaningful interpretation. Without baseline, raw
numbers are uninterpretable.

**Baseline group**: Sessions with zero skill invocations.
**Skill group**: Sessions with at least one skill invocation.

| Comparison | Good Signal | Bad Signal |
|------------|-------------|------------|
| Friction delta (skill - baseline) | Negative (skills reduce friction) | Positive (skills add friction) |
| Error rate delta | Negative | Positive |
| Duration delta | Negative (faster) | Positive (slower) |

### Trend Detection

Compare across time windows to detect degradation:

```
7d_effectiveness vs 30d_effectiveness → trend direction
```

| Trend | Interpretation | Action |
|-------|----------------|--------|
| Rising effectiveness | Skill improvements working | Continue monitoring |
| Stable | No change | Check if already good enough |
| Declining | Skill degrading | Investigate: model changes? code changes? |
| Insufficient data | < 3 invocations in window | Extend window or wait |

## Per-Skill Evaluation Criteria

Different skills have different "correctness" proxies:

### `/rb:review`

| Proxy | Signal | How to measure |
|-------|--------|----------------|
| Suggestion acceptance | Edits to files flagged in review | post_edits to review-mentioned files |
| False positive rate | Corrections after review | post_corrections |
| Completeness | No new issues found later | absence of subsequent /rb:review |

### `/rb:plan`

| Proxy | Signal | How to measure |
|-------|--------|----------------|
| Task completion | Checkboxes completed | Requires plan.md parsing |
| Scope accuracy | No corrections during /rb:work | post_corrections in work sessions |
| Rework rate | Plan re-done via --existing | Subsequent /rb:plan --existing |

### `/rb:investigate`

| Proxy | Signal | How to measure |
|-------|--------|----------------|
| Root cause found | Edits follow investigation | post_edits > 0 |
| Fix success | Tests pass after fix | post_test_runs with no post_errors |
| Debugging loop break | No retry loops after | absence of retry_loop friction signal |

### `/rb:compound`

| Proxy | Signal | How to measure |
|-------|--------|----------------|
| Solution created | File written to .claude/solutions/ | post_edits to solutions dir |
| Reuse | Solution referenced in future sessions | Cross-session grep (deep-dive only) |
| Quality | No corrections during creation | post_corrections == 0 |

### `/rb:verify`

| Proxy | Signal | How to measure |
|-------|--------|----------------|
| Pass rate | Tests/zeitwerk/format pass | post_errors == 0 |
| Issues found | Led to fixes | post_edits > 0 after errors found |
| False alarms | Corrections about irrelevant failures | post_corrections |

### `/rb:quick`

| Proxy | Signal | How to measure |
|-------|--------|----------------|
| One-shot success | Task done without follow-up | no subsequent corrections |
| Scope containment | Small change count | post_edits < 5 |
| Speed | Low tool count after invocation | total window tools < 20 |

## Dashboard JSON Schema

Output format for `.claude/skill-metrics/dashboard-{date}.json`:

```json
{
  "computed_at": "ISO8601",
  "window": "7d|30d|all",
  "session_count": 50,
  "sessions_with_skills": 18,
  "sessions_without_skills": 32,
  "baseline_friction": 0.32,
  "skill_friction": 0.18,
  "friction_delta": -0.14,
  "skills": {
    "/rb:review": {
      "invocations": 12,
      "sessions": 8,
      "action_rate": 0.92,
      "avg_post_errors": 0.5,
      "avg_post_corrections": 0.1,
      "effectiveness_score": 0.89,
      "outcome_distribution": {
        "effective": 9,
        "mixed": 2,
        "friction": 1,
        "no_action": 0
      },
      "trend": "stable"
    }
  },
  "flagged_skills": [
    {
      "skill": "/rb:investigate",
      "reason": "effectiveness_score < 0.5",
      "score": 0.42,
      "recommendation": "Review error handling patterns"
    }
  ]
}
```

## Minimum Data Requirements

| Analysis Level | Minimum Sessions | Minimum Invocations |
|----------------|-----------------|---------------------|
| Dashboard | 5 | 3 per skill |
| Trend comparison | 10 (across both windows) | 5 per skill |
| Improvement recs | 10 | 5 per flagged skill |
| Statistical confidence | 30 | 15 per skill |

Below minimums: show data with "LOW CONFIDENCE" warning.
