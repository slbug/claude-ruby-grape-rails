# Skill Effectiveness Metrics

Reference for the observational skill-use signals currently emitted by
`compute-metrics.py`.

## Core Principle

These metrics are behavioral proxies, not correctness proofs.

They can help answer:

- which skills appear to lead to follow-up action?
- which skills often precede corrections or confusion?
- which skills deserve transcript review?

They cannot, on their own, prove that a prompt or agent change improved the
plugin.

## What the Ledger Actually Contains

Per skill, the current scorer records:

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

Do not claim support for measurements the ledger does not compute.

## Outcome Labels

Current outcome labels are simple heuristics:

| Outcome | Meaning |
|---------|---------|
| `effective` | low visible friction and some follow-up action |
| `friction` | strong visible corrections or many errors |
| `no_action` | little visible follow-up after invocation |
| `mixed` | some action and some friction |

## Cross-Session Aggregates

Reasonable dashboard aggregates:

| Aggregate | Meaning |
|-----------|---------|
| total invocations | how often the skill was called |
| sessions used in | how broad the sample is |
| weighted action rate | how often the skill appears to trigger follow-up action |
| weighted avg post-errors | visible failures after the skill |
| weighted avg post-corrections | visible user redirections after the skill |
| outcome distribution | rough shape of the observed outcomes |

## Interpreting the Numbers Safely

### Action rate

Useful for:

- finding ignored or low-follow-through skills

Not enough for:

- claiming a skill is correct or helpful by itself

### Post-errors and post-corrections

Useful for:

- finding sessions worth transcript review
- spotting misleading or incomplete skill behavior

Not enough for:

- proving the skill caused the errors

### Baseline comparison

Sessions with and without skills can be compared, but the result is still
heavily confounded by task type, contributor choice, and session difficulty.

If you show baseline deltas, label them as heuristic context.

## Confidence Rules

Use explicit confidence notes:

| Situation | Guidance |
|-----------|----------|
| fewer than 3 invocations | very low confidence |
| mixed providers | low confidence until segmented |
| no corroborating transcript review | low-to-medium confidence |
| corroborated by `lab/eval` or docs-check | stronger recommendation basis |

## Corroboration Checklist

Before turning dashboard output into a recommendation, check at least one of:

- manual transcript review
- `lab/eval`
- docs-check
- deterministic plugin validation

Without corroboration, keep the output framed as an investigation lead.
