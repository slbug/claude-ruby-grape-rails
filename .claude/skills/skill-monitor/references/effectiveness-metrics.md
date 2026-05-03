# Skill Effectiveness Metrics

## Audience: Agents, Not Humans

Imperative-only.

## Core Principle

These metrics are behavioral proxies, NOT correctness proofs.

| They can answer | They cannot |
|---|---|
| which skills appear to lead to follow-up action? | prove a prompt or agent change improved the plugin |
| which skills often precede corrections or confusion? | (see above) |
| which skills deserve transcript review? | (see above) |

## What the Ledger Contains

Per skill, current scorer records:

- `invocation_count`
- `total_post_edits`
- `total_post_reads`
- `total_post_test_runs`
- `total_post_errors`
- `total_post_corrections`
- `led_to_action_count`
- `outcomes`
- `action_rate`
- `avg_post_errors`
- `avg_post_corrections`
- `dominant_outcome`

Do NOT claim support for measurements the ledger does not compute.

## Outcome Labels

| Outcome | Meaning |
|---------|---------|
| `effective` | low visible friction + some follow-up action |
| `friction` | strong visible corrections or many errors |
| `no_action` | little visible follow-up after invocation |
| `mixed` | some action + some friction |

## Cross-Session Aggregates

| Aggregate | Meaning |
|-----------|---------|
| total invocations | how often the skill was called |
| sessions used in | how broad the sample is |
| weighted action rate | how often the skill appears to trigger follow-up action |
| weighted avg post-errors | visible failures after the skill |
| weighted avg post-corrections | visible user redirections after the skill |
| outcome distribution | rough shape of observed outcomes |

## Interpreting the Numbers Safely

### Action rate

| Use | Status |
|---|---|
| finding ignored / low-follow-through skills | OK |
| claiming a skill is correct or helpful by itself | NO |

### Post-errors and post-corrections

| Use | Status |
|---|---|
| finding sessions worth transcript review | OK |
| spotting misleading or incomplete skill behavior | OK |
| proving the skill caused the errors | NO |

### Baseline comparison

Sessions with vs without skills can be compared, but result is heavily
confounded by task type, contributor choice, session difficulty.

Show baseline deltas → label as heuristic context.

## Confidence Rules

| Situation | Guidance |
|-----------|----------|
| fewer than 3 invocations | very low confidence |
| mixed providers | low confidence until segmented |
| no corroborating transcript review | low-to-medium confidence |
| corroborated by `lab/eval` or docs-check | stronger recommendation basis |

## Corroboration Checklist

Before turning dashboard output into a recommendation, check at least one:

- manual transcript review
- `lab/eval`
- docs-check
- deterministic plugin validation

Without corroboration → frame output as investigation lead, NOT
recommendation.
