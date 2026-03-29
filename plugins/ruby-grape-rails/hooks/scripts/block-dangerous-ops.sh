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

trim_leading_whitespace() {
  local segment="$1"

  segment="${segment#"${segment%%[![:space:]]*}"}"
  printf '%s\n' "$segment"
}

to_ascii_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

LEADING_ENV_PREFIXES_RESULT=""
STRIPPED_COMMAND_RESULT=""

split_leading_env_prefixes() {
  local segment
  local prefix=""
  local assignment=""

  segment=$(trim_leading_whitespace "$1")

  while :; do
    if [[ "$segment" =~ ^env[[:space:]]+ ]]; then
      prefix+="env "
      segment="${segment#env}"
      segment=$(trim_leading_whitespace "$segment")
      continue
    fi

    if [[ "$segment" =~ ^([A-Za-z_][A-Za-z0-9_]*=([^[:space:]]+|\"[^\"]*\"|\'[^\']*\'))([[:space:]]+|$) ]]; then
      assignment="${BASH_REMATCH[1]}"
      prefix+="${assignment} "
      segment="${segment#"${BASH_REMATCH[0]}"}"
      segment=$(trim_leading_whitespace "$segment")
      continue
    fi

    break
  done

  LEADING_ENV_PREFIXES_RESULT="$prefix"
  STRIPPED_COMMAND_RESULT="$segment"
}

strip_leading_env_prefixes() {
  split_leading_env_prefixes "$1"
  printf '%s\n' "$STRIPPED_COMMAND_RESULT"
}

is_destructive_db_command() {
  local command_text="$1"
  local segment

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    if [[ "$segment" =~ ^((bundle[[:space:]]+exec[[:space:]]+)?((\./)?bin/)?(rails|rake))([[:space:]]|$) ]] &&
      printf '%s' "$segment" | grep -qE "(^|[[:space:]])['\"]?db:(drop|reset|purge)(:[[:alnum:]_:-]+)?['\"]?([[:space:]]|$)"; then
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

    lowered=$(to_ascii_lower "$segment")
    if [[ "$lowered" =~ ^redis-cli([[:space:]]+[^[:space:]]+)*[[:space:]]+flush(all|db)([[:space:]]|$) ]]; then
      return 0
    fi
  done < <(normalize_command_segments "$command_text")

  return 1
}

is_force_push_command() {
  local command_text="$1"
  local segment

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    if [[ "$segment" =~ ^git([[:space:]]+-c[[:space:]]+[^[:space:]]+)*[[:space:]]+push([[:space:]]|$) ]] &&
      printf '%s' "$segment" | grep -qE '(^|[[:space:]])(--force|-f)([[:space:]]|$)'; then
      return 0
    fi
  done < <(normalize_command_segments "$command_text")

  return 1
}

is_harmless_env_probe() {
  printf '%s' "$1" | grep -qE '^(echo|printf|cat|env|export|declare|typeset|readonly|unset|true|false)([[:space:]]|$)'
}

is_production_env_command() {
  local command_text="$1"
  local segment

  while IFS= read -r segment; do
    split_leading_env_prefixes "$segment"
    [[ -n "$LEADING_ENV_PREFIXES_RESULT" ]] || continue
    [[ -n "$STRIPPED_COMMAND_RESULT" ]] || continue

    if ! printf '%s' "$LEADING_ENV_PREFIXES_RESULT" | grep -qiE '(^|[[:space:]])(RAILS_ENV|RACK_ENV)=["'\'']?(prod|production)["'\'']?([[:space:]]|$)'; then
      continue
    fi

    if is_harmless_env_probe "$STRIPPED_COMMAND_RESULT"; then
      continue
    fi

    return 0
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

if is_force_push_command "$COMMAND"; then
  cat >&2 <<'MSG'
BLOCKED: force push detected. Prefer git push --force-with-lease.
MSG
  exit 2
fi

if is_production_env_command "$COMMAND"; then
  cat >&2 <<'MSG'
BLOCKED: production environment detected. Re-check that this command belongs in Claude Code.
MSG
  exit 2
fi

exit 0
