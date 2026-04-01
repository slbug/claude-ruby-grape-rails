# Claude Settings Permission Format

How to write Claude Code permission rules safely for Ruby projects.

## Settings File Hierarchy

More specific scopes take precedence. `deny` beats `allow` at any level.

| Scope | File | Shared? |
|-------|------|---------|
| User (global) | `~/.claude/settings.json` | No |
| Project (team) | `.claude/settings.json` | Yes |
| Local (personal) | `.claude/settings.local.json` | No |

Rules are evaluated in this order: `deny -> ask -> allow`.

## Permission Format

```json
{
  "permissions": {
    "allow": [
      "Bash(bundle exec rspec *)",
      "Bash(bundle exec rubocop *)",
      "Bash(git status *)"
    ],
    "deny": [
      "Bash(bundle exec rails db:drop *)",
      "Bash(git push --force *)",
      "Bash(rm -rf *)"
    ]
  }
}
```

## Pattern Syntax

- `Bash` or `Bash(*)` matches all Bash commands
- `Bash(cmd *)` matches `cmd` with arguments, or the exact bare command `cmd`
- `Bash(cmd)` is an exact match
- the space before `*` matters:
  - `Bash(git *)` matches `git`, `git diff`, `git add`
  - `Bash(git*)` also matches `gitk`
  - `Bash(git *)` keeps a word boundary, so it does not match `gitk`

### Deprecated Syntax

Do not use `Bash(git:*)`. Rewrite it to `Bash(git *)`.

## Recommended Placement

| Command Type | Recommended File |
|--------------|------------------|
| Universal tools (`rg`, `jq`, `git status`) | `~/.claude/settings.json` |
| Ruby project verification (`bundle exec rspec`, `bundle exec rubocop`) | `.claude/settings.json` |
| Personal workflow tweaks | `.claude/settings.local.json` |

## Recommended Ruby Patterns

### Good Narrow Patterns

```json
{
  "permissions": {
    "allow": [
      "Bash(bundle exec rspec *)",
      "Bash(bundle exec rails test *)",
      "Bash(bundle exec standardrb *)",
      "Bash(bundle exec rubocop *)",
      "Bash(bundle exec brakeman *)",
      "Bash(bundle exec rails zeitwerk:check *)",
      "Bash(git status *)",
      "Bash(git diff *)"
    ]
  }
}
```

### Too Broad for Normal Teams

```json
{
  "permissions": {
    "allow": [
      "Bash(bundle *)",
      "Bash(rails *)",
      "Bash(git *)"
    ]
  }
}
```

Only recommend broad rules like these if the user explicitly wants a high-trust
project setup.
