# CC Changelog Analysis Rules

## Plugin Component Mapping

When analyzing CC changelog entries, map them to specific plugin components:

### Hooks System

| CC Change Pattern | Plugin Files to Check |
|-------------------|-----------------------|
| Hook events (new/changed/removed) | `plugins/ruby-grape-rails/hooks/hooks.json` |
| Hook `if` conditions | All hooks with `"if":` patterns |
| Hook output behavior | `plugins/ruby-grape-rails/hooks/scripts/*.sh` |
| `asyncRewake`, `once`, `timeout` | hooks.json hook definitions |
| `additionalContext` changes | SubagentStart, PostToolUseFailure hooks |
| `hookSpecificOutput` changes | All hooks using exit 2 + stderr |
| New hook types (agent, prompt, http) | Consider new hook opportunities |

### Agent Frontmatter

| CC Change Pattern | Plugin Files to Check |
|-------------------|-----------------------|
| New frontmatter fields | All 23 agents in `plugins/ruby-grape-rails/agents/*.md` |
| `model:` value changes | Agents using specific model values |
| `effort:` level changes | All agents with effort levels |
| `tools:` / `disallowedTools:` | Review agents (read-only enforcement) |
| `omitClaudeMd:` behavior | Agents with `omitClaudeMd: true` |
| `skills:` preloading | Agents with preloaded skills |
| `isolation:` / `background:` | Orchestrator agents |
| `maxTurns:` behavior | All agents with maxTurns set |

### Skill System

| CC Change Pattern | Plugin Files to Check |
|-------------------|-----------------------|
| Skill format changes | All 51 skills in `plugins/ruby-grape-rails/skills/` |
| `description` length limits | All SKILL.md frontmatter (250 char cap) |
| `paths:` field behavior | Skills with `paths:` for auto-loading |
| Skill listing/truncation | Skill descriptions and ordering |
| `argument-hint:` | Command skills with argument hints |
| `effort:` level support | All skills with effort levels |

### Plugin Config

| CC Change Pattern | Plugin Files to Check |
|-------------------|-----------------------|
| `plugin.json` schema | `plugins/ruby-grape-rails/.claude-plugin/plugin.json` |
| `marketplace.json` schema | `.claude-plugin/marketplace.json` |
| `${CLAUDE_PLUGIN_DATA}` | `hooks/scripts/setup-dirs.sh`, `log-progress.sh` |
| `${CLAUDE_PLUGIN_ROOT}` | All hooks.json paths |
| `settings.json` keys | `plugins/ruby-grape-rails/settings.json` |
| Plugin validation changes | CI workflow |

### Tool System

| CC Change Pattern | Plugin Files to Check |
|-------------------|-----------------------|
| Tool parameter changes | Hooks checking tool inputs |
| New tools added | Agent `tools:` / `disallowedTools:` lists |
| Tool deprecation | Agent tool references, skill instructions |
| `SendMessage` / `TaskCreate` / etc. | Orchestrator agents using these tools |

### Compaction and Memory

| CC Change Pattern | Plugin Files to Check |
|-------------------|-----------------------|
| Compaction behavior | `PreCompact` / `PostCompact` hooks |
| Context window changes | Agent token budgets, skill sizes |
| Memory system changes | Agents with `memory: project` |

## Impact Classification Rules

### BREAKING — Requires Immediate Action

Flag as BREAKING when CC changelog says:

- "Breaking change" explicitly
- "Removed" a feature/parameter we use
- "Changed" behavior of a hook event we rely on
- "Renamed" an API/tool/parameter we reference
- Tool parameter schema changed (affects hook `if` patterns)

**Verification**: grep the plugin for the affected term/pattern.

### OPPORTUNITY — New Feature We Could Use

Flag as OPPORTUNITY when:

- New hook event added
- New agent frontmatter field that could improve our agents
- New plugin capability (new `${}` variables, settings keys)
- New tool that agents could benefit from
- Performance improvement that changes best practices

**Prioritization**: Score 1-3 based on how many plugin components benefit.

### RELEVANT FIX — CC Fixed Something We Work Around

Flag as RELEVANT FIX when:

- CC fixed a bug we documented in CLAUDE.md or memory
- CC fixed a behavior our hooks explicitly handle
- Error mentioned in compound solutions

**Verification**: search CLAUDE.md and hooks for the bug pattern.

### DEPRECATION — Migration Needed

Flag as DEPRECATION when:

- CC deprecated a tool/parameter we use
- CC will remove something in a future version
- CC recommends migrating from X to Y (and we use X)

**Urgency**: immediate if removal announced, low if just deprecated.

### INFO — Log Only

Everything else: performance improvements, unrelated bug fixes, features for
capabilities we don't use (e.g., PowerShell, Computer Use).

## Cross-Reference Checklist

For each BREAKING or DEPRECATION item, always:

1. `grep -r "PATTERN" plugins/ruby-grape-rails/` — find all usages
2. Check `hooks/hooks.json` — any hook referencing the feature
3. Check CLAUDE.md — any instructions referencing this
4. Check `2.0.0.md` — any deferred items affected
