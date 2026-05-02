# Repository Context

This is a **Claude Code plugin** for Ruby/Rails/Grape development, not a Ruby
application. Do not suggest Ruby app patterns (controllers, models, routes) for
plugin files.

## Architecture

The plugin ships specialist agents, skills, hooks, and eval tooling:

- **Agents** (`plugins/ruby-grape-rails/agents/*.md`): Markdown files with YAML
  frontmatter. Specialist reviewers that analyze code without modifying it.
- **Skills** (`plugins/ruby-grape-rails/skills/*/SKILL.md`): Command-driven or
  auto-loaded knowledge with references/ subdirectories.
- **Hooks** (`plugins/ruby-grape-rails/hooks/hooks.json` + `scripts/*`):
  Shell scripts and Ruby scripts triggered by Claude Code events
  (PostToolUse, PostToolUseFailure, SessionStart, etc).
- **Executables** (`plugins/ruby-grape-rails/bin/*`): plugin CLIs added to
  the Bash tool PATH when the plugin is enabled. No file extension, chmod +x.
  Mixed languages (bash + Ruby). Currently shipped: `subagent-statusline`
  (bash, advisory statusline renderer), `detect-stack` (Ruby, `/rb:init`
  stack detection), `extract-permissions` (Ruby, transcript-based Bash
  permission recommender), `resolve-base-ref` (bash, eval-able BASE_REF
  resolver for diff comparisons), `compression-stats` (Ruby, end-user
  reader for verify-output telemetry with `--redact` mode that emits
  intermediate input for the `/rb:compression-report` skill — NOT a
  final paste-anywhere artifact; the skill drafts the markdown report
  users review and share), `provenance-scan` (Ruby, end-user provenance-
  sidecar auditor — walks `.claude/{research,reviews,audit,plans/*}` and
  classifies each `*.provenance.md` via the 4-state algorithm; writes a
  dated Markdown report; surfaced via `/rb:provenance-scan`),
  `manifest-update` (Ruby, atomic JSON manifest writer for spawn-fanout
  RUN-CURRENT.json files — `prepare-run` (structured args:
  `--skill --slug --agents [--base-ref]`; helper computes path /
  datesuffix / agent paths / consolidated path / git pins),
  `field` (dotted-key field extraction), `spawn-paths` (tab-separated
  agent slug + absolute path per line), `init` / `patch` / `prepare-respawn` /
  `archive` / `resume-check` / `status` subcommands; path-allowlist
  gate, symlink refusal, fsync + POSIX rename; main session calls
  this instead of improvising `mv` / `cp` / `jq -i` / `rm`).
- **Plugin-owned Ruby library** (`plugins/ruby-grape-rails/lib/*.rb`):
  end-user runtime modules required by `bin/` CLIs and hook scripts.
  Ruby ≥ 3.4. Stdlib only (no Bundler gems). PyYAML is contributor-only;
  do NOT introduce a Python runtime dep under `lib/`.
- **Plugin settings** (`plugins/ruby-grape-rails/settings.json`): default
  settings applied when the plugin is enabled. Only `agent` and
  `subagentStatusLine` keys are supported per CC docs.
- **Eval** (`lab/eval/`): Deterministic Python eval framework for plugin quality.
- **Contributor tooling** (`.claude/`): Not shipped with the plugin.
  Includes `.claude/rules/` (auto-loaded context rules, some path-scoped)
  and `.claude/skills/` (contributor-only skills).

## How These Rules Are Scoped

Each `.github/instructions/*.instructions.md` file has an `applyTo:`
glob (`lab/eval/**`, `**/*.sh`, `**/*.md`, `plugins/**`) and an
`excludeAgent: "coding-agent"` directive. The `excludeAgent` flag tells
the harness that these rules are **review-only** — they apply to PR
review agents, not to a coding-agent that is mid-implementation. The
goal is to avoid feedback loops where the coding-agent over-fits to its
own review checklist while writing the diff. Reviewers (this file +
the four scoped files) follow the rules; the implementer ignores them
until handing off for review.

## What CI Already Checks

Do not flag issues already caught by CI:

- Markdown linting (markdownlint)
- Shell linting (shellcheck)
- JSON/YAML validation
- Plugin manifest validation (`claude plugin validate`)
- Eval scoring gate (`make eval-ci-deterministic`)
- Release metadata alignment (`check-release-metadata.py`)
- Dynamic injection scanning (`check-dynamic-injection.sh`)

