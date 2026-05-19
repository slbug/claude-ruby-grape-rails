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

Documented for general subagents but silently dropped on plugin-shipped
agents — do NOT recommend in plugin agent frontmatter:

- `color` — listed in general `--agents` JSON spec; plugin-supported
  set in `plugins-reference.md` does NOT include it
- `initialPrompt` — fires only when an agent runs as the main session
  agent via `--agent` / settings; inert for plugin subagents

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

Currently-supported skill frontmatter (per agentskills.io canon):

- `name`
- `description` (single field; replaces former `description` + `when_to_use` split)
- `argument-hint`
- `disable-model-invocation`
- `user-invocable`
- `allowed-tools`
- `model`
- `effort`
- `context`
- `agent`
- `hooks`
- `shell`

Notes:

- `when_to_use` is no longer a supported field — content folds into the
  single `description` field
- `paths:` is documented in CC skill schema but empirically non-functional
  at plugin scope; project-level `.claude/rules/*.md` `paths:` is a
  separate, functional mechanism
- Colon in `name` (e.g., `rb:plan`) is repo policy via the frontmatter
  `name` field. Cached `skills.md` § Frontmatter reference documents
  the charset as lowercase letters, numbers, hyphens only; repo accepts
  colons in practice. Migration to hyphen names with aliases is the
  fallback if CC enforces the documented charset. Treat as INFO (repo
  policy override of doc charset), NOT a WARNING — see
  `.claude/rules/skill-development.md` § "Colon Naming"
- **Two substitution layers, not one.** Skill substitution questions
  REQUIRE reading BOTH cached pages — `skills.md` covers only
  skill-scope dynamic values; `plugins-reference.md` § "Environment
  variables" covers plugin-scope path variables. Conflating the layers
  produces false-positive WARNINGS:

  | Layer | Source page | Variables |
  |---|---|---|
  | Skill-scope dynamic | `skills.md` § Available string substitutions | `$ARGUMENTS`, `$N`, `$name`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}` |
  | Plugin-scope path | `plugins-reference.md` § Environment variables | `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}` |

  Plugin-scope variables are substituted in skill content, agent
  content, hook commands, monitor commands, and MCP/LSP server configs
  per `plugins-reference.md`. Use in SKILL.md prose or bash injection
  is fully documented behavior, NOT drift.

- **Marketplace plugin entries inherit the full plugin.json schema.**
  `plugin-marketplaces.md` § "Plugin entries" states: "You can include
  any field from the plugin manifest schema". The quick-summary table
  row "(`name` required, `email` optional)" is shorthand, NOT the
  authoritative author shape. Authoritative `author` schema lives in
  `plugins-reference.md` § "Plugin manifest schema" and includes
  `name`, `email`, `url`. Do NOT flag `author.url` in
  `marketplace.json` as drift.

- **Artifact-writing agents intentionally retain `Write`.** Per
  `.claude/rules/agent-development.md` § "Tool Access":
  artifact-writing agents add `Edit, NotebookEdit` to `disallowedTools`
  (NOT `Write`); conversation-only agents add `Write` on top. Plugin
  reviewer agents (ruby-reviewer, migration-safety-reviewer,
  security-analyzer, testing-reviewer, iron-law-judge,
  data-integrity-reviewer, etc.) AND the two researcher agents
  (web-researcher, ruby-gem-researcher) write their artifact to the
  absolute path passed in the spawn prompt — Write is the canonical
  output channel. Convo-only specialists (e.g. output-verifier,
  active-record-schema-designer, call-tracer, dependency-analyzer)
  return text; main session persists any artifact. Do NOT flag missing
  `Write` in `disallowedTools` for artifact-writing agents. Verify by
  cross-checking sibling agents in the same directory before
  classifying as drift.

Checks:

1. Flag undocumented skill frontmatter as docs issue.
2. Do NOT flag documented fields (`effort`, `shell`).
3. Continue treating `triggers:` as invalid — skills docs do not support it.
4. Flag `when_to_use:` on a plugin SKILL.md as drift — single `description` only.
5. Flag plugin-scope `paths:` as drift (non-functional at plugin scope).
6. Colon names (`rb:<slug>`) are repo policy — classify INFO, not WARNING.
7. Skill `description` over 1,024 characters → `ERROR` (agentskills.io cap).
   Over 250 characters → `WARNING` (cached docs say Claude truncates them
   in skill listing).

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
