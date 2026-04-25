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
- `behavioral_scorer.py` — LLM-based trigger routing. Default provider
  resolved by `--provider` flag → `RUBY_PLUGIN_EVAL_PROVIDER` env var →
  `ollama` (local Gemma4, model tag `RUBY_PLUGIN_EVAL_OLLAMA_MODEL`,
  default `gemma4:26b-a4b-it-q8_0`). Other choices: `apfel` (on-device,
  no gate input), `haiku` (paid Anthropic API, prompt-cache via
  `ENABLE_PROMPT_CACHING_1H=1` / `FORCE_PROMPT_CACHING_5M=1`)
- `epistemic_suite.py` — epistemic-posture metrics (regex +
  LLM-judge) over fixtures in `lab/eval/fixtures/epistemic/`. Captures
  baselines at `lab/eval/baselines/epistemic/{namespace}/pre-posture.json`
  (gitignored). Refuses to run when baseline is missing or injector hash
  matches baseline (nothing changed). Gate providers: `ollama` and
  `haiku` only — `apfel` results are reference-only
- `agent_matchers.py` / `agent_scorer.py` — deterministic structural
  scoring of agent frontmatter and body (separate from skill scoring)
- `artifact_scorer.py` / `output_checks.py` — research/review output
  artifact checks against fixtures in `lab/eval/fixtures/output/`
  (canonical contributor check for provenance/report contract changes)
- `check_refs.py` — validates internal `/rb:<skill>` and
  `subagent_type: <agent>` cross-references resolve on disk
- `trigger_expand.py` — Haiku-assisted self-sampled trigger corpus
  expansion (contributor-only; not part of `eval-ci-deterministic`)
- `trigger_scorer.py` — validation and scoring of deterministic
  trigger corpora; enforces minimum counts, axis coverage,
  contamination guards
- `frontmatter.py` / `schemas.py` — shared YAML frontmatter parser and
  result dataclasses; reuse instead of re-implementing
- `results_dir.py` — single source of truth for behavioral result
  paths under `lab/eval/triggers/results/{namespace}/`
- `eval_auth.py` — `claude --bare` auth resolution (keychain via
  `bare_settings.json` → cached OAuth)
- `eval_logging.py` — `emit_info` shared logger usable from CLI and tests
- `baseline.py` / `compare.py` — snapshot + comparison (drives
  `make eval-baseline` / `make eval-compare`)

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
  `Makefile`, `package.json` scripts, and the "Additional Modules"
  list in this file
- `EXPECTED_PATHS_SKILLS` in `context_budget.py` must include any new
  framework skill paths

## Do NOT Flag

- Generated trigger prompts that seem generic (padding for count thresholds)
- `**_: Any` in matcher signatures (kwargs forwarding pattern)
- `_template.json` files (not scored, used as contributor reference)
- Files starting with `_` in triggers/ (special corpus files)
- `bare_settings.json` (eval auth fixture, not a runtime secret)
- Gitignored `lab/eval/baselines/` snapshots being absent from the repo
- `lab/eval/fixtures/epistemic/` scenarios that look adversarial — they
  are intentional baseline-vs-current contrasts for posture metrics