## Review Priorities

- CRITICAL: Security vulnerabilities, data loss risks, breaking plugin schema
- IMPORTANT: Convention violations, missing frontmatter, incorrect tool access
- IMPORTANT: Treat unsupported agreement with the author's framing as a review defect when diff or evidence points elsewhere. Challenge false premises directly.
- IMPORTANT: Prefer direct correction over soft alignment when identifying real risks. Use direct language for HIGH-confidence findings; reserve "might" / "potentially" for genuine uncertainty.
- SUGGESTION: Readability improvements, description wording, minor optimizations

## Cross-File Consistency (Drift Check)

A PR diff is necessary but not sufficient. Many defects in this repo
surface as drift between modified and unmodified files. When reviewing a
PR, also inspect untouched files for stale references, missed
regenerations, and inconsistent state introduced by the diff. Flag drift
even when the unmodified file is not part of the PR.

### Required cross-file checks

- **Skill rename / removal / description change** → also check
  `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`,
  `plugins/ruby-grape-rails/skills/init/references/injectable-template.md`,
  `lab/eval/evals/<skill>.json`, `lab/eval/triggers/<skill>.json`,
  `lab/eval/triggers/_hard_corpus.json`, `lab/eval/triggers/_confusable_pairs.json`,
  `lab/eval/triggers/_semantic_pairs.json`, `README.md`, `CHANGELOG.md`,
  cross-skill `/rb:<name>` mentions in other skills/agents.
- **Agent rename / removal / description change** → also check
  skill-body fanout owners
  (`plugins/ruby-grape-rails/skills/{review,plan,full}/SKILL.md` and
  `.claude/skills/docs-check/SKILL.md` for contributor agents),
  `plugins/ruby-grape-rails/skills/plan/references/planning-workflow.md`
  (selection matrix), skill files mentioning `subagent_type: <name>`,
  `plugins/ruby-grape-rails/skills/intro/SKILL.md` and
  `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`
  (count claims), `README.md` (Agent Hierarchy diagram + agents table +
  count claims), `CLAUDE.md` (count + structure tree),
  `.github/instructions/plugin-review.instructions.md`,
  `.claude/skills/cc-changelog/references/analysis-rules.md`
  (analysis assumptions).
- **`plugins/ruby-grape-rails/references/iron-laws.yml`** edited →
  required regeneration via `scripts/generate-iron-law-outputs.sh all`.
  Verify these regenerated artifacts are in the diff and match source:
  `README.md` (Iron Laws section),
  `plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md`,
  `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`,
  `plugins/ruby-grape-rails/agents/iron-law-judge.md`,
  `plugins/ruby-grape-rails/hooks/scripts/inject-rules.sh`
  (header `Source versions: iron-laws=<v>`). A `iron-laws.yml` change
  with no regenerated outputs in the diff is a drift defect. The init
  injectable template (`skills/init/references/injectable-template.md`)
  is no longer a regeneration target — Iron Laws + Preferences are
  delivered via runtime hook (`SessionStart` + `SubagentStart`), not
  inline in CLAUDE.md.
- **`plugins/ruby-grape-rails/references/preferences.yml`** edited →
  required regeneration as above; verify the `Advisory Preferences`
  section of `inject-rules.sh` matches source. Also flag if
  `lab/eval/baselines/epistemic/*/pre-posture.json` is committed
  (baselines are gitignored snapshots).
- **Plugin version bump** in any of `package.json`,
  `.claude-plugin/marketplace.json`,
  `plugins/ruby-grape-rails/.claude-plugin/plugin.json` → all three must
  match, and `CHANGELOG.md` must have a section for the new version
  (categories: Added, Changed, Fixed, Removed). Validated by
  `scripts/check-release-metadata.py`; flag locally before CI runs it.
- **Hook renamed / added / removed** under
  `plugins/ruby-grape-rails/hooks/scripts/` → also check
  `plugins/ruby-grape-rails/hooks/hooks.json` references, sourcing in
  other `*.sh` files (`source ".../<lib>.sh"`), and any matching tests
  under `lab/eval/tests/test_runtime_scripts.py`.
