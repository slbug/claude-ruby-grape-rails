# Contributor Eval Workflow

## Audience: Agents, Not Humans

Imperative-only. Tables for command/option lists.

Minimum runtime: python3 3.14+ for `lab/eval/`.

Session analytics under `.claude/skills/session-scan/` and `skill-monitor`
are heuristic + observational. Use as corroborating evidence ONLY,
after deterministic gates pass. See `.claude/rules/development.md`
§ "Deterministic-First Ordering".

## Eval Entrypoints

| Command | Description |
|---------|-------------|
| `make eval` / `npm run eval` | Lint + injection check + tracked changed surfaces |
| `make eval-all` / `npm run eval:all` | Full eval snapshot |
| `make eval-ci-deterministic` / `npm run eval:ci:deterministic` | Full deterministic CI gate. Runs `eval-output` + `check-refs` + `eval-compression` + `run_eval.sh --ci` (lint, injection guard, skill/agent/trigger scoring, ablation, hygiene + context-budget advisory). Used by GitHub CI. MUST NOT transitively invoke any LLM provider |
| `make check-refs` / `npm run check:refs` | Validate skill/agent cross-references resolve on disk |
| `make eval-output` / `npm run eval:output` | Deterministic research/review artifact checks |
| `make eval-compression` / `npm run eval:compression` | Deterministic fixture eval for the verify-output compressor (Ruby CLI). Pass thresholds: ≥40% mean bytes reduction, 0 preservation violations, ≤15% diff |
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
| `make eval-trigger-expand SKILL=<name>` | Self-sampled trigger corpus expansion for one skill via Ollama |
| `make eval-trigger-expand-fragile` / `npm run eval:trigger-expand:fragile` | Same, fragile skills (from eval sensitivity) |
| `make eval-trigger-expand-all` / `npm run eval:trigger-expand:all` | Same, all skills |
| `make eval-baseline` | Baseline snapshot |
| `make eval-compare` | Compare against baseline |
| `make eval-overlap` | Overlap analysis |
| `make eval-hard-corpus` | Hard corpus evaluation |

## Notes

- `eval-output` is part of `eval-ci-deterministic`; can also be invoked standalone
- `--include-untracked` makes results non-comparable; NOT part of `eval-ci-deterministic`
- `check-dynamic-injection.sh` expects git metadata for tracked-file scans
- Long contributor eval runs (`make eval-all`, `make eval-behavioral-fresh`):
  set `ENABLE_PROMPT_CACHING_1H=1` for 1-hour cache TTL (reduces per-call
  cost). Complements `FORCE_PROMPT_CACHING_5M=1` for default shorter TTL
  on specific subruns. (CC 2.1.108+.)

## Current Scope

- Structural scoring + budget gates for all 52 shipped skills and all shipped agents
- Trigger corpora + behavioral routing scoring scoped to non-DMI skills only.
  Skills with `disable-model-invocation: true` have their descriptions stripped
  from Claude Code's routing context per [CC docs](https://code.claude.com/docs/en/skills),
  so routing eval against them measures behavior the runtime cannot perform.
  Helpers `load_hidden_skills()` in `trigger_scorer.py` and the matching filter
  in `behavioral_scorer.py`, `neighbor_confusion.py`, `neighbor_regression.py`,
  `triggers/generate_confusable_pairs.py`, `triggers/generate_hard_corpus.py`
  enforce the exclusion.
- Deterministic trigger corpora and confusable-pair analysis
- Optional behavioral routing dimension (cached Ollama-model namespace results; the provider dispatch in `behavioral_scorer._run_provider` is pluggable for future additions such as Microsoft Waza)

## Contributor Workflow Order

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `make eval-output` for artifact fixture checks
4. `/docs-check` when Claude docs or schema assumptions may have drifted
5. Session analytics only as corroborating, provider-scoped evidence

## Epistemic Posture Eval (`make eval-epistemic`)

Measures behavioral effect of `preferences.yml` / `iron-laws.yml`
changes by comparing model responses across two injector states:
**before** + **after** regeneration. System prompt for every fixture
call is captured at run time from
`plugins/ruby-grape-rails/hooks/scripts/inject-rules.sh` (shared
`SessionStart` + `SubagentStart` injector — real shipped signal, no
mirror).

### PR Workflow

PRs touching `preferences.yml` / `iron-laws.yml` MUST start with a
fresh baseline capture. Baselines are gitignored local snapshots and
may persist on disk across PRs — start a new PR without re-capturing
→ post-change delta includes changes from `main` between previous
baseline and this PR.

1. **Start PR from fresh main.** Pull latest.

2. **Capture baseline** against current injector state. Delete the stale baseline from the previous PR first, then capture:

   ```bash
   rm -f lab/eval/baselines/epistemic/*/pre-posture.json

   python3 -m lab.eval.epistemic_suite --baseline-only --provider ollama --workers 6 --summary --pretty
   ```

   Output auto-resolves to `lab/eval/baselines/epistemic/{namespace}/pre-posture.json`. Baselines are gitignored (local snapshot, same convention as `make eval-baseline`).

