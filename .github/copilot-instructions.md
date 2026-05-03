# Repository Context

This repo is a **Claude Code plugin** for Ruby/Rails/Grape development —
NOT a Ruby application. Do not suggest Ruby app patterns (controllers,
models, routes) for plugin files.

## Audience: Agents, Not Humans

ALL prose in this repo (except `README.md`, `CHANGELOG.md`, executable
code under `scripts/` / `lab/eval/`) loads into some agent's context at
runtime:

| Surface | Audience |
|---|---|
| shipped plugin docs | Claude sub-/main-sessions |
| `.claude/rules/` + `.claude/skills/` | contributor-session Claude |
| `.github/copilot-instructions.md` + `.github/instructions/*` | Copilot |

Authoring rules:

- Imperative instructions, not explanatory guides
- No tutorial narration ("first do X, then Y, this teaches…")
- No reasoning preludes — state the action
- No `#` thinking/checklist lines inside Bash command bodies (preference #6); use markdown tables / prose around bash blocks to label commands
- Markdown tables for option/command lists

PR review: flag prose that violates this rule.

## Architecture

| Component | Path | Role |
|---|---|---|
| Agents | `plugins/ruby-grape-rails/agents/*.md` | Markdown + YAML frontmatter; specialist reviewers, analyze without modifying |
| Skills | `plugins/ruby-grape-rails/skills/*/SKILL.md` | Command-driven or auto-loaded knowledge with `references/` subdirs |
| Hooks | `plugins/ruby-grape-rails/hooks/hooks.json` + `scripts/*` | Shell + Ruby triggered by CC events (PostToolUse, PostToolUseFailure, SessionStart, etc) |
| Executables | `plugins/ruby-grape-rails/bin/*` | Plugin CLIs added to Bash PATH; no extension; chmod +x; mixed bash + Ruby |
| Library | `plugins/ruby-grape-rails/lib/*.rb` | End-user runtime modules (Ruby ≥ 3.4, stdlib only) |
| Plugin settings | `plugins/ruby-grape-rails/settings.json` | Only `agent` + `subagentStatusLine` keys supported per CC docs |
| Eval | `lab/eval/` | Deterministic Python eval framework for plugin quality |
| Contributor tooling | `.claude/` | NOT shipped; `.claude/rules/` (auto-loaded path-scoped rules), `.claude/skills/` (contributor-only skills) |

### Currently-shipped binaries

| Binary | Purpose |
|---|---|
| `subagent-statusline` (bash) | advisory statusline renderer; fail-open |
| `detect-stack` (Ruby) | `/rb:init` stack detection |
| `extract-permissions` (Ruby) | transcript-based Bash permission recommender |
| `resolve-base-ref` (bash) | eval-able BASE_REF resolver for diff comparisons |
| `compression-stats` (Ruby) | end-user reader for verify-output telemetry; `--redact` mode emits intermediate input for `/rb:compression-report` skill (NOT a final paste-anywhere artifact — skill drafts the final markdown) |
| `provenance-scan` (Ruby) | end-user provenance-sidecar auditor; classifies `*.provenance.md` via 4-state algorithm; surfaced via `/rb:provenance-scan` |
| `manifest-update` (Ruby) | atomic JSON manifest writer for spawn-fanout `RUN-CURRENT.json`; subcommands: `prepare-run`, `field`, `spawn-paths`, `init`, `patch`, `prepare-respawn`, `archive`, `resume-check`, `status`; path-allowlist gate, symlink refusal, fsync + POSIX rename. Main session calls this — NOT raw `mv` / `cp` / `jq -i` / `rm` |

## Rule Scope

`.github/instructions/*.instructions.md` files declare `applyTo:` glob
and `excludeAgent: "coding-agent"`. Review-only — coding-agent ignores
during implementation; reviewers (this file + scoped files) enforce
on handoff.

## What CI Already Checks

Do NOT flag issues already caught by CI:

- Markdown linting (markdownlint)
- Shell linting (shellcheck)
- JSON/YAML validation
- Plugin manifest validation (`claude plugin validate`)
- Eval scoring gate (`make eval-ci-deterministic`)
- Release metadata alignment (`check-release-metadata.py`)
- Dynamic injection scanning (`check-dynamic-injection.sh`)

## Review Priorities

| Priority | Scope |
|---|---|
| CRITICAL | security vulnerabilities, data loss risks, breaking plugin schema |
| IMPORTANT | convention violations, missing frontmatter, incorrect tool access |
| IMPORTANT | unsupported agreement with author's framing when diff or evidence points elsewhere → review defect; challenge false premises directly |
| IMPORTANT | direct correction over soft alignment; HIGH-confidence findings use direct language; reserve "might" / "potentially" for genuine uncertainty |
| SUGGESTION | readability improvements, description wording, minor optimizations |

## Cross-File Consistency (Drift Check)

A PR diff is necessary but NOT sufficient. Many defects in this repo
surface as drift between modified and unmodified files. Inspect
untouched files for stale references, missed regenerations, inconsistent
state introduced by the diff. Flag drift even when the unmodified file
is not part of the PR.

### Required cross-file checks

- **Skill rename / removal / description change** → also check
  `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`,
  `plugins/ruby-grape-rails/skills/init/references/injectable-template.md`,
  `lab/eval/evals/<skill>.json`, `lab/eval/triggers/<skill>.json`,
  `lab/eval/triggers/_hard_corpus.json`,
  `lab/eval/triggers/_confusable_pairs.json`,
  `lab/eval/triggers/_semantic_pairs.json`, `README.md`, `CHANGELOG.md`,
  cross-skill `/rb:<name>` mentions in other skills/agents.
- **Agent rename / removal / description change** → also check skill-body
  fanout owners
  (`plugins/ruby-grape-rails/skills/{review,plan,full}/SKILL.md`,
  `.claude/skills/docs-check/SKILL.md` for contributor agents),
  `plugins/ruby-grape-rails/skills/plan/references/planning-workflow.md`
  (selection matrix), skill files mentioning `subagent_type: <name>`,
  `plugins/ruby-grape-rails/skills/intro/SKILL.md` +
  `intro/references/tutorial-content.md` (count claims), `README.md`
  (Agent Hierarchy diagram + agents table + count claims), `CLAUDE.md`
  (count + structure tree),
  `.github/instructions/plugin-review.instructions.md`,
  `.claude/skills/cc-changelog/references/analysis-rules.md` (analysis
  assumptions).
- **`plugins/ruby-grape-rails/references/iron-laws.yml`** edited →
  required regeneration via `scripts/generate-iron-law-outputs.sh all`.
  Verify these regenerated artifacts ride along in the diff and match
  source: `README.md` (Iron Laws section),
  `plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md`,
  `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`,
  `plugins/ruby-grape-rails/agents/iron-law-judge.md`,
  `plugins/ruby-grape-rails/hooks/scripts/inject-rules.sh` (header
  `Source versions: iron-laws=<v>`). `iron-laws.yml` change with no
  regenerated outputs in diff → drift defect. Init injectable template
  (`skills/init/references/injectable-template.md`) is no longer a
  regeneration target — Iron Laws + Preferences delivered via runtime
  hook (`SessionStart` + `SubagentStart`), NOT inline in CLAUDE.md.
- **`plugins/ruby-grape-rails/references/preferences.yml`** edited →
  required regeneration as above; verify `Advisory Preferences` section
  of `inject-rules.sh` matches source. Flag if
  `lab/eval/baselines/epistemic/*/pre-posture.json` is committed
  (baselines are gitignored snapshots).
- **Plugin version bump** in any of `package.json`,
  `.claude-plugin/marketplace.json`,
  `plugins/ruby-grape-rails/.claude-plugin/plugin.json` → all three MUST
  match; `CHANGELOG.md` MUST have a section for the new version
  (categories: Added, Changed, Fixed, Removed). Validated by
  `scripts/check-release-metadata.py`; flag locally before CI.
- **Hook renamed / added / removed** under
  `plugins/ruby-grape-rails/hooks/scripts/` → also check
  `hooks/hooks.json` references, sourcing in other `*.sh` files
  (`source ".../<lib>.sh"`), matching tests under
  `lab/eval/tests/test_runtime_scripts.py`.
- **`bin/<exec>` renamed / added / removed** → also check
  `plugins/ruby-grape-rails/settings.json` (statusline command path),
  `plugins/ruby-grape-rails/hooks/scripts/install-statusline-wrapper.sh`,
  any skill/agent/script that shells out, `CLAUDE.md` "Executables"
  enumeration.
- **New skill / agent / hook added** → also check corresponding
  `lab/eval/evals/`, `lab/eval/triggers/`, `lab/eval/dimensions/`
  artifacts exist; intro tutorial mentions it; CLAUDE.md skill/agent
  counts updated.
- **Eval module added / renamed under `lab/eval/`** → also check
  `lab/eval/run_eval.sh`, `Makefile`, `package.json` `scripts:` block,
  `.claude/rules/eval-workflow.md`,
  `.github/instructions/eval-review.instructions.md` "Additional
  Modules" list.
- **Skill / agent description text change** → check combined
  `description + when_to_use` length against ceilings (skills: 1,536;
  agents: 250). Flag if unchanged sibling field pushes total over limit
  after the edit.
- **`compute_trust_state` schema change** in
  `lab/eval/output_checks.py` → also update fixtures under
  `lab/eval/fixtures/output/` + `lab/eval/fixtures/trust-states/` +
  tests in `lab/eval/tests/test_trust_states.py`. Schema rules
  (required keys, allowed `kind` values, `supports` shape) live only in
  code — no separate JSON Schema file. Schema rule edit without
  matching fixture + test updates → drift defect.
- **`requirements-dev.txt` edited** (Python module added/removed) →
  also update `scripts/check-contributor-prereqs.sh`
  `check_dev_python_modules()` + `pip install -r requirements-dev.txt`
  step in `.github/workflows/lint.yml`. Doctor script hardcodes module
  names by design (no user-supplied argument flows into `python3 -c`);
  each new dep needs explicit `python3 -c "import <name>"` line.
- **`make eval-ci-deterministic` Makefile target edited** → audit
  comment ("Must NOT transitively invoke any LLM provider …") is
  self-checked by `lab/eval/tests/test_eval_ci_determinism.py`. Reword
  the comment → update the regex in
  `EvalCiDeterminismTests.test_makefile_target_exists`. Removing
  comment without updating test → drift defect; removing without
  restoring equivalent guard → determinism-policy regression.
- **`plugins/ruby-grape-rails/references/run-manifest.md`** edited →
  also check `plugins/ruby-grape-rails/bin/manifest-update` (encodes
  schema in `SKILL_CONVENTIONS` + `ALLOWED_PATH_RE`),
  `plugins/ruby-grape-rails/skills/review/SKILL.md`,
  `skills/review/references/review-playbook.md`,
  `skills/review/references/review-template.md`,
  `plugins/ruby-grape-rails/skills/plan/SKILL.md`,
  `skills/plan/references/planning-workflow.md`,
  `plugins/ruby-grape-rails/skills/brainstorm/SKILL.md`, `README.md`
  (How Review Works + Artifact Layout), `CLAUDE.md` (Artifact
  Directories), `.claude/rules/skill-development.md`,
  `.claude/rules/agent-development.md`. Manifest schema, staleness
  rules, atomic-write protocol, per-skill conventions MUST stay aligned
  across these surfaces. Per-run artifact paths use
  `{slug}-{datesuffix}.md` (review) or stable `{topic-slug}.md`
  (plan/brainstorm); shipped reference to `{slug}.md` (without
  datesuffix) for review consolidated artifacts → drift defect. Schema
  change without matching `bin/manifest-update` `SKILL_CONVENTIONS`
  update → silent contract break.
- **`plugins/ruby-grape-rails/references/research/tool-batching.md`**
  edited → verify links from `.claude/rules/agent-development.md` §
  "Bash Discipline" and
  `plugins/ruby-grape-rails/skills/review/references/review-playbook.md`
  § "Diff strategy" still resolve. Tool-batching preference rule itself
  lives in `references/preferences.yml`; rule edits trigger preferences
  regeneration as above.

### How to surface drift findings

Direct: "PR edits `<file A>` but unchanged `<file B>` still references
the old name/value. Also update `<file B>`."

Do NOT soften with "might want to" / "consider also" — drift is a
correctness defect, NOT a style suggestion.
