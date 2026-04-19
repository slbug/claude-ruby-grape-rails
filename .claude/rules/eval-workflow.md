# Contributor Eval Workflow

Minimum runtime: python3 3.14+ for `lab/eval/`.

## Eval Entrypoints

| Command | Description |
|---------|-------------|
| `make eval` / `npm run eval` | Lint + injection check + tracked changed surfaces |
| `make eval-all` / `npm run eval:all` | Full eval snapshot |
| `make eval-ci` / `npm run eval:ci` | Contributor CI gate |
| `make eval-output` / `npm run eval:output` | Deterministic research/review artifact checks |
| `make eval-epistemic` / `npm run eval:epistemic` | Epistemic-posture metrics (6 metrics, 10 scenarios, 1 system-prompt snapshot per run) |
| `make security-injection` / `npm run security:injection` | Dynamic injection scanning |
| `make eval-tests` / `npm run eval:test` | Default unittest discovery |
| `make eval-tests-pytest` / `npm run eval:test:pytest` | Explicit pytest runs |
| `make eval-behavioral` / `npm run eval:behavioral` | LLM trigger routing (cache-only) |
| `make eval-behavioral-verbose` | Same with verbose cache/score output |
| `make eval-behavioral-fresh` | Ignore cache, re-run via default provider (Ollama `gemma4:26b-a4b-it-q8_0`, local) |
| `make eval-behavioral-fresh-verbose` | Fresh run with full prompt/response debug |
| `make eval-ablation` / `npm run eval:ablation` | Leave-one-out matcher signal/noise (deterministic) |
| `make eval-neighbor` / `npm run eval:neighbor` | Confusable-pair regression on changed skills |
| `make eval-hygiene` / `npm run eval:hygiene` | Trigger corpus contamination scanning |
| `make eval-baseline` | Baseline snapshot |
| `make eval-compare` | Compare against baseline |
| `make eval-overlap` | Overlap analysis |
| `make eval-hard-corpus` | Hard corpus evaluation |

## Notes

- `eval-output` is separate from `eval-all` / `eval-ci`
- `--include-untracked` makes results non-comparable; not part of `eval-ci`
- `check-dynamic-injection.sh` expects git metadata for tracked-file scans
- For long contributor eval runs (`make eval-all`, `make eval-behavioral-fresh`),
  set `ENABLE_PROMPT_CACHING_1H=1` to opt into the 1-hour cache TTL and reduce
  per-call cost. Complements `FORCE_PROMPT_CACHING_5M=1` when you need the
  default shorter TTL on specific subruns. (CC 2.1.108+.)

## Current Scope

- 51/51 skill eval coverage and trigger corpora
- Structural scoring for all shipped agents
- Deterministic trigger corpora and confusable-pair analysis
- Optional behavioral routing dimension (cached Ollama model namespace, apfel, or haiku results per `RUBY_PLUGIN_EVAL_PROVIDER`)

## Contributor Workflow Order

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `make eval-output` for artifact fixture checks
4. `/docs-check` when Claude docs or schema assumptions may have drifted
5. Session analytics only as corroborating, provider-scoped evidence

## Epistemic Posture Eval (`make eval-epistemic`)

Measures the behavioral effect of changes to `preferences.yml` / `iron-laws.yml`
by comparing model responses across two injector states: **before** and
**after** a regeneration. The system prompt for every fixture call is
captured at run time from `plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh`
— i.e. the real SubagentStart signal, no mirror.

### PR Workflow

Every PR that touches `preferences.yml` / `iron-laws.yml` must start with a
fresh baseline capture. Baselines are gitignored local snapshots and may
persist on disk across PRs — if you start a new PR without re-capturing,
your post-change delta will include changes from `main` that landed
between your previous baseline and this PR.

1. **Start PR from fresh main.** Pull latest.

2. **Capture baseline** against current injector state, per provider you
   plan to measure:

   ```bash
   # delete any stale baseline from a previous PR first
   rm -f lab/eval/baselines/epistemic/*/pre-posture.json

   python3 -m lab.eval.epistemic_suite --baseline-only --provider ollama --workers 6 --summary --pretty
   python3 -m lab.eval.epistemic_suite --baseline-only --provider apfel  --workers 6 --summary --pretty
   python3 -m lab.eval.epistemic_suite --baseline-only --provider haiku  --workers 6 --summary --pretty
   ```

   Outputs auto-resolve to
   `lab/eval/baselines/epistemic/{namespace}/pre-posture.json`. Baselines
   are gitignored (local snapshot, same convention as `make eval-baseline`).

3. **Make your `preferences.yml` / `iron-laws.yml` edits.**

4. **Regenerate** — `bash scripts/generate-iron-law-outputs.sh all`. The
   presence gate at `scripts/check-epistemic-baseline-drift.py` blocks
   regeneration only when the active provider's baseline is missing.
   Baseline freshness (timestamp + hash) is printed so you can judge
   whether it's from this PR or a leftover. Hash-mismatch between
   baseline and current injector is expected during iteration (edit →
   regen → edit → regen) — the gate does not block on mismatch. Skip
   the gate entirely with `EPISTEMIC_BASELINE_CHECK=0` when no
   epistemic measurement is planned (initial generation, CI without
   eval, etc.).