- **`bin/<exec>` renamed / added / removed** → also check
  `plugins/ruby-grape-rails/settings.json` (statusline command path),
  `plugins/ruby-grape-rails/hooks/scripts/install-statusline-wrapper.sh`,
  any skill/agent/script that shells out to the executable, and
  `CLAUDE.md` "Executables" enumeration.
- **New skill / agent / hook added** → also check the corresponding
  `lab/eval/evals/`, `lab/eval/triggers/`, `lab/eval/dimensions/`
  artifacts exist; intro tutorial mentions it; CLAUDE.md skill/agent
  counts updated.
- **Eval module added / renamed under `lab/eval/`** → also check
  `lab/eval/run_eval.sh`, `Makefile`, `package.json` `scripts:` block,
  `.claude/rules/eval-workflow.md`, and `.github/instructions/eval-review.instructions.md`
  list of "Additional Modules".
- **Skill / agent description text change** → check the combined
  `description + when_to_use` length still fits the ceilings (skills:
  1,536; agents: 250). Flag if the unchanged sibling field pushes the
  total over the limit after the edit.
- **`compute_trust_state` schema change** in `lab/eval/output_checks.py`
  → also update fixtures under `lab/eval/fixtures/output/` and
  `lab/eval/fixtures/trust-states/` plus tests in
  `lab/eval/tests/test_trust_states.py`. Schema rules (required keys,
  allowed `kind` values, `supports` shape) live only in code — there is
  no separate JSON Schema file. A schema rule edit without matching
  fixture + test updates is a drift defect.
- **`requirements-dev.txt` edited** (added/removed Python module) →
  also update `scripts/check-contributor-prereqs.sh`
  `check_dev_python_modules()` and the `pip install -r
  requirements-dev.txt` step in `.github/workflows/lint.yml`. The
  doctor script hardcodes module names by design (no user-supplied
  argument flows into `python3 -c`); each new dep needs an explicit
  `python3 -c "import <name>"` line.
- **`make eval-ci-deterministic` Makefile target edited** → the audit
  comment ("Must NOT transitively invoke any LLM provider …") is
  self-checked by `lab/eval/tests/test_eval_ci_determinism.py`. If you
  reword the comment, update the regex in
  `EvalCiDeterminismTests.test_makefile_target_exists`. Removing the
  comment without updating the test is a drift defect; removing it
  without restoring an equivalent guard is a determinism-policy
  regression.
- **`plugins/ruby-grape-rails/references/run-manifest.md`** edited →
  also check `plugins/ruby-grape-rails/bin/manifest-update`
  (encodes the schema in `SKILL_CONVENTIONS` + `ALLOWED_PATH_RE`),
  `plugins/ruby-grape-rails/skills/review/SKILL.md`,
  `plugins/ruby-grape-rails/skills/review/references/review-playbook.md`,
  `plugins/ruby-grape-rails/skills/review/references/review-template.md`,
  `plugins/ruby-grape-rails/skills/plan/SKILL.md`,
  `plugins/ruby-grape-rails/skills/plan/references/planning-workflow.md`,
  `plugins/ruby-grape-rails/skills/brainstorm/SKILL.md`,
  `README.md` (How Review Works section + Artifact Layout),
  `CLAUDE.md` (Artifact Directories), `.claude/rules/skill-development.md`,
  `.claude/rules/agent-development.md`. Manifest schema, staleness
  rules, atomic-write protocol, and per-skill conventions must stay
  aligned across these surfaces. Per-run artifact paths use
  `{slug}-{datesuffix}.md` (review) or stable `{topic-slug}.md`
  (plan/brainstorm); a shipped reference to `{slug}.md` (without
  datesuffix) for review consolidated artifacts is a drift defect.
  A schema change without matching `bin/manifest-update`
  `SKILL_CONVENTIONS` update is a silent contract break.
- **`plugins/ruby-grape-rails/references/research/tool-batching.md`**
  edited → verify links from `.claude/rules/agent-development.md` §
  "Bash Discipline" and
  `plugins/ruby-grape-rails/skills/review/references/review-playbook.md`
  § "Diff strategy" still resolve. The tool-batching preference rule
  itself lives in `references/preferences.yml`; rule edits trigger
  preferences regeneration as documented above.

### How to surface drift findings

State the drift directly: "PR edits `<file A>` but unchanged `<file B>`
still references the old name/value. Also update `<file B>`."
Do not soften with "might want to" / "consider also" — drift is a
correctness defect, not a style suggestion.
