---
name: plugin-dev-workflow
description: Guide plugin development workflow for this repo. Use when editing shipped plugin files under plugins/ruby-grape-rails/, release/docs metadata, or contributor tooling under .claude/.
effort: medium
---

# Plugin Development Workflow

## Audience: Agents, Not Humans

Imperative-only. Tables for command/option lists.

## Surface Boundary

Two surfaces, kept separate in implementation + validation:

| Surface | Path |
|---|---|
| shipped plugin | `plugins/ruby-grape-rails/` |
| contributor-only tooling | `.claude/` |

Supported environments: macOS, Linux, WSL. Native Windows: NOT supported.

Session analytics under `.claude/skills/session-*` and
`.claude/skills/skill-monitor/`: exploratory only, NOT release-grade.

## Scope Check

Before editing, identify the surface:

| Layer | Files |
|---|---|
| shipped plugin | skills, agents, hooks, `bin/`, plugin `settings.json`, plugin metadata, README, user-facing docs |
| contributor tooling | `.claude/skills/`, `.claude/agents/`, local planning/audit notes |

Do NOT treat contributor-only changes as shipped plugin features.

## Validation Matrix

Run checks matching the files touched:

| Files touched | Run |
|---|---|
| Markdown docs / skills / agents | `npx markdownlint <touched-files>` |
| Shell hooks | `bash -n plugins/ruby-grape-rails/hooks/scripts/<file>.sh`, `shellcheck -x plugins/ruby-grape-rails/hooks/scripts/<file>.sh` |
| `bin/` executables | `bash -n plugins/ruby-grape-rails/bin/<name>`, `shellcheck plugins/ruby-grape-rails/bin/<name>`, mock-test via crafted stdin when the executable reads hook-style JSON |
| Ruby scripts | `ruby -c <file>` |
| Shipped plugin shape | `claude plugin validate plugins/ruby-grape-rails` |
| Contributor eval tooling | `make eval`, `make eval-all`, `make eval-ci-deterministic`, `make eval-output`, `make security-injection`, `make eval-tests`, `make eval-overlap`, `make eval-hard-corpus` |

Multiple shipped surfaces touched → run plugin validator + file-type-specific checks.

Trust order before contributor-analytics conclusions:

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `make eval-output` (deterministic research/review artifact fixtures)
4. `/docs-check` when Claude docs / plugin schema assumptions may have changed
5. session-derived analytics — corroborating evidence only

When `lab/eval/` changes, also run:

- `python3` 3.14+ (eval tooling floor)
- `python3 -m compileall lab/eval`
- `bash scripts/run-eval-tests.sh`
- `python3 -m lab.eval.artifact_scorer --all`
- `python3 -m pytest lab/eval/tests -v` when `pytest` installed

For research/review artifact changes, consult
`${CLAUDE_SKILL_DIR}/references/output-verification-checklist.md`.

## Release Discipline

User-visible change steps:

1. Update `CHANGELOG.md`.
2. Align version metadata across:
   - `package.json`
   - `.claude-plugin/marketplace.json`
   - `plugins/ruby-grape-rails/.claude-plugin/plugin.json`
3. Update `README.md` / `CLAUDE.md` when counts, commands, or behavior changed.

Routing:

| State | Section |
|---|---|
| current version already released | new notes go under `Unreleased` |
| preparing next release | move work into target version section |

## Audit / Roadmap Maintenance

Contributor workflow direction or local planning/audit notes change:

- update local planning/audit notes
- keep recommendations grounded in current Ruby implementation + repo state

## Practical Defaults

- prefer small, verifiable patches over broad churn
- prefer CLI tools first, then Ruby, then ad-hoc Python only as last resort
- `rm -f` only for `mktemp` outputs or exact fixed plugin-owned paths
- `rm -rf` only for validated `mktemp -d` outputs; prefer `rmdir` for expected-empty lock dirs
- variable-based cleanup → require both path validation + `${var:?}`
- keep shipped docs aligned with real implementation
- do NOT promote ignored local artifacts into tracked files unless genuinely reusable
