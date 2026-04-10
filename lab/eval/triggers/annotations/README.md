# Failure Triage Annotations

Manual attribution for behavioral eval misses. Stored separately from
auto-generated results (which get overwritten on each rerun).

## Schema

Each file is `{skill}_annotations.json`:

```json
{
  "annotations": {
    "Plan a new Sidekiq retry workflow|true": {
      "failure_attribution": "router_defect",
      "note": "Haiku consistently preferred brainstorm"
    }
  }
}
```

Key format: `{prompt_text}|{expected_bool}` (stable across reruns).

## Valid `failure_attribution` values

- `router_defect` -- skill description needs tuning
- `corpus_defect` -- test prompt is misleading or wrong
- `ambiguity_mislabel` -- should be fork, not lock (or vice versa)
- `judge_artifact` -- order-bias or stochastic Haiku behavior
- `unknown` -- needs further investigation

## Workflow

1. Run `make eval-behavioral` and review misses
2. For each miss, create/update the annotation file
3. Attribution guides whether to fix the description, the corpus, or neither
