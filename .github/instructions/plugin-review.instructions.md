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
  disable-model-invocation, paths (framework-specific skills),
  when_to_use (trigger phrases and negative routing). Also valid per CC
  docs: allowed-tools, model, context, agent, hooks, shell
- No `triggers:` field — skills docs do not support it
- No executable bash blocks (``` bash) — use inline prose instructions
  instead ("Run `bundle exec rspec`")
- Combined description + when_to_use must be <= 1,536 characters
- Descriptions should start with "Use when" for consistent routing signal
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

## bin/ Executables (plugins/**/bin/*)

- No file extension, chmod +x
- Header policy comment near the top documents advisory vs fail-closed
  behavior
- `set -o nounset` + `set -o pipefail` at the top
- `command -v <dep> >/dev/null 2>&1 || exit 0` for optional deps
- Advisory fail-open pattern (empty stdout, exit 0 on any error) is
  intentional for statusline and similar advisory executables — do NOT
  flag as "missing error handling"
- From `hooks.json`, `.mcp.json`, `monitors/monitors.json`, template
  expansion is supported; reference bundled scripts via
  `${CLAUDE_PLUGIN_ROOT}/...`

## Plugin Settings (plugins/**/settings.json)

- Only `agent` and `subagentStatusLine` keys are supported per CC docs
  (`plugins-reference.md` standard plugin layout)
- Unknown keys are silently ignored by CC — do NOT flag partial coverage
  of other settings fields
- `subagentStatusLine.command` does NOT expand `${CLAUDE_PLUGIN_ROOT}`
  and CC does NOT export `CLAUDE_PLUGIN_ROOT` to the statusline
  subprocess nor add plugin `bin/` to its PATH. Plugin-bundled
  statusline scripts therefore require a SessionStart hook that writes
  a small wrapper at `~/.claude/<plugin-id>-subagent-statusline`
  pointing at the current absolute plugin path. The plugin
  `settings.json` then references that stable user-home path. The
  wrapper must be rewritten only when its content differs from the
  desired content (plugin version changes change the absolute path).
  Do NOT flag this indirection as unnecessary — it is required by the
  documented CC substitution scope

### subagentStatusLine payload schema (as observed, not fully documented)

The statusline subprocess receives base hook fields plus `columns` and a
`tasks[]` array. Each task provides `id`, `type` (e.g. `local_agent`),
`status`, `description`, `label` (usually the same text as `description`),
`startTime` as epoch milliseconds (13-digit integer), `tokenCount`,
`tokenSamples` as a number array, and `cwd`. The docs also list `.name`
but current CC payloads do NOT include it — match emoji/label from
`.label` first, falling back to `.description` and finally `.name`. Do
NOT flag the fallback chain as over-engineered.

## Do NOT Flag

- Large file sizes on orchestrators or workflow skills (intentional)
- Missing `tools:` field on agents (denylist-only pattern)
- `omitClaudeMd: true` on specialist agents (intentional context savings)
- Colon-namespaced skill names like `rb:plan` (known compatibility item)
- `memory: project` on orchestrator agents (intentional cross-session learning)
- Advisory fail-open (empty stdout, exit 0) in `bin/` and advisory hooks
- Partial coverage in plugin `settings.json` (only `agent` and
  `subagentStatusLine` are documented as supported)
