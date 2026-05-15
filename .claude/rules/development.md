# Development Workflow

## Audience: Agents, Not Humans

Imperative-only. Tables for command/option lists.

## Setup

- `npm ci` — install dependencies with committed lockfile
- `npm run doctor` — verify shellcheck, Claude CLI, python3/ruby/jq, optional betterleaks

## Testing Locally

- `claude --plugin-dir ./plugins/ruby-grape-rails` — test local working-tree changes directly
- Marketplace install flow: `/plugin marketplace add .` then `/plugin install ruby-grape-rails`
  (uses git-subdir source, not uncommitted working tree)

## Testing Workflow

- `/rb:plan Test feature` then check `.claude/plans/` for checkbox plan
- `/rb:work .claude/plans/test-feature/plan.md` then check checkboxes update and progress logged

## Linting

- `npm run lint` — full local lint/validation bundle
- `npm run lint:markdown` — markdown only
- `npm run lint:fix` — auto-fix issues

## Validation

- `python3 -m pip install -r requirements-dev.txt` — run once per local environment before any `python3 -m lab.eval...` invocation. CI re-installs on every lint and eval job.
- `npm run validate` — plugin structure and manifest
- `python3 scripts/check-release-metadata.py` — version alignment + changelog integrity
- `npm run check:refs` — cross-reference, registry, orphan, traversal, and broken-path gates (failure-by-default)
- `claude plugin details ruby-grape-rails` — component inventory + projected per-session token cost
- All checks should pass before committing

## Adding a New Agent

1. Create `plugins/ruby-grape-rails/agents/{name}.md`
2. Add frontmatter with all required fields (model, description, tools/disallowedTools)
3. Target under 300 lines when practical

## Adding a New Skill

1. Create `plugins/ruby-grape-rails/skills/{name}/SKILL.md` (prefer ~100-200 lines)
2. Create `references/` directory with detailed content
3. For workflow skills, document integration with the plan/work/review/compound cycle

## Output Artifact Eval

- `make eval-output` or `npm run eval:output`
- Scores tracked fixture artifacts under `lab/eval/fixtures/output/`
- Canonical contributor check for provenance/report contract changes

## Deterministic-First Ordering

For skill / agent / hook quality assessment, run in order:

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval-ci-deterministic`
3. `make eval-output`
4. `/docs-check`
5. Session analytics (`.claude/skills/session-scan/`, `skill-monitor`) — heuristic, observational

Do NOT draw conclusions from session analytics alone. Corroborate via
deterministic eval signals or manual transcript review.
