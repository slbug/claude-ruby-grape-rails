# Documentation Pages

Contributor mapping for `.claude/docs-check/`.

Use this file to decide which cached Claude docs are authoritative for a given
validation question. Do not load every cached page unless the problem actually
crosses those boundaries.

## Cached Inputs

The fetch script maintains:

- `llms.txt` as the discovery index
- 46 detailed cached pages under `.claude/docs-check/docs-cache/` (includes nested `whats-new/` and `agent-sdk/` subdirectories)

Primary cached pages (plugin-critical):

| Page | Primary use |
|------|-------------|
| `sub-agents.md` | Agent tool syntax, `Agent(...)` restrictions, general subagent behavior |
| `skills.md` | Skill frontmatter, `paths`, `shell`, supporting-file conventions |
| `hooks.md` | Hook events, hook types, handler schema, `if` examples |
| `hooks-guide.md` | Hook best practices, version-gated `if` behavior, design guidance |
| `plugins-reference.md` | Plugin manifest, plugin-shipped agent support, `userConfig`, `channels`, `${CLAUDE_PLUGIN_DATA}` |
| `plugin-marketplaces.md` | Marketplace manifest structure and source forms |
| `plugin-dependencies.md` | `plugin.json` dependency version constraints |
| `plugins.md` | Plugin structure, plugin creation guidance, high-level conventions |
| `settings.md` | Settings semantics when a finding depends on permission or config behavior |
| `mcp.md` | MCP config semantics when plugin findings touch bundled MCP servers |
| `tools-reference.md` | Tool schema and examples |
| `claude-directory.md` | Authoritative `.claude/` layout: CLAUDE.md, settings.json, hooks, skills, commands, subagents, rules, auto memory |
| `commands.md` | Slash command reference and bundled skills; plugin `/rb:*` namespace overlap checks |
| `env-vars.md` | Environment variable contract: `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PROJECT_DIR`, etc. |
| `errors.md` | Error taxonomy driving hook failure classification and `StopFailure` matchers |
| `cli-reference.md` | `claude plugin validate`, `--plugin-dir`, flags used by eval/doctor scripts |
| `statusline.md` | Plugin-level `subagentStatusLine` setting schema |
| `discover-plugins.md` | Marketplace install flow, `git-subdir` path resolution |
| `sandboxing.md` | Bash sandboxing semantics affecting hook side-effect guarantees |
| `context-window.md` | PreCompact/PostCompact hook timing and payload |
| `code-review.md` | Built-in `/code-review` flow — overlap check with plugin `/rb:review` |
| `best-practices.md` | Plugin development best practices — contributor baseline for authoring guidelines |
| `security.md` | Plugin-facing security guidance — alignment for `block-dangerous-ops.sh` / `secret-scan.sh` policy |
| `checkpointing.md` | File checkpointing semantics affecting hook ordering assumptions |
| `remote-control.md` | `CronCreate` / scheduled trigger surface — `schedule` skill validation |
| `model-config.md` | Agent/skill `model:` frontmatter validity (opus-4-7, sonnet-4-6, haiku-4-5) |
| `ultraplan.md` | Bundled `/ultraplan` — overlap check with plugin `/rb:plan` |
| `ultrareview.md` | Bundled `/ultrareview` — overlap check with plugin `/rb:review` |
| `changelog.md` | Canonical CC changelog — authoritative source for `cc-changelog` skill |

Additional cached pages (context/reference):

| Page | Primary use |
|------|-------------|
| `agent-teams.md` | Agent teams and collaboration features |
| `how-claude-code-works.md` | Claude Code architecture and concepts |
| `third-party-integrations.md` | Supported third-party integrations |
| `features-overview.md` | Key features and capabilities overview |
| `memory.md` | Memory types and CLAUDE.md usage guidelines |
| `overview.md` | High-level Claude Code overview |
| `permission-modes.md` | Permission modes and implications for plugins |
| `permissions.md` | Comprehensive permissions guide |
| `fast-mode.md` | `/fast` Opus 4.6 semantics — relates to `effort: max` skill settings |
| `output-styles.md` | Output-style surface adjacent to statusline + `subagentStatusLine` |
| `troubleshooting.md` | Hook failure diagnosis patterns |
| `common-workflows.md` | Plan/Work/Review lifecycle comparison with `/rb:*` workflows |
| `whats-new/index.md` | Weekly release notes index — `cc-changelog` + docs-check feed |
| `agent-sdk/hooks.md` | SDK hook interface parity check (SDK vs plugin surface) |
| `agent-sdk/plugins.md` | SDK plugin packaging parity |
| `agent-sdk/subagents.md` | SDK subagent frontmatter parity |
| `agent-sdk/slash-commands.md` | SDK slash command parity |

## Which Pages To Read

### Agents

Use:

- `plugins-reference.md`
- `sub-agents.md`

Questions this answers:

- Which frontmatter fields are supported for plugin-shipped agents?
- Is a given tool name or `Agent(...)` restriction documented?
- Is a reported agent-field issue real or just stale local guidance?

