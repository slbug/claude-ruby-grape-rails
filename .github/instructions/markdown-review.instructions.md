---
applyTo: "**/*.md"
excludeAgent: "coding-agent"
---

# Markdown File Review Rules

## Skill and Agent Frontmatter

Files under `plugins/**/skills/` and `plugins/**/agents/` use YAML
frontmatter between `---` delimiters. This is Claude Code plugin syntax,
not standard markdown metadata.

Valid frontmatter fields for skills: name, description, argument-hint,
effort, disable-model-invocation, user-invocable, allowed-tools, model,
context, agent, hooks, paths, shell

Valid frontmatter fields for agents: name, description, model, effort,
maxTurns, tools, disallowedTools, skills, memory, background, isolation,
omitClaudeMd, color, initialPrompt

## Runtime Variables

These are NOT errors — they are resolved at runtime by Claude Code:

- `${CLAUDE_SKILL_DIR}` — path to the skill's own directory
- `${CLAUDE_PLUGIN_ROOT}` — path to the plugin root
- `${CLAUDE_PLUGIN_DATA}` — persistent plugin data directory

## Consistency Checks

- Skill description + when_to_use combined must be <= 1,536 characters
- Agent description must be <= 250 characters
- Skill names use `rb:` prefix for user-invocable commands
- Agent names use plain kebab-case (no prefix)
- References to other skills use `/rb:name` format
- References to agents use `subagent_type` format

## CHANGELOG Conventions

- Format: Keep a Changelog (<https://keepachangelog.com/>)
- Categories: Added, Changed, Fixed, Removed
- Version links at bottom must include all version entries
- Versions must align across plugin.json, marketplace.json, package.json

## Do NOT Flag

- Inline backtick commands in skills (e.g., "Run `bundle exec rspec`") —
  this is the correct pattern replacing bash blocks
- Long numbered lists in Iron Laws sections
- `<!-- -->` HTML comments (used for markdownlint control)
- Files under `.claude/` (contributor tooling, not shipped)
- `paths:` YAML frontmatter in `.claude/rules/*.md` (path-scoped rules)
