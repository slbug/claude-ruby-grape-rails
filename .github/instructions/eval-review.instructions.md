---
applyTo: "lab/eval/**"
excludeAgent: "coding-agent"
---

# Eval Framework Review Rules

## Eval Definitions (lab/eval/evals/*.json)

- Each JSON defines dimensions: completeness, accuracy, conciseness,
  triggering, safety, clarity
- Each dimension has a weight (float, all weights should sum to ~1.0) and
  an array of checks
- Check types must match functions in matchers.py MATCHERS dict
- Skill-specific checks override the default_eval() fallback in scorer.py
- Eval definitions should not exceed 3KB

## Trigger Corpora (lab/eval/triggers/*.json)

- Each JSON has: skill, should_trigger, should_not_trigger,
  hard_should_trigger, hard_should_not_trigger
- Minimum counts: 4 should_trigger, 4 should_not_trigger,
  2 hard_should_trigger, 2 hard_should_not_trigger
- Hard prompts must have an `axis` field with >= 2 distinct values
  across hard_should_trigger (typically "confusable" and "multi_step")
- Prompts must not contain skill names (routing contamination)
- No duplicate prompts within a file (normalized comparison)

## Context Budget (lab/eval/context_budget.py)

- Advisory checks for CLAUDE.md size and framework skill paths: coverage
- Zero API cost — file reads and frontmatter scanning only
- Wired into `--changed`, `--all`, and `--ci` modes in run_eval.sh
- `EXPECTED_PATHS_SKILLS` list must be updated when adding framework skills

## Additional Modules

- `matcher_ablation.py` — leave-one-out matcher signal/noise classification
- `neighbor_regression.py` — confusable-pair regression detection
- `eval_sensitivity.py` — threshold sensitivity analysis
- `behavioral_scorer.py` — LLM-based trigger routing (cached apfel/haiku
  results per `--provider` flag or `RUBY_PLUGIN_EVAL_PROVIDER` env var;
  apfel is the default)

## Matchers (lab/eval/matchers.py)

- All matchers are deterministic — zero API cost
- Matchers return `tuple[bool, str]` (passed, evidence)
- Register new matchers in the MATCHERS dict
- Behavioral dimension exists but uses cached results from separate
  `make eval-behavioral` runs — not part of default eval

## Scorer (lab/eval/scorer.py)

- default_eval() provides fallback for skills without explicit eval JSONs
- score_skill() returns SubjectScore with composite 0.0-1.0
- The eval-ci-deterministic gate requires all skills to pass a minimum threshold

## Do NOT Flag

- Generated trigger prompts that seem generic (padding for count thresholds)
- `**_: Any` in matcher signatures (kwargs forwarding pattern)
- `_template.json` files (not scored, used as contributor reference)
- Files starting with `_` in triggers/ (special corpus files)
