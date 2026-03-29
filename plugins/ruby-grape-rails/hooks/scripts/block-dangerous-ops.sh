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

normalize_command_segments() {
  local command_text="$1"

  command_text=${command_text//$'\r'/}
  command_text=${command_text//$'\n'/;}
  command_text=${command_text//&&/;}
  command_text=${command_text//||/;}
  command_text=${command_text//|/;}
  command_text=${command_text//(/;}
  command_text=${command_text//)/;}

  printf '%s\n' "$command_text" | tr ';' '\n'
}

strip_leading_env_prefixes() {
  local segment="$1"

  segment="${segment#"${segment%%[![:space:]]*}"}"

  while :; do
    if [[ "$segment" =~ ^env[[:space:]]+ ]]; then
      segment="${segment#env}"
      segment="${segment#"${segment%%[![:space:]]*}"}"
      continue
    fi

    if [[ "$segment" =~ ^[A-Za-z_][A-Za-z0-9_]*=([^[:space:]]+|\"[^\"]*\"|\'[^\']*\')[[:space:]]+ ]]; then
      segment="${segment#"${BASH_REMATCH[0]}"}"
      segment="${segment#"${segment%%[![:space:]]*}"}"
      continue
    fi

    break
  done

  printf '%s\n' "$segment"
}

is_destructive_db_command() {
  local command_text="$1"
  local segment

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    if [[ "$segment" =~ ^((bundle[[:space:]]+exec[[:space:]]+)?((\./)?bin/)?(rails|rake))[[:space:]]+db:(drop|reset|purge)([[:space:]]|$) ]]; then
      return 0
    fi
  done < <(normalize_command_segments "$command_text")

  return 1
}

is_destructive_redis_command() {
  local command_text="$1"
  local segment
  local lowered

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    lowered=${segment,,}
    if [[ "$lowered" =~ ^redis-cli([[:space:]]+[^[:space:]]+)*[[:space:]]+flush(all|db)([[:space:]]|$) ]]; then
      return 0
    fi
  done < <(normalize_command_segments "$command_text")

  return 1
}

if is_destructive_db_command "$COMMAND"; then
  cat >&2 <<'MSG'
BLOCKED: destructive Rails database command detected.
Use a targeted rollback or migration instead. If you truly need a full reset,
run it manually outside Claude Code.
MSG
  exit 2
fi

if is_destructive_redis_command "$COMMAND"; then
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
