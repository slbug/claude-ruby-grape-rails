# Validation Rules

Per-component checklists for validation workers.
Each section is passed ONLY to the subagent responsible for that component type.

## Agent Validation Rules

### Frontmatter Fields

Check each agent `.md` YAML frontmatter against `sub-agents.md` docs.

**Required fields:**

- `name` — lowercase, hyphens only, no spaces
- `description` — must include when to use/delegate guidance

**Optional fields (check valid values if present):**

| Field | Valid Values | Notes |
|-------|-------------|-------|
| `model` | `sonnet`, `opus`, `haiku`, `inherit` | Default: inherit |
| `permissionMode` | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` | Honored for local dev (`--plugin-dir`), **ignored for marketplace installs** per docs |
| `tools` | `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `Agent`, `WebFetch`, `WebSearch`, `NotebookEdit`, `Skill`, `AskUserQuestion`, `TaskCreate`, `TaskUpdate`, `TaskOutput`, `KillShell`, `MCPSearch`, `ExitPlanMode` | Check docs for new tools |
| `disallowedTools` | Same tool names as `tools` | |
| `maxTurns` | Positive integer | |
| `skills` | List of skill names | Verify referenced skills exist |
| `mcpServers` | Object or list | |
| `hooks` | Object | Per-agent lifecycle hooks |
| `memory` | `user`, `project`, `local` | Auto-enables Read/Write/Edit |
| `background` | `true`, `false` | Always run as background task |
| `isolation` | `worktree` | Run in temporary git worktree |

**Cross-checks:**

- If `memory` set, agent should have Write access (auto-enabled by memory)
- Review-only agents: `disallowedTools: Write, Edit, NotebookEdit`
- `tools` and `disallowedTools` must not overlap
- Skills in `skills:` must exist in `plugins/ruby-grape-rails/skills/`

**Detect changes:**

- Compare field list in docs against fields above
- Flag new fields the plugin doesn't use yet
- Flag fields the plugin uses that docs don't document (potential removal)

### Structural

- Valid markdown with YAML frontmatter (between `---` delimiters)
- Specialist agents: ≤365 lines (soft limit), target ~300 lines
- Orchestrator agents (has subagent prompts inline): ≤535 lines (justified by embedded prompts)
- **EXCEPTION**: Command skills may exceed 185 lines when execution flow must be inline
- **EXCEPTION**: Pattern skills may exceed 100 lines when they include comprehensive Iron Laws

## Skill Validation Rules

### Structure

Check each `skills/*/` directory against `skills.md` docs.

**Required:**

- `SKILL.md` exists with `name` in frontmatter

**Frontmatter fields:**

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Convention: `rb:{name}` for commands, `{domain}:{name}` for domain-specific, or plain `{name}` for pattern skills |
| `description` | No | Used for auto-loading |
| `argument-hint` | No | Shown in command help |
| `disable-model-invocation` | No | Boolean, default false |
| `user-invocable` | No | Boolean, default true. Set false to hide from `/` menu |
| `allowed-tools` | No | Restrict tools when skill is active |
| `model` | No | Model to use when skill is active |
| `context` | No | Set to `fork` to run in forked subagent |
| `agent` | No | Subagent type when `context: fork` is set |
| `hooks` | No | Lifecycle hooks scoped to this skill |

**Forbidden:** `triggers:` — MUST NOT be present.

**Detect changes:** New frontmatter fields, changed structure conventions.

### Structural

- SKILL.md: ≤185 lines for simple skills, ≤300 lines for workflow/command skills
- references/*.md: ≤350 lines each (soft limit for detailed reference content)

## Hook Validation Rules

### Schema

Check `hooks/hooks.json` against `hooks.md` docs.

**Structure:**

```json
{ "hooks": { "EventName": [{ "matcher": "", "hooks": [{ "type": "command", "command": "..." }] }] } }
```

**Valid event names:**

`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`,
`UserPromptSubmit`, `Notification`, `Stop`, `StopFailure`, `SubagentStart`, `SubagentStop`,
`SessionStart`, `SessionEnd`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `PostCompact`,
`InstructionsLoaded`, `ConfigChange`, `WorktreeCreate`, `WorktreeRemove`,
`Elicitation`, `ElicitationResult`

**Valid hook types:**

| Type | Required Fields | Optional Fields |
|------|----------------|-----------------|
| `command` | `command` | `timeout`, `environment` |
| `prompt` | `prompt` | `model`, `tools` |
| `agent` | `prompt` | `model`, `tools`, `maxTurns` |

**Cross-checks:**

- Event names not in valid set = **BLOCKER** (silently ignored by Claude Code)
- `command` paths with `${CLAUDE_PLUGIN_ROOT}` should resolve to existing scripts
- Check docs for new event names, hook types, or fields

## Plugin Config Validation Rules

### plugin.json

**Required:** `name` (kebab-case, no spaces)

**Valid optional fields:**

`version`, `description`, `author` (`{name, email?, url?}`), `homepage`,
`repository`, `license`, `keywords`, `commands`, `agents`, `skills`,
`hooks`, `mcpServers`, `outputStyles`, `lspServers`

**Cross-checks:** All path fields resolve to existing files/directories.

### marketplace.json

**Required:** `name`, `owner` (object with `name`), `plugins` (array)

**Each plugin entry:** `name` (required), `source` (required), with optional `description`, `version`, `author`, `category`, `tags`.

**Valid `source` forms:**

- Relative path string to a plugin dir inside the marketplace repo
- Source object, including at least:
  - `git-subdir`
  - `github`
  - `url`
  - `npm`

**Cross-checks:**

- Relative-path `source` values exist and each has `.claude-plugin/plugin.json`
- `git-subdir` sources include `url` and `path`
- `github` sources include `repo`
- `url` sources include `url`
- `npm` sources include `package`
- Names are unique
- Relative paths must stay within the marketplace root and must not contain `..`

## Priority Classification

Workers MUST classify every finding:

| Level | Meaning | Example |
|-------|---------|---------|
| **BLOCKER** | Breaks with current Claude Code | Invalid event name, removed field |
| **WARNING** | Deprecated/discouraged | Old field name, deprecated pattern |
| **INFO** | New capability available | New hook event, new frontmatter field |
| **PASS** | Validates correctly | Field values match docs |

## Output Template

```markdown
# {Type} Validation Report

**Files checked**: {count}
**Documentation version**: {date fetched}

## Breaking Changes (BLOCKER)
- **{file}:{line}** — {description}
  - Current: `{what plugin has}`
  - Expected: `{what docs say}`

## Deprecations (WARNING)
- **{file}** — {description}
  - Replacement: `{recommended alternative}`

## New Features Available (INFO)
- **{feature}** — {description}
  - Docs reference: {section}

## Validation Passed
- {count} files checked, {count} fields validated
```
