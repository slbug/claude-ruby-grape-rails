---
applyTo: "plugins/**"
excludeAgent: "coding-agent"
---

# Plugin File Review Rules

## Agent Conventions (plugins/**/agents/*.md)

- Agents use YAML frontmatter. Common: name, description, model,
  disallowedTools, omitClaudeMd, skills, memory. Also valid per CC docs:
  tools, effort, maxTurns, background, isolation, color, initialPrompt
- Prefer denylist-only (`disallowedTools:`) over allowlist (`tools:`).
  A missing `tools:` field is intentional — agents inherit all tools minus
  those in disallowedTools
- Artifact-writing agents: `disallowedTools: Edit, NotebookEdit, Agent,
  EnterWorktree, ExitWorktree, Skill`
- Conversation-only agents add `Write` to the above
- `parallel-reviewer` keeps `Agent` (spawns sub-reviewers) — this is correct
- Agents with intentionally narrow tool sets (web-researcher,
  output-verifier, ruby-gem-researcher) use `tools:` allowlists — this is
  correct
- `omitClaudeMd: true` is correct for specialist agents that do not need
  contributor CLAUDE.md context
- Do NOT flag `permissionMode` as missing — Claude Code ignores it on
  plugin agents
- Model tiers: opus for primary orchestrators, sonnet for most specialists,
  haiku for mechanical tasks
- Descriptions must be <= 250 characters

## Skill Conventions (plugins/**/skills/*/SKILL.md)

- Skills use YAML frontmatter. Required: name, description. Common:
  argument-hint (command skills), effort, user-invocable,
  disable-model-invocation, paths (framework-specific skills). Also valid
  per CC docs: allowed-tools, model, context, agent, hooks, shell
- No `triggers:` field — skills docs do not support it
- No executable bash blocks (``` bash) — use inline prose instructions
  instead ("Run `bundle exec rspec`")
- Descriptions must be <= 250 characters
- `${CLAUDE_SKILL_DIR}` is a valid runtime variable, not an error
- Iron Laws sections contain numbered non-negotiable rules — do not suggest
  making them optional or softer
- Large orchestrator/workflow skills (300+ lines) are acceptable when they
  must embed subagent prompts inline

## Hook Conventions (plugins/**/hooks/)

- hooks.json uses documented Claude Code hook events and types
- Each `if` filter uses a single pattern per hook entry — do NOT combine
  with `|` OR syntax
- `async: true` is only valid on `type: "command"` hooks
- `${CLAUDE_PLUGIN_ROOT}` is a valid runtime variable in hook commands

## Do NOT Flag

- Large file sizes on orchestrators or workflow skills (intentional)
- Missing `tools:` field on agents (denylist-only pattern)
- `omitClaudeMd: true` on specialist agents (intentional context savings)
- Colon-namespaced skill names like `rb:plan` (known compatibility item)
- `memory: project` on orchestrator agents (intentional cross-session learning)
