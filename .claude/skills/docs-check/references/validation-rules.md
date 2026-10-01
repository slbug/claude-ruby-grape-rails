# Validation Rules

## Audience: Agents, Not Humans

Contributor checklist, not frozen schema snapshot. When this file
conflicts with cached docs in `.claude/docs-check/docs-cache/`, cached
docs win.

## First Principles

1. Run `claude plugin validate --strict plugins/ruby-grape-rails` and
   `claude plugin validate --strict .` first. `--strict` turns
   unrecognized-field warnings into errors; the marketplace manifest needs
   its own run. A bogus hook event name fails as
   `hooks.<Name>: Invalid key in record`, so the validator is authoritative
   on event names even when `hooks.md` lags.
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

- `plugins/components.md` § "Frontmatter fields in plugin agents" —
  plugin-shipped agent support
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
- `omitClaudeMd`
- `isolation`
- `color`
- `experimental.cacheTtl` (the only supported `experimental` key)

Ignored on plugin-shipped agents (CC drops them) — do NOT recommend in
plugin agent frontmatter:

- `permissionMode`
- `hooks`
- `mcpServers`
- `initialPrompt`

Important constraints:

- `isolation` only documents `worktree`
- `Agent(...)` is current syntax for restricting spawned subagents
  - `Task(...)` may appear as historical alias in docs; contributor guidance prefers `Agent(...)`
- `omitClaudeMd` is documented. Requiring it on every shipped specialist
  is repo policy (`.claude/rules/agent-development.md`)
- `effort` only applies on models `model-config.md` § effort levels
  lists. That table currently omits Haiku, and the page states models
  absent from it do not support effort. `effort` on such a model is
  inert configuration — classify `WARNING` (dead config), never
  `BLOCKER`, since the field itself stays documented

Checks:

1. Confirm plugin agents only use fields currently documented for plugin agents.
2. Confirm `tools` / `disallowedTools` use currently documented tool names. Missing `tools:` is expected (denylist-only) — agent inherits all tools minus `disallowedTools`.
3. Confirm `skills:` references point to real shipped skills.
4. Missing `omitClaudeMd: true` on a shipped specialist is a repo-policy finding, not docs drift.
5. New documented fields → `INFO`, not automatic repo defects.

## Skill Validation

Authoritative cached docs:

- `skills.md`
- `hooks.md` + `hooks-guide.md` (skill-scoped hooks)

Currently-supported skill frontmatter (cached `skills.md` § Frontmatter
reference):

- `name`
- `description` (single field — repo policy; see the `when_to_use` note below)
- `when_to_use` (documented; repo avoids it)
- `argument-hint`
- `arguments`
- `disable-model-invocation`
- `user-invocable`
- `allowed-tools`
- `disallowed-tools`
- `model`
- `effort`
- `context`
- `agent`
- `background` (only with `context: fork`)
- `hooks`
- `paths` (documented; see the plugin-scope note below)
- `shell`
- `metadata`
- `license`
- `compatibility`

Notes:

- `when_to_use` is REPO POLICY to avoid, not a removed Claude Code
  field. Cached `skills.md` § Frontmatter reference still documents it
  (appended to `description` in the skill listing, counted toward the
  combined listing cap). Avoid it because the portable agentskills.io
  set — `name`, `description`, `license`, `compatibility`, `metadata`,
  `allowed-tools` — excludes it, so a skill using it stops being
  portable to claude.ai uploads, the Skills API, and `package_skill.py`.
  Fold the content into the single `description` field. Encountering
  `when_to_use` on a plugin SKILL.md is a repo-policy finding, NOT a
  docs incompatibility
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
  `plugins/marketplace-reference.md` § "Plugin entries" states: "An
  entry also accepts every `plugin.json` field". Authoritative `author`
  schema lives in `plugins-reference.md` (manifest reference) field
  table: `name` required, optional `email` and `url`. Do NOT flag
  `author.url` in `marketplace.json` as drift.

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
4. Flag `when_to_use:` on a plugin SKILL.md as a repo-policy violation
   (portability), NOT as docs drift — Claude Code still documents the field.
