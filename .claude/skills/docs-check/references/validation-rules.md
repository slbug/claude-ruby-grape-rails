# Validation Rules

Use this file as a contributor checklist, not as a frozen schema snapshot.
When it conflicts with the cached docs in `.claude/docs-check/docs-cache/`, the
cached docs win.

## First Principles

1. Run `claude plugin validate plugins/ruby-grape-rails` first.
2. Treat the cached docs as the authority for current Claude Code behavior.
3. Separate schema truth from repo policy:
   - schema truth: whether Claude Code documents a field, event, or hook type
   - repo policy: whether this repo should adopt that capability
4. Do not file findings about naming style, line counts, or other local taste as
   docs-compatibility issues.

## Docs-Check Output Levels

| Level | Use for |
|-------|---------|
| `BLOCKER` | The plugin uses something current docs reject or no longer support |
| `WARNING` | Docs still allow it, but the pattern is deprecated, version-gated, or misleading |
| `INFO` | Docs now support something the repo may want to adopt |
| `PASS` | Current repo behavior matches current docs |

## Agent Validation

Authoritative cached docs:

- `plugins-reference.md` for plugin-shipped agent support
- `sub-agents.md` for tool syntax and agent behavior details

Current plugin-agent frontmatter supported by docs:

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

Important current constraints:

- `isolation` only documents `worktree`
- plugin-shipped agents do not support these frontmatter fields; if present,
  Claude currently ignores them when loading agents from a plugin:
  - `hooks`
  - `mcpServers`
  - `permissionMode`
- `Agent(...)` is the current syntax for restricting spawned subagents
  - `Task(...)` may still appear as historical alias in docs, but contributor
    guidance should prefer `Agent(...)`

Checks:

1. Confirm plugin agents only use fields currently documented for plugin agents.
2. Confirm `tools` / `disallowedTools` use currently documented tool names.
3. Confirm any `skills:` references point to real shipped skills.
4. Treat new documented fields as `INFO`, not as automatic repo defects.

## Skill Validation

Authoritative cached docs:

- `skills.md`
- `hooks.md` and `hooks-guide.md` for skill-scoped hooks

Current skill frontmatter supported by docs:

- `name`
- `description`
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

1. Flag undocumented skill frontmatter as a docs issue.
2. Do not flag documented fields such as `effort`, `paths`, or `shell`.
3. Continue treating `triggers:` as invalid because skills docs do not support
   it.
4. When `paths:` is present, confirm the glob patterns are repo-relevant rather
   than treating the field itself as suspicious.

## Hook Validation

Authoritative cached docs:

- `hooks.md`
- `hooks-guide.md`

Current documented hook events include:

- `SessionStart`
- `SessionEnd`
- `UserPromptSubmit`
- `PreToolUse`
- `PermissionRequest`
- `PostToolUse`
- `PostToolUseFailure`
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

Current documented hook types:

- `command`
- `http`
- `prompt`
- `agent`

Important current constraints:

- handler-level `if` filters are documented and useful
- `if` is version-gated:
  - requires Claude Code `v2.1.85+`
  - only works on tool events:
    - `PreToolUse`
    - `PostToolUse`
    - `PostToolUseFailure`
    - `PermissionRequest`
- `FileChanged` uses `matcher` for watched filenames, so do not lint it as a
  normal tool matcher only

Checks:

1. Confirm `hooks/hooks.json` only uses documented events and hook types.
2. Flag undocumented events and hook types as `BLOCKER`.
3. Treat `if` usage outside tool events as `WARNING` or `BLOCKER` depending on
   whether it disables the handler.
4. Validate `${CLAUDE_PLUGIN_ROOT}` references against real repo paths.
   - in this repo, those targets live under `plugins/ruby-grape-rails/...`
   - inside the packaged plugin root, the same files appear as paths like
     `hooks/hooks.json` or `.claude-plugin/plugin.json`

## Plugin Config Validation

Authoritative cached docs:

- `plugins-reference.md`
- `plugin-marketplaces.md`
- `plugins.md`
- `mcp.md`
- `settings.md` only when a finding depends on settings semantics

Checks for `.claude-plugin/plugin.json`:

1. Confirm required manifest structure still matches current docs.
2. Treat these as currently documented plugin capabilities when present:
   - `hooks`
   - `mcpServers`
   - `outputStyles`
   - `lspServers`
   - `userConfig`
   - `channels`
3. When validating path behavior, remember:
   - custom `commands`, `agents`, `skills`, and `outputStyles` replace defaults
   - arrays can keep the default path and add extras
4. When validating environment-variable guidance, distinguish:
   - `${CLAUDE_PLUGIN_ROOT}` for bundled files
   - `${CLAUDE_PLUGIN_DATA}` for persistent state that survives plugin updates

Checks for `.claude-plugin/marketplace.json`:

1. Confirm plugin entries still use documented source shapes.
2. Flag broken relative paths or malformed source objects.
3. Treat marketplace metadata gaps as repo policy issues unless current docs
   make them invalid.

## Recommended Validation Flow

1. Run deterministic plugin validation.
2. Identify the exact docs question:
   - agent schema
   - skill frontmatter
   - hooks
   - manifest / marketplace
3. Read only the cached doc sections that answer that question.
4. Compare only the relevant plugin file snippets.
5. Classify each finding as:
   - docs incompatibility
   - repo recommendation
   - false alarm caused by stale local guidance
