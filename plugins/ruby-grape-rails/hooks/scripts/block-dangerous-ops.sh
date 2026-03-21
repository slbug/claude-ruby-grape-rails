#!/usr/bin/env bash

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
[[ "$TOOL" == "Bash" ]] || exit 0

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[[ -n "$COMMAND" ]] || exit 0

if echo "$COMMAND" | grep -qE '(bin/rails|bundle exec rails) db:(drop|reset|purge)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
BLOCKED: destructive Rails database command detected.
Use a targeted rollback or migration instead. If you truly need a full reset,
run it manually outside Claude Code.
MSG
  exit 2
fi

if echo "$COMMAND" | grep -qE 'redis-cli .*FLUSH(ALL|DB)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
BLOCKED: destructive Redis flush detected.
If intentional, run it manually outside Claude Code.
MSG
  exit 2
fi

if echo "$COMMAND" | grep -qE 'git push.*(--force|-f)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
BLOCKED: force push detected. Prefer git push --force-with-lease.
MSG
  exit 2
fi

if echo "$COMMAND" | grep -qE '(RAILS_ENV|RACK_ENV)=(prod|production)'; then
  cat >&2 <<'MSG'
WARNING: production environment detected. Re-check that this command belongs in Claude Code.
MSG
  exit 2
fi
