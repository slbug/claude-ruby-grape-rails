---
applyTo: "lab/eval/**"
excludeAgent: "coding-agent"
---

# Eval Framework Review Rules

## Audience: Agents, Not Humans

Imperative-only.

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

- Advisory checks for CLAUDE.md size and aggregate routing-prompt char
  budget (8,000-char hard ceiling on the skill listing per CC routing
  budget)
- Zero API cost — file reads and frontmatter scanning only
- Wired into `--changed`, `--all`, and `--ci` modes in run_eval.sh

## Module Map

The canonical module list is `ls lab/eval/*.py`. Re-derive on every
review pass; do not rely on a frozen enumeration here.

When reviewing a change under `lab/eval/`:

1. Read the module's docstring and `import` block — they declare its
   role and whether it touches an LLM provider.
2. Check whether `make eval-ci-deterministic` reaches it transitively
   (see `lab/eval/run_eval.sh --ci` body and the allowlist in
   `lab/eval/tests/test_eval_ci_determinism.py::DETERMINISTIC_PATH_FILES`).
   Modules on that path MUST stay LLM-free.
3. LLM-bearing modules (`behavioral_scorer.py`, `epistemic_suite.py`,
   `trigger_scorer.py --semantic` path) are intentionally OFF the
   deterministic path. Confirm any new transport import goes into one
   of those, not into the deterministic path.

Provider conventions (apply when reviewing LLM-bearing changes):

- `behavioral_scorer.py` — provider via `--provider` flag →
  `RUBY_PLUGIN_EVAL_PROVIDER` → `ollama` default (Gemma4, model tag
  `RUBY_PLUGIN_EVAL_OLLAMA_MODEL`, default `gemma4:26b-a4b-it-q8_0`).
  Ollama is currently the only wired provider; future providers (e.g.,
  Microsoft Waza) plug in via `_PROVIDER_SETTINGS` +
  `_run_provider` dispatch + `SUPPORTED_PROVIDERS` in `results_dir.py`.
- `epistemic_suite.py` — captures baselines at
  `lab/eval/baselines/epistemic/{namespace}/pre-posture.json`
  (gitignored). Refuses to run when baseline is missing or injector
  hash matches baseline.

Shared infrastructure to reuse (do not re-implement):

- `frontmatter.py` / `schemas.py` — YAML frontmatter parser, result
  dataclasses
- `results_dir.py` — single source of truth for behavioral result
  paths under `lab/eval/triggers/results/{namespace}/`
- `eval_logging.py` — `emit_info` shared logger usable from CLI + tests

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

## Fixtures, Baselines, Tests

- `lab/eval/fixtures/output/` — tracked artifact fixtures scored by
  `output_checks.py` / `artifact_scorer.py`
- `lab/eval/fixtures/epistemic/` — scenarios consumed by `epistemic_suite.py`
- `lab/eval/fixtures/trust-states/` — trust-state fixtures (see
  `tests/test_trust_states.py`)
- `lab/eval/fixtures/compression/` — `{rspec_long_failure,
  brakeman_noisy, migration_success}/{raw.txt,expected.txt}` consumed
  by `compression_eval.py` (the deterministic-path fixture eval that
  shells to `lab/eval/bin/compress-verify`)
- `lab/eval/baselines/` — gitignored local snapshots; never commit
- `lab/eval/tests/` — unittest-discoverable test modules; tests are
  required for any new module under `lab/eval/`

## Cross-File Drift Around Eval Changes

- New skill under `plugins/.../skills/<name>/` → require matching
  `lab/eval/evals/<name>.json` and `lab/eval/triggers/<name>.json`
  (otherwise `default_eval()` fallback hides regressions)
- Removed skill/agent → require removal of corresponding eval/trigger
  JSONs; `check_refs.py` will fail on stale cross-references
- Added/renamed module under `lab/eval/` → also update `run_eval.sh`,
  `Makefile`, `package.json` scripts, and (if the new module is reached
  by `make eval-ci-deterministic`)
  `lab/eval/tests/test_eval_ci_determinism.py::DETERMINISTIC_PATH_FILES`.
  Reviewers rely on the canonical `ls lab/eval/*.py` set re-derived each
  pass, not a frozen list in this file.

## Do NOT Flag

- Generated trigger prompts that seem generic (padding for count thresholds)
- `**_: Any` in matcher signatures (kwargs forwarding pattern)
- `_template.json` files (not scored, used as contributor reference)
- Files starting with `_` in triggers/ (special corpus files)
- Gitignored `lab/eval/baselines/` snapshots being absent from the repo
- `lab/eval/fixtures/epistemic/` scenarios that look adversarial — they
  are intentional baseline-vs-current contrasts for posture metrics
