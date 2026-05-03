---
applyTo: "**/*.md"
excludeAgent: "coding-agent"
---

# Markdown File Review Rules

## Audience: Agents, Not Humans

Markdown in this repo loads into agent context at runtime. Flag
prose that violates the imperative-only rule:

- Tutorial narration ("first do X, then Y, this teaches…") → flag
- Reasoning preludes before commands → flag
- `#` thinking/checklist lines inside Bash command bodies
  (preference #6) → flag, suggest markdown table or prose lead-in
- Long explanatory paragraphs where a table fits → flag

Exception files (human-facing, narrative OK): `README.md`,
`CHANGELOG.md`, files under `scripts/` (executable code), files
under `lab/eval/` (test fixtures).

## Skill and Agent Frontmatter

Files under `plugins/**/skills/` and `plugins/**/agents/` use YAML
frontmatter between `---` delimiters. This is Claude Code plugin syntax,
not standard markdown metadata.

Valid frontmatter fields for skills: name, description, when_to_use,
argument-hint, arguments, effort, disable-model-invocation,
user-invocable, allowed-tools, model, context, agent, hooks, paths,
shell

Valid frontmatter fields for agents (general subagent surface, see
<https://docs.claude.com/en/docs/claude-code/sub-agents>): name,
description, model, effort, maxTurns, tools, disallowedTools, skills,
memory, background, isolation, omitClaudeMd, color, initialPrompt.
Plugin-shipped agents under `plugins/**/agents/` are narrowed by the
plugins reference
(<https://docs.claude.com/en/docs/claude-code/plugins-reference>) to
the subset CC honors on plugin agents — do not add `color` or
`initialPrompt` to plugin-shipped agents (see
`plugin-review.instructions.md` for the narrowed set).

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

- `README.md` Iron Laws section (`IRON_LAWS_START/END` markers)
- `plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md`
  (whole-file generation; no markers)
- `plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`
  Iron Laws walkthrough block (`IRON_LAWS_START/END` markers)
- `plugins/ruby-grape-rails/agents/iron-law-judge.md` Iron Laws roster
  (`IRON_LAWS_JUDGE_START/END` markers)
- `plugins/ruby-grape-rails/hooks/scripts/inject-rules.sh` (whole-file
  generation; carries `Source versions: iron-laws=<v> preferences=<v>`
  in the header — verify the version pair matches source YAML)

The init injectable template
(`plugins/ruby-grape-rails/skills/init/references/injectable-template.md`)
no longer ships `IRON_LAWS_START/END` or `PREFERENCES_START/END` blocks
— Iron Laws + Preferences are delivered at runtime via the
`inject-rules.sh` hook (wired to both `SessionStart` and
`SubagentStart`), not inline in CLAUDE.md.

## Cross-File Drift Around Markdown Changes

- Skill or agent renamed / removed / new → check
  `intro/references/tutorial-content.md`,
  `init/references/injectable-template.md`, README, CHANGELOG, and
  other skills' `/rb:<name>` mentions. For agent removals, also check
  skill-body fanout owners
  (`plugins/ruby-grape-rails/skills/{review,plan,full}/SKILL.md`,
  `.claude/skills/docs-check/SKILL.md`) and agent count claims.
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
