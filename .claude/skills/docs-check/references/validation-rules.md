# Validation Rules

## Audience: Agents, Not Humans

Contributor checklist, not frozen schema snapshot. When this file
conflicts with cached docs in `.claude/docs-check/docs-cache/`, cached
docs win.

## First Principles

1. Run `claude plugin validate plugins/ruby-grape-rails` first.
2. Cached docs are the authority for current Claude Code behavior.
3. Separate schema truth from repo policy:

   | Layer | Definition |
   |---|---|
   | schema truth | whether Claude Code documents a field, event, or hook type |
   | repo policy | whether this repo should adopt that capability |

4. Do NOT file naming style / line count / local taste as docs-compatibility issues.

## Docs-Check Output Levels

| Level | Use for |
|-------|---------|
| `BLOCKER` | plugin uses something current docs reject or no longer support |
| `WARNING` | docs allow it, but pattern is deprecated, version-gated, or misleading |
| `INFO` | docs now support something repo may want to adopt |
| `PASS` | current repo behavior matches current docs |

## Agent Validation

Authoritative cached docs:

- `plugins-reference.md` — plugin-shipped agent support
- `sub-agents.md` — tool syntax + agent behavior

### Agent / Skill Boundary Rule

| Surface | Rule |
|---|---|
| Agent frontmatter (`plugins/**/agents/*.md`, `.claude/agents/*.md`) | `tools:` MUST NOT include `Agent`. Body MUST NOT contain `Agent(...)` / `subagent_type:` calls. BLOCKER if found. |
| Skill bodies + skill references (`plugins/**/skills/*/SKILL.md`, `plugins/**/skills/*/references/*.md`, `.claude/skills/*/SKILL.md`) | MAY contain `Agent(...)` calls when describing main-session fanout. Allowed. |

Source: `sub-agents.md` (cached docs).

Currently-supported plugin-agent frontmatter:

- `name`
- `description`
- `model`
- `effort`
- `maxTurns`
- `tools`
- `disallowedTools`
- `skills`
- `memory`
- `background`
- `isolation`

Important constraints:

- `isolation` only documents `worktree`
- plugin-shipped agents do NOT support these fields (CC silently drops):
  - `hooks`
  - `mcpServers`
  - `permissionMode`
- `Agent(...)` is current syntax for restricting spawned subagents
  - `Task(...)` may appear as historical alias in docs; contributor guidance prefers `Agent(...)`
- `omitClaudeMd` is repo policy (not cached-docs baseline) unless cached docs document it later

Checks:

1. Confirm plugin agents only use fields currently documented for plugin agents.
2. Confirm `tools` / `disallowedTools` use currently documented tool names. Missing `tools:` is expected (denylist-only) — agent inherits all tools minus `disallowedTools`.
3. Confirm `skills:` references point to real shipped skills.
4. `omitClaudeMd` enforcement is repo policy unless cached docs explicitly document it.
5. New documented fields → `INFO`, not automatic repo defects.

## Skill Validation

Authoritative cached docs:

- `skills.md`
- `hooks.md` + `hooks-guide.md` (skill-scoped hooks)

Currently-supported skill frontmatter:

- `name`
- `description`
- `when_to_use`
- `argument-hint`
- `disable-model-invocation`
- `user-invocable`
- `allowed-tools`
- `model`
- `effort`
- `context`
- `agent`
- `hooks`
- `paths`
- `shell`

Checks:

1. Flag undocumented skill frontmatter as docs issue.
2. Do NOT flag documented fields (`effort`, `paths`, `shell`).
3. Continue treating `triggers:` as invalid — skills docs do not support it.
4. `paths:` present → confirm globs are repo-relevant; do NOT treat the field as suspicious.
5. Skill descriptions over 250 characters → `WARNING` (cached docs say Claude truncates them in skill listing).

## Hook Validation

Authoritative cached docs:

- `hooks.md`
- `hooks-guide.md`

Documented hook events:

- `Setup`
- `SessionStart`
- `SessionEnd`
- `UserPromptSubmit`
- `UserPromptExpansion`
- `PreToolUse`
- `PermissionRequest`
- `PermissionDenied`
- `PostToolUse`
- `PostToolUseFailure`
- `PostToolBatch`
- `Notification`
- `SubagentStart`
- `SubagentStop`
- `TaskCreated`
- `TaskCompleted`
- `Stop`
- `StopFailure`
- `TeammateIdle`
- `InstructionsLoaded`
- `ConfigChange`
- `CwdChanged`
- `FileChanged`
- `WorktreeCreate`
- `WorktreeRemove`
- `PreCompact`
- `PostCompact`
- `Elicitation`
- `ElicitationResult`

Documented hook types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.

Important constraints:

| Constraint | Detail |
|---|---|
| handler-level `if` filters | documented + useful |
| `if` version gate | requires CC `v2.1.85+`, only works on tool events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest` |
| `FileChanged` matcher | matcher = watched filenames (NOT a tool matcher); do not lint as one |
| `async` | documented only for `type: "command"` hooks |
| async control | async hooks cannot block / control Claude after start; `decision`, `permissionDecision`, `continue` MUST NOT be treated as meaningful on async handlers |

Checks:

1. Confirm `hooks/hooks.json` only uses documented events + types.
2. Flag undocumented events / hook types as `BLOCKER`.
3. `if` outside tool events → `WARNING` or `BLOCKER` (depending on whether handler is disabled).
4. Async on non-`command` hooks → docs issue.
5. Async hook + control output → not supported unless cached docs explicitly say.
6. Validate `${CLAUDE_PLUGIN_ROOT}` references against real repo paths:

   | Context | Path |
   |---|---|
   | this repo | `plugins/ruby-grape-rails/...` |
   | packaged plugin root | `hooks/hooks.json`, `.claude-plugin/plugin.json` |

## Plugin Config Validation

Authoritative cached docs:

- `plugins-reference.md`
- `plugin-marketplaces.md`
- `plugins.md`
- `mcp.md`
- `settings.md` (only when finding depends on settings semantics)

Checks for `.claude-plugin/plugin.json`:

1. Confirm required manifest structure matches current docs.
2. Currently-documented capabilities (when present):
   - `hooks`
   - `mcpServers`
   - `outputStyles`
   - `lspServers`
   - `userConfig`
   - `channels`
3. Path behavior:
   - custom `commands`, `agents`, `skills`, `outputStyles` REPLACE defaults
   - arrays can keep default path + add extras
4. Environment-variable distinction:

   | Variable | Use |
   |---|---|
   | `${CLAUDE_PLUGIN_ROOT}` | bundled files |
   | `${CLAUDE_PLUGIN_DATA}` | persistent state surviving plugin updates |

Checks for `.claude-plugin/marketplace.json`:

1. Confirm plugin entries use documented source shapes.
2. Flag broken relative paths / malformed source objects.
3. Marketplace metadata gaps → repo policy issues unless current docs make them invalid.

## Recommended Validation Flow

1. Run deterministic plugin validation.
2. Identify the docs question:
   - agent schema
   - skill frontmatter
   - hooks
   - manifest / marketplace
3. Read only the cached doc sections that answer the question.
4. Compare only relevant plugin file snippets.
5. Classify each finding:
   - docs incompatibility
   - repo recommendation
   - false alarm caused by stale local guidance