### Skills

Use:

- `skills.md`
- `hooks.md` if the skill uses skill-scoped hooks

Questions this answers:

- Is a skill frontmatter field documented?
- Are `paths` / `shell` / `effort` valid?
- Is a structure complaint actually a docs issue?

### Hooks

Use:

- `hooks.md`
- `hooks-guide.md`

Questions this answers:

- Is this hook event or hook type documented?
- Is handler-level `if` valid here?
- Is this a schema break, version gate, or only a local recommendation?

### Plugin Config

Use:

- `plugins-reference.md`
- `plugin-marketplaces.md`
- `plugin-dependencies.md` when the question touches version constraints
- `plugins.md`
- `mcp.md` when MCP config is involved
- `settings.md` only when a conclusion depends on settings behavior
- `discover-plugins.md` when the marketplace install flow is in question

Questions this answers:

- Does `plugin.json` support this field?
- Are `userConfig`, `channels`, or `dependencies` documented?
- Should a recommendation use `${CLAUDE_PLUGIN_ROOT}` or
  `${CLAUDE_PLUGIN_DATA}`?

### Commands and `.claude/` Layout

Use:

- `claude-directory.md`
- `commands.md`

Questions this answers:

- Is a `.claude/` subpath or file reserved by CC?
- Does a plugin-shipped slash command collide with a built-in?

### Hook Runtime Contract

Use:

- `env-vars.md`
- `errors.md`
- `sandboxing.md`
- `context-window.md`

Questions this answers:

- Is a referenced env var (`CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`,
  `CLAUDE_PROJECT_DIR`, etc.) documented?
- Are `StopFailure` matcher values or error codes documented?
- Does a hook's bash command rely on behavior the sandbox disallows?
- Does a PreCompact/PostCompact hook see the payload fields it expects?

### CLI and Status Line

Use:

- `cli-reference.md`
- `statusline.md`

Questions this answers:

- Is the `claude plugin ...` subcommand used by doctor/eval still documented?
- Does plugin-level `subagentStatusLine` match the documented schema?

### Built-in Feature Overlap

Use:

- `code-review.md`
- `ultraplan.md`
- `ultrareview.md`
- `common-workflows.md`

Questions this answers:

- Does a plugin `/rb:*` command duplicate or conflict with a built-in CC
  command (e.g., `/code-review`, `/ultraplan`, `/ultrareview`)?
- Is a plugin workflow step already covered by a documented CC lifecycle?

### CC Version Tracking

Use:

- `changelog.md`
- `whats-new/index.md`

Questions this answers:

- Is a CC feature mentioned in the plugin actually shipped yet?
- Does a plugin workaround predate an upstream fix that should remove it?
- What new CC entries landed since the last `/cc-changelog` run?

### Remote Control and Scheduled Tasks

Use:

- `remote-control.md`

Questions this answers:

- Does a plugin reference to `CronCreate` / scheduled triggers still match
  the documented surface?
- Are Remote Control-only features assumed present in a skill that should
  degrade gracefully?

### Effort Tiering and Fast Mode

Use:

- `fast-mode.md`
- `model-config.md`

Questions this answers:

- Is `effort: max` valid for the model chosen in a given skill's frontmatter?
- Does `/fast` Opus 4.6 behavior match assumptions in workflow skills?
- Are agent/skill `model:` frontmatter values still supported?

### Plugin Best Practices

Use:

- `best-practices.md`

Questions this answers:

- Does a contributor recommendation contradict documented plugin best
  practices?
- Is a structural guideline in this repo aligned with CC authoring guidance?

### Security Baseline

Use:

- `security.md`

Questions this answers:

- Does `block-dangerous-ops.sh` or `secret-scan.sh` policy align with
  documented plugin security guidance?
- Are plugin-injected security reminders still matched by documented CC
  behavior?

### File Checkpointing and Hook Ordering

Use:

- `checkpointing.md`
- `troubleshooting.md`

Questions this answers:

- Does a plugin hook rely on file-checkpoint ordering the docs still
  describe?
- Is a reported hook failure pattern a known documented issue?

### SDK Parity Checks

Use (only when the finding crosses plugin/SDK boundaries):

- `agent-sdk/hooks.md`
- `agent-sdk/plugins.md`
- `agent-sdk/subagents.md`
- `agent-sdk/slash-commands.md`

Questions this answers:

- Does a plugin-shipped agent frontmatter field match the SDK-documented
  surface?
- Does a plugin slash-command shape match the SDK command interface?
- Is a hook event or payload field documented equivalently in plugin and
  SDK surfaces?

## Practical Loading Rules

1. Start with the smallest page set that answers the question.
2. Use `llms.txt` only as the cached index, not as the detailed authority.
3. Prefer targeted snippets over pasting full cached pages into subagent
   prompts.
4. If a finding depends on version-gated behavior, include the exact cached doc
   snippet that states the gate.
