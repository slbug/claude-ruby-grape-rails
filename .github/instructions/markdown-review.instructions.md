---
applyTo: "**/*.md"
excludeAgent: "coding-agent"
---

# Markdown File Review Rules

## Skill and Agent Frontmatter

Files under `plugins/**/skills/` and `plugins/**/agents/` use YAML
frontmatter between `---` delimiters. This is Claude Code plugin syntax,
not standard markdown metadata.

Valid frontmatter fields for skills: name, description, when_to_use,
argument-hint, effort, disable-model-invocation, user-invocable,
allowed-tools, model, context, agent, hooks, paths, shell

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

## Generated Markdown Sections

These markdown blocks are generated from
`plugins/ruby-grape-rails/references/iron-laws.yml` and
`preferences.yml` via `scripts/generate-iron-law-outputs.sh`. Do not
hand-edit; flag PRs that change them without a matching YAML edit:

- `README.md` Iron Laws section
- `plugins/ruby-grape-rails/skills/init/references/template.md`
  `IRON_LAWS_START/END` and `PREFERENCES_START/END` blocks
- `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`
  Iron Laws walkthrough block
- `plugins/ruby-grape-rails/agents/iron-law-judge.md` Iron Laws roster

## Cross-File Drift Around Markdown Changes

- Skill or agent renamed → check `intro/references/tutorial-content.md`,
  `init/references/template.md`, README, CHANGELOG, and other skills'
  `/rb:<name>` mentions
- Iron Law count claim ("22 Total", "N Iron Laws") in any markdown →
  verify against `plugins/ruby-grape-rails/references/iron-laws.yml`
- Plugin version mentioned in markdown → align with manifest trio
- New skill / agent → CLAUDE.md skill/agent counts and intro tutorial
  must be updated in the same PR

## Do NOT Flag

- Inline backtick commands in skills (e.g., "Run `bundle exec rspec`") —
  this is the correct pattern replacing bash blocks
- Long numbered lists in Iron Laws sections
- `<!-- -->` HTML comments (used for markdownlint control)
- Files under `.claude/` (contributor tooling, not shipped)
- `paths:` YAML frontmatter in `.claude/rules/*.md` (path-scoped rules)
- `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_DATA}`
  in skill or hook prose (runtime variables, not unresolved templates)
