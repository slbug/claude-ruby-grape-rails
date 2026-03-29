# Optional External Integrations

These are user-level Claude Code safety/productivity integrations, not plugin
dependencies. Detecting them only means they are installed on the workstation.

## RTK

- Purpose: Claude command rewriting / token optimization proxy
- Recommended setup: `rtk init -g`
- Note: detection alone does not make Claude use RTK

## DCG

- Purpose: external destructive-command guard for Claude Code Bash usage
- Recommended setup: `dcg setup`
- Note: detection alone does not install the Claude Code hook

If the user wants the manual Claude Code hook shape instead of `dcg setup`,
recommend this `~/.claude/settings.json` fragment:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "dcg"
          }
        ]
      }
    ]
  }
}
```

Optional shell startup verification:

```bash
dcg setup --shell-check
```

## Shellfirm

- Purpose: external shell and AI-agent safety layer for Claude Code
- Recommended setup: `shellfirm connect claude-code`
- Note: detection alone does not install hooks or MCP integration
- Project policies can live in `.shellfirm.yaml`, but this plugin does not ship
  a default policy because Shellfirm's policy schema and team rules are
  external to the plugin
