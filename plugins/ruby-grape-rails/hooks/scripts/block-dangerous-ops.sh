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

  printf '%s\n' "$command_text" | tr ';' '\n'
}

trim_leading_whitespace() {
  local segment="$1"

  segment="${segment#"${segment%%[![:space:]]*}"}"
  printf '%s\n' "$segment"
}

trim_trailing_whitespace() {
  local segment="$1"

  segment="${segment%"${segment##*[![:space:]]}"}"
  printf '%s\n' "$segment"
}

trim_matching_outer_quotes() {
  local segment

  segment=$(trim_leading_whitespace "$1")
  segment=$(trim_trailing_whitespace "$segment")

  case "$segment" in
    \"*\")
      segment="${segment#\"}"
      segment="${segment%\"}"
      ;;
    \'*\')
      segment="${segment#\'}"
      segment="${segment%\'}"
      ;;
  esac

  printf '%s\n' "$segment"
}

trim_enclosing_grouping() {
  local segment

  segment=$(trim_leading_whitespace "$1")
  segment=$(trim_trailing_whitespace "$segment")

  while [[ "$segment" == \(*\) ]]; do
    segment="${segment#(}"
    segment="${segment%)}"
    segment=$(trim_leading_whitespace "$segment")
    segment=$(trim_trailing_whitespace "$segment")
  done

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

extract_shell_wrapper_payload() {
  local segment

  segment=$(trim_enclosing_grouping "$1")

  if [[ "$segment" =~ ^(bash|sh|zsh)([[:space:]]+[-A-Za-z0-9_:./=]+)*[[:space:]]+-[A-Za-z]*c[A-Za-z]*[[:space:]]+(.+)$ ]]; then
    trim_matching_outer_quotes "${BASH_REMATCH[3]}"
    return 0
  fi

  return 1
}

extract_ruby_wrapper_payload() {
  local segment
  local rest
  local token
  local ruby_code
  local nested_command

  segment=$(trim_enclosing_grouping "$1")
  [[ "$segment" == ruby[[:space:]]* ]] || return 1

  rest="${segment#ruby}"
  while :; do
    rest=$(trim_leading_whitespace "$rest")
    [[ -n "$rest" ]] || return 1

    token="${rest%%[[:space:]]*}"
    if [[ "$token" == "$rest" ]]; then
      return 1
    fi

    if [[ "$token" == "-e" ]]; then
      rest="${rest#"$token"}"
      ruby_code=$(trim_matching_outer_quotes "$rest")
      nested_command=$(printf '%s' "$ruby_code" | sed -nE "s/.*(system|exec|spawn)\\('([^']*)'\\).*/\\2/p")
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\("([^"]*)"\).*/\2/p')
      fi
      [[ -n "$nested_command" ]] || return 1
      printf '%s\n' "$nested_command"
      return 0
    fi

    [[ "$token" == -* ]] || return 1
    rest="${rest#"$token"}"
  done

  return 1
}

emit_command_variants() {
  local command_text="$1"
  local depth="${2:-2}"
  local nested=""
  local normalized=""

  normalized=$(trim_enclosing_grouping "$command_text")
  [[ -n "$normalized" ]] || return 0

  printf '%s\n' "$normalized"

  [[ "$depth" -gt 0 ]] || return 0

  if nested=$(extract_shell_wrapper_payload "$normalized"); then
    emit_command_variants "$nested" $(( depth - 1 ))
  fi

  if nested=$(extract_ruby_wrapper_payload "$normalized"); then
    emit_command_variants "$nested" $(( depth - 1 ))
  fi
}

is_destructive_db_command() {
  local command_text="$1"
  local segment
  local candidate

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    while IFS= read -r candidate; do
      if [[ "$candidate" =~ ^((bundle[[:space:]]+exec[[:space:]]+)?((\./)?bin/)?(rails|rake))([[:space:]]|$) ]] &&
        printf '%s' "$candidate" | grep -qE "(^|[[:space:]])['\"]?db:(drop|reset|purge)(:[[:alnum:]_:-]+)?['\"]?([[:space:]]|$)"; then
        return 0
      fi
    done < <(emit_command_variants "$segment")
  done < <(normalize_command_segments "$command_text")

  return 1
}

is_destructive_redis_command() {
  local command_text="$1"
  local segment
  local candidate
  local lowered

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    while IFS= read -r candidate; do
      lowered=$(to_ascii_lower "$candidate")
      if [[ "$lowered" =~ ^redis-cli([[:space:]]+[^[:space:]]+)*[[:space:]]+flush(all|db)([[:space:]]|$) ]]; then
        return 0
      fi
    done < <(emit_command_variants "$segment")
  done < <(normalize_command_segments "$command_text")

  return 1
}

is_force_push_command() {
  local command_text="$1"
  local segment
  local candidate

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue

    while IFS= read -r candidate; do
      if [[ "$candidate" =~ ^git([[:space:]]+-c[[:space:]]+[^[:space:]]+)*[[:space:]]+push([[:space:]]|$) ]] &&
        printf '%s' "$candidate" | grep -qE '(^|[[:space:]])(--force|-f)([[:space:]]|$)'; then
        return 0
      fi
    done < <(emit_command_variants "$segment")
  done < <(normalize_command_segments "$command_text")

  return 1
}

is_harmless_env_probe() {
  printf '%s' "$1" | grep -qE '^(echo|printf|cat|env|export|declare|typeset|readonly|unset|true|false)([[:space:]]|$)'
}

is_production_env_command() {
  local command_text="$1"
  local segment
  local candidate

  while IFS= read -r segment; do
    while IFS= read -r candidate; do
      split_leading_env_prefixes "$candidate"
      [[ -n "$LEADING_ENV_PREFIXES_RESULT" ]] || continue
      [[ -n "$STRIPPED_COMMAND_RESULT" ]] || continue

      if ! printf '%s' "$LEADING_ENV_PREFIXES_RESULT" | grep -qiE '(^|[[:space:]])(RAILS_ENV|RACK_ENV)=["'\'']?(prod|production)["'\'']?([[:space:]]|$)'; then
        continue
      fi

      if is_harmless_env_probe "$STRIPPED_COMMAND_RESULT"; then
        continue
      fi

      return 0
    done < <(emit_command_variants "$segment")
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
