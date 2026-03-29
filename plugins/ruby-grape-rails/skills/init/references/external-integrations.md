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

Optional user-level config for `~/.config/dcg/config.toml`:

```toml
[packs]
enabled = [
  # Keep dcg's default/core git and filesystem protections.

  # Add these only when they match the local stack/tooling:
  "database.redis",      # redis-cli / Sidekiq / Redis operations
  "database.mysql",      # MySQL / MariaDB
  "database.sqlite",     # SQLite
  "storage.s3",          # aws s3 rm / sync --delete
  "cloud.aws",           # aws CLI destructive resource changes
  "kubernetes.kubectl",  # kubectl delete / drain / namespace ops

  # Optional stricter git policy if the user wants more than dcg's defaults:
  # "strict_git",
]

[agents.claude-code]
trust_level = "high"
```

Do not try to encode Rails-specific tasks like `rails db:drop` here. Keep those
in the plugin's own dangerous-op hook; `dcg` config is better for generic CLI
families and infrastructure tools.

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
- If the user wants team policies, point them to Shellfirm's official policy
  docs instead of generating a generic `.shellfirm.yaml` from plugin-local
  assumptions
