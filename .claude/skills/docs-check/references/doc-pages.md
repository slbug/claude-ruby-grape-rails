# Documentation Pages

Contributor mapping for `.claude/docs-check/`.

Use this file to decide which cached Claude docs are authoritative for a given
validation question. Do not load every cached page unless the problem actually
crosses those boundaries.

## Cached Inputs

The fetch script maintains:

- `llms.txt` as the discovery index
- 9 detailed cached pages under `.claude/docs-check/docs-cache/`

Primary cached pages:

| Page | Primary use |
|------|-------------|
| `sub-agents.md` | Agent tool syntax, `Agent(...)` restrictions, general subagent behavior |
| `skills.md` | Skill frontmatter, `paths`, `shell`, supporting-file conventions |
| `hooks.md` | Hook events, hook types, handler schema, `if` examples |
| `hooks-guide.md` | Hook best practices, version-gated `if` behavior, design guidance |
| `plugins-reference.md` | Plugin manifest, plugin-shipped agent support, `userConfig`, `channels`, `${CLAUDE_PLUGIN_DATA}` |
| `plugin-marketplaces.md` | Marketplace manifest structure and source forms |
| `plugins.md` | Plugin structure, plugin creation guidance, high-level conventions |
| `settings.md` | Settings semantics when a finding depends on permission or config behavior |
| `mcp.md` | MCP config semantics when plugin findings touch bundled MCP servers |

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
- `plugins.md`
- `mcp.md` when MCP config is involved
- `settings.md` only when a conclusion depends on settings behavior

Questions this answers:

- Does `plugin.json` support this field?
- Are `userConfig` or `channels` documented?
- Should a recommendation use `${CLAUDE_PLUGIN_ROOT}` or
  `${CLAUDE_PLUGIN_DATA}`?

## Practical Loading Rules

1. Start with the smallest page set that answers the question.
2. Use `llms.txt` only as the cached index, not as the detailed authority.
3. Prefer targeted snippets over pasting full cached pages into subagent
   prompts.
4. If a finding depends on version-gated behavior, include the exact cached doc
   snippet that states the gate.
