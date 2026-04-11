# Development Workflow

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

- `npm run validate` — plugin structure and manifest
- `python3 scripts/check-release-metadata.py` — version alignment + changelog integrity
- Both should pass before committing

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