5. **Iterate.** Edit source, regen, edit, regen. Baseline stays as
   fixed reference. Each regen produces a new current state.

6. **Run post-change measurement:**

   ```bash
   python3 -m lab.eval.epistemic_suite --provider ollama --workers 6 --summary --pretty
   ```

   Suite refuses to run (exit 2) when:
   - Baseline is missing (nothing to compare against)
   - Current injector hash matches baseline hash (inject-iron-laws.sh
     unchanged since baseline — you likely forgot to regenerate)

   On success, prints per-metric baseline / current / delta drift.

### Env vars

- `RUBY_PLUGIN_EVAL_PROVIDER` — `ollama` (default) / `apfel` / `haiku`.
- `RUBY_PLUGIN_EVAL_OLLAMA_MODEL` — model tag (default
  `gemma4:26b-a4b-it-q8_0`, ~28GB, MoE with 4B active tokens).
  The namespace is derived from the tag (`gemma4:26b-a4b-it-q8_0` →
  `gemma4-26b-a4b-it-q8_0`) so each model keeps its own baseline
  directory. The two LLM-judge metrics benefit from a larger instruct
  model that follows the AGREE/FLAG/DISAGREE format reliably.

  **Low-RAM fallback.** If ~28GB of free RAM isn't available for the
  model, switch to the smaller tag before running anything:

  ```bash
  export RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest
  # or inline per command:
  RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest make eval-epistemic
  RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest make eval-behavioral-fresh
  ```

  Under the low-RAM fallback: regex metrics (`apology_density`,
  `hedge_cascade_rate`, `finding_recall`, `false_positive_rate`) are
  unaffected; the two LLM-judge metrics become noisier because the
  smaller model is weaker at the format-constrained classification.
  Baselines captured under the low-RAM model live at a different
  namespace (`lab/eval/baselines/epistemic/gemma4/`) so they do not
  mix with the 26b baselines.
- `EPISTEMIC_BASELINE_CHECK=0` — opt out of the drift gate in
  `generate-iron-law-outputs.sh` (initial generation, legitimate baseline
  loss, provider switch).
- `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`,
  `OLLAMA_NUM_PARALLEL=4`, `OLLAMA_MAX_LOADED_MODELS=1` — auto-set by
  `_ensure_ollama_server` when the suite starts the server itself.
  Without `OLLAMA_NUM_PARALLEL > 1`, the ollama daemon serializes
  requests so `--workers > 1` queues at the server instead of running
  in parallel. These env vars must be set BEFORE `ollama serve`
  starts — if ollama is already running (Ollama.app, external
  `ollama serve`), the suite emits a warning and no env-var change
  applies. Stop the external server (`killall ollama`, quit Ollama.app)
  to let the suite autostart with the eval-tuned env. Override
  individual values if VRAM is tight: e.g.
  `OLLAMA_NUM_PARALLEL=1 make eval-epistemic`.
- `ENABLE_PROMPT_CACHING_1H=1` / `FORCE_PROMPT_CACHING_5M=1` — Haiku-only
  cost controls (CC 2.1.108+).

### Metrics

- **Regex** (no LLM call): `apology_density`, `hedge_cascade_rate`,
  `finding_recall`, `false_positive_rate`.
- **LLM-judge** (provider call per scenario): `unsupported_agreement_rate`,
  `direct_contradiction_rate`. Roughly 2 calls per run per judge-metric
  scenario.

### Provider notes

- **Apfel:** kept in the provider set for future expansion of Apple
  Foundation Model capabilities (larger context, stronger on-device
  reasoning). Currently of limited practical use for epistemic eval:
  - 4096-token context window overflows on several fixtures (baseline
    errors on a rotating subset each run — fixtures + system prompt
    ~3.6-4k tokens combined).
  - Apple FM 4B is too weak to serve as a reliable LLM-judge
    (observed `unsupported_agreement_rate=1.0` on baseline fixtures
    where haiku scored 0.0).
  - Weak model over-literalizes posture preferences: observed
    "Acknowledge mistakes once" turning into a full `### Apology`
    heading + paragraph in delta runs, increasing apology_density
    vs baseline (opposite of intended posture effect).
  - **Apfel is NOT a gate input.** Gate providers are ollama and
    haiku only. Apfel results are captured for reference / future
    expansion but do not block merge.
- **Haiku:** cloud Claude, cheap per run. Use prompt caching env vars
  for repeated runs. Most reliable LLM-judge of the three providers.
- **Ollama:** fully local. First run starts `ollama serve` automatically;
  model gets pulled on first use if missing. Gemma4 26b+ MoE with
  `reasoning_effort` control is the recommended local judge.
