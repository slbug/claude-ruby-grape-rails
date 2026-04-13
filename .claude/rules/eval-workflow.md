# Contributor Eval Workflow

Minimum runtime: python3 3.10+ for `lab/eval/`.

## Eval Entrypoints

| Command | Description |
|---------|-------------|
| `make eval` / `npm run eval` | Lint + injection check + tracked changed surfaces |
| `make eval-all` / `npm run eval:all` | Full eval snapshot |
| `make eval-ci` / `npm run eval:ci` | Contributor CI gate |
| `make eval-output` / `npm run eval:output` | Deterministic research/review artifact checks |
| `make security-injection` / `npm run security:injection` | Dynamic injection scanning |
| `make eval-tests` / `npm run eval:test` | Default unittest discovery |
| `make eval-tests-pytest` / `npm run eval:test:pytest` | Explicit pytest runs |
| `make eval-behavioral` / `npm run eval:behavioral` | LLM trigger routing (cache-only) |
| `make eval-behavioral-verbose` | Same with verbose cache/score output |
| `make eval-behavioral-fresh` | Ignore cache, re-run via default provider (apfel, on-device) |
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

## Current Scope

- 51/51 skill eval coverage and trigger corpora
- Structural scoring for all shipped agents
- Deterministic trigger corpora and confusable-pair analysis
- Optional behavioral routing dimension (cached apfel/haiku results per `RUBY_PLUGIN_EVAL_PROVIDER`)

## Contributor Workflow Order

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `make eval-output` for artifact fixture checks
4. `/docs-check` when Claude docs or schema assumptions may have drifted
5. Session analytics only as corroborating, provider-scoped evidence
