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
- **Hooks** (`plugins/ruby-grape-rails/hooks/hooks.json` + `scripts/*.sh`):
  Shell scripts triggered by Claude Code events (PostToolUse, SessionStart, etc).
- **Eval** (`lab/eval/`): Deterministic Python eval framework for plugin quality.
- **Contributor tooling** (`.claude/`): Not shipped with the plugin.
  Includes `.claude/rules/` (auto-loaded context rules, some path-scoped)
  and `.claude/skills/` (contributor-only skills).

## What CI Already Checks

Do not flag issues already caught by CI:

- Markdown linting (markdownlint)
- Shell linting (shellcheck)
- JSON/YAML validation
- Plugin manifest validation (`claude plugin validate`)
- Eval scoring gate (`make eval-ci`)
- Release metadata alignment (`check-release-metadata.py`)
- Dynamic injection scanning (`check-dynamic-injection.sh`)

## Review Priorities

- CRITICAL: Security vulnerabilities, data loss risks, breaking plugin schema
- IMPORTANT: Convention violations, missing frontmatter, incorrect tool access
- SUGGESTION: Readability improvements, description wording, minor optimizations