3. **Make `preferences.yml` / `iron-laws.yml` edits.**

4. **Regenerate** — `bash scripts/generate-iron-law-outputs.sh all`. Presence gate at `scripts/check-epistemic-baseline-drift.py` blocks regeneration when:
   - active provider's baseline missing
   - `python3` not on PATH
   - `python3` older than 3.14 (repo floor for `lab/eval/`)

   Baseline freshness (timestamp + hash) printed → judge whether from
   this PR or leftover. Hash-mismatch between baseline and current
   injector is expected during iteration (edit → regen → edit → regen)
   — gate does NOT block on mismatch. Skip the gate entirely with
   `EPISTEMIC_BASELINE_CHECK=0` when no epistemic measurement is planned
   (initial generation, CI without eval, contributor without python3
   3.14+ installed).

5. **Iterate.** Edit source, regen, edit, regen. Baseline stays as fixed reference. Each regen produces new current state.

6. **Run post-change measurement:**

   ```bash
   python3 -m lab.eval.epistemic_suite --provider ollama --workers 6 --summary --pretty
   ```

   Suite refuses (exit 2) when:
   - baseline missing (nothing to compare against)
   - current injector hash matches baseline hash (`inject-rules.sh` unchanged since baseline — likely forgot to regenerate)

   On success: prints per-metric baseline / current / delta drift.

### Env vars

- `RUBY_PLUGIN_EVAL_PROVIDER` — currently `ollama` only. Pluggable: future providers (e.g., Microsoft Waza) extend `SUPPORTED_PROVIDERS` in `lab/eval/results_dir.py` + add a dispatch branch in `behavioral_scorer._run_provider`.
- `RUBY_PLUGIN_EVAL_OLLAMA_MODEL` — model tag (default
  `gemma4:26b-a4b-it-q8_0`, ~28GB, MoE with 4B active tokens).
  Namespace derived from tag (`gemma4:26b-a4b-it-q8_0` →
  `gemma4-26b-a4b-it-q8_0`) → each model keeps its own baseline
  directory. Two LLM-judge metrics benefit from larger instruct model
  that follows the AGREE/FLAG/DISAGREE format reliably.

  **Low-RAM fallback.** ~28GB free RAM unavailable → switch to smaller tag before running anything:

  ```bash
  export RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest
  RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest make eval-epistemic
  RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest make eval-behavioral-fresh
  ```

  Export once per shell, or pass the env var inline per command.

  Under low-RAM fallback:

  | Metric class | Effect |
  |---|---|
  | regex (`apology_density`, `hedge_cascade_rate`, `finding_recall`, `false_positive_rate`) | unaffected |
  | LLM-judge | noisier — smaller model is weaker at format-constrained classification |

  Baselines under low-RAM model live at different namespace (`lab/eval/baselines/epistemic/gemma4/`) — do NOT mix with 26b baselines.
- `EPISTEMIC_BASELINE_CHECK=0` — opt out of the drift gate in `generate-iron-law-outputs.sh` (initial generation, legitimate baseline loss, provider switch).
- `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`,
  `OLLAMA_NUM_PARALLEL=4`, `OLLAMA_MAX_LOADED_MODELS=1` — auto-set by
  `_ensure_ollama_server` when suite starts the server itself. Without
  `OLLAMA_NUM_PARALLEL > 1`, ollama daemon serializes requests →
  `--workers > 1` queues at server instead of running in parallel. Env
  vars MUST be set BEFORE `ollama serve` starts — ollama already
  running (Ollama.app, external `ollama serve`) → suite emits warning,
  no env-var change applies. Stop external server (`killall ollama`,
  quit Ollama.app) → suite autostarts with eval-tuned env. Override
  individual values when VRAM tight:
  `OLLAMA_NUM_PARALLEL=1 make eval-epistemic`.

### Metrics

| Class | Metrics | Cost |
|---|---|---|
| Regex | `apology_density`, `hedge_cascade_rate`, `finding_recall`, `false_positive_rate` | no LLM call |
| LLM-judge | `unsupported_agreement_rate`, `direct_contradiction_rate` | provider call per scenario; ~2 calls per run per judge-metric scenario |

### Provider notes

- **Ollama:** fully local, $0 per run. First run starts `ollama serve`
  automatically. The eval suite does NOT auto-pull missing models; run
  `ollama pull gemma4:26b-a4b-it-q8_0` (or the value of
  `RUBY_PLUGIN_EVAL_OLLAMA_MODEL` if overridden) once before the first
  fresh eval. Gemma4 26b+ MoE with `reasoning_effort` control is the
  recommended local judge.
- **Future providers:** the dispatch in
  `behavioral_scorer._run_provider` is pluggable. Microsoft Waza is the
  planned next target; a Waza migration spec will land its dispatch
  entry + auth helpers when ready.
