# Documentation Pages

Contributor mapping for `.claude/docs-check/`.

Use this file to decide which cached Claude docs are authoritative for a given
validation question. Do not load every cached page unless the problem actually
crosses those boundaries.

## Cached Inputs

The fetch script maintains:

- `llms.txt` as the discovery index
- 29 detailed cached pages under `.claude/docs-check/docs-cache/`

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

Questions this answers:

- Does a plugin `/rb:*` command duplicate or conflict with a built-in CC
  command (e.g., `/code-review`)?

## Practical Loading Rules

1. Start with the smallest page set that answers the question.
2. Use `llms.txt` only as the cached index, not as the detailed authority.
3. Prefer targeted snippets over pasting full cached pages into subagent
   prompts.
4. If a finding depends on version-gated behavior, include the exact cached doc
   snippet that states the gate.