5. Flag plugin-scope `paths:` as drift (non-functional at plugin scope).
6. Colon names (`rb:<slug>`) are repo policy — classify INFO, not WARNING.
7. Skill `description` length — three separate limits, none superseding
   another:

   | Limit | Source | Level |
   |---|---|---|
   | 1,024 characters | agentskills.io spec cap; NOT stated in cached `skills.md` — treat as unverified against the cache until a cited source is added | `ERROR` |
   | 1,536 characters | cached `skills.md` § Frontmatter reference — combined `description` + `when_to_use` truncation in the skill listing, adjustable via `skillListingMaxDescChars` | `ERROR` |
   | 250 characters | repo authoring target for routing quality | `WARNING` |

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
- `PreModelSwitch`
- `PostModelSwitch`
- `TaskCreated`
- `TaskCompleted`
- `Stop`
- `StopFailure`
- `TeammateIdle`
- `InstructionsLoaded`
- `ConfigChange`
- `CwdChanged`
- `FileChanged`
- `DirectoryAdded`
- `WorktreeCreate`
- `WorktreeRemove`
- `PreCompact`
- `PostCompact`
- `Elicitation`
- `ElicitationResult`
- `MessageDisplay`

Documented hook types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.

Known runtime-ahead-of-docs events — do NOT flag as undocumented:

| Event | Status |
|---|---|
| (none) | `DirectoryAdded` graduated on 2026-08-30 — now documented in `hooks.md` main event table, its own section, and `agent-sdk/hooks.md`. |

Add a row when the CC changelog announces an event `hooks.md` does not
yet carry; delete the row once the event reaches `hooks.md`.

A handler on such an event MUST NOT read event-specific payload fields, and
MUST be advisory (exit 0 on every path), so an unannounced schema cannot
break a session. Reading base fields common to all hook events (for example
`.cwd` via `resolve_workspace_root`) is allowed, provided the handler still
succeeds when the payload is missing, empty, or unparseable.

Important constraints:

| Constraint | Detail |
|---|---|
| handler-level `if` filters | documented + useful |
| `if` event scope | evaluated only on tool events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`. On other events a hook with `if` never runs |
| `FileChanged` matcher | matcher = watched filenames (NOT a tool matcher); do not lint as one |
| single-segment `dir/**` in `if` | matches ONLY `<cwd>/dir`, not `dir/` at any depth. Any-depth intent requires `**/dir/**`. `deny`/`ask` permission rules keep their any-depth match — do NOT generalize this rule to permission rules |
| `async` | documented only for `type: "command"` hooks |
| async control | async hooks cannot block / control Claude after start; `decision`, `permissionDecision`, `continue` MUST NOT be treated as meaningful on async handlers |
| `PreModelSwitch` | blocking (10s budget; a timeout also blocks). Matcher compares the canonical target-model name — aliases, dated IDs, provider IDs, and the `[1m]` suffix all normalize. When no canonical name resolves, every handler runs regardless of matcher, so a blocking handler MUST read `to_model` itself. Does NOT fire for Claude-initiated switches (auto-fallback, resume-restore) |
| `PostModelSwitch` | non-blocking, side-effect only — the model already changed. Receives the Claude-initiated switches `PreModelSwitch` skips |

Checks:

1. Confirm `hooks/hooks.json` only uses documented events + types.
2. Flag undocumented events / hook types as `BLOCKER`.
3. `if` outside tool events → `WARNING` or `BLOCKER` (depending on whether handler is disabled).
4. Single-segment `dir/**` path glob in any `if` filter → `BLOCKER` when the handler is meant to fire for nested Rails layouts (engines, modular monolith packages). Expect `**/dir/**`.
5. Async on non-`command` hooks → docs issue.
6. Async hook + control output → not supported unless cached docs explicitly say.
7. Validate `${CLAUDE_PLUGIN_ROOT}` references against real repo paths:

   | Context | Path |
   |---|---|
   | this repo | `plugins/ruby-grape-rails/...` |
   | packaged plugin root | `hooks/hooks.json`, `.claude-plugin/plugin.json` |

## Plugin Config Validation

Authoritative cached docs:

- `plugins-reference.md` (serves the manifest reference)
- `plugins/marketplace-reference.md`
- `plugins/components.md`
- `plugins.md`
- `mcp.md`
- `settings.md` (only when finding depends on settings semantics)

Checks for `.claude-plugin/plugin.json`:

1. Confirm required manifest structure matches current docs. `name` is
   the only required key.
2. Currently-documented top-level keys (when present):
   - metadata: `$schema`, `name`, `displayName`, `version`,
     `description`, `author`, `homepage`, `repository`, `license`,
     `keywords`, `metadata`, `defaultEnabled`, `dependencies`
   - behavior: `settings` (only `agent` and `subagentStatusLine` take
     effect), `userConfig`, `channels`
   - components: `skills`, `commands`, `agents`, `hooks`, `mcpServers`,
     `lspServers`, `outputStyles`, `workflows`
   - `experimental.themes`, `experimental.monitors`, `experimental.evals`
     (shape may still change)
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
