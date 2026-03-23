#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

INPUT=$(read_hook_input)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
[[ "$TOOL" == "Bash" ]] || exit 0

COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -n "$COMMAND" ]] || exit 0

if printf '%s' "$COMMAND" | grep -qE '(bin/rails|bundle exec rails) db:(drop|reset|purge)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
BLOCKED: destructive Rails database command detected.
Use a targeted rollback or migration instead. If you truly need a full reset,
run it manually outside Claude Code.
MSG
  exit 2
fi

if printf '%s' "$COMMAND" | grep -qE 'redis-cli .*FLUSH(ALL|DB)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
BLOCKED: destructive Redis flush detected.
If intentional, run it manually outside Claude Code.
MSG
  exit 2
fi

if printf '%s' "$COMMAND" | grep -qE 'git push.*(--force|-f)([[:space:]]|$)'; then
  cat >&2 <<'MSG'
BLOCKED: force push detected. Prefer git push --force-with-lease.
MSG
  exit 2
fi

if printf '%s' "$COMMAND" | grep -qiE '(RAILS_ENV|RACK_ENV)=["'\'']?(prod|production)["'\'']?'; then
  cat >&2 <<'MSG'
BLOCKED: production environment detected. Re-check that this command belongs in Claude Code.
MSG
  exit 2
fi

exit 0
