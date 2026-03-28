---
name: plugin-dev-workflow
description: Guide plugin development workflow for this repo. Use when editing shipped plugin files under plugins/ruby-grape-rails/, release/docs metadata, or contributor tooling under .claude/.
effort: medium
---

# Plugin Development Workflow

This repo contains both:

- shipped user-facing plugin code under `plugins/ruby-grape-rails/`
- contributor-only tooling under `.claude/`

Keep those surfaces separate in both implementation and validation.

## Scope Check

Before editing, decide which surface you are changing:

- shipped plugin:
  - skills
  - agents
  - hooks
  - plugin metadata
  - README / user-facing docs
- contributor tooling:
  - `.claude/skills/`
  - `.claude/agents/`
  - local planning/audit notes, if present

Do not treat contributor-only changes as shipped plugin features.

## Validation Matrix

Run the checks that match the files you touched:

- Markdown docs / skills / agents:
  - `npx markdownlint <touched-files>`
- Shell hooks:
  - `bash -n plugins/ruby-grape-rails/hooks/scripts/<file>.sh`
  - `shellcheck -x plugins/ruby-grape-rails/hooks/scripts/<file>.sh`
- Ruby scripts:
  - `ruby -c <file>`
- Shipped plugin shape:
  - `claude plugin validate plugins/ruby-grape-rails`

If multiple shipped surfaces changed, run the plugin validator plus the
file-type-specific checks.

## Release Discipline

When a change is user-visible:

1. update `CHANGELOG.md`
2. keep version metadata aligned across:
   - `package.json`
   - `.claude-plugin/marketplace.json`
   - `plugins/ruby-grape-rails/.claude-plugin/plugin.json`
3. update `README.md` / `CLAUDE.md` when counts, commands, or behavior changed

Rules:

- if the current version is already treated as released, new notes go under
  `Unreleased`
- if preparing the next release, move that work into the target version section

## Audit / Roadmap Maintenance

When contributor workflow direction or local planning/audit notes change:

- update local planning/audit notes, if present
- keep recommendations grounded in current Ruby implementation and current
  repo state

## Practical Defaults

- prefer small, verifiable patches over broad churn
- prefer CLI tools first, then Ruby, then ad-hoc Python only as a last resort
- keep shipped docs aligned with real implementation
- do not promote ignored local artifacts into tracked files unless they are
  genuinely reusable
