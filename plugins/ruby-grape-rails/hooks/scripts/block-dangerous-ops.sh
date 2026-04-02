#!/usr/bin/env bash
set -o nounset
set -o pipefail

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: block-dangerous-ops.sh cannot inspect the command because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before running destructive commands." >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
command -v grep >/dev/null 2>&1 || emit_missing_dependency_block "grep"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

read_hook_input
INPUT="$HOOK_INPUT_VALUE"
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "BLOCKED: block-dangerous-ops.sh could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      echo "Increase RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES or fix the hook input before re-running this command." >&2
      exit 2
      ;;
  esac
fi

emit_payload_schema_block() {
  local reason="$1"

  echo "BLOCKED: block-dangerous-ops.sh could not safely inspect the command because ${reason}." >&2
  echo "Fix the hook payload schema before re-running this command." >&2
  exit 2
}

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || emit_payload_schema_block "tool_name could not be parsed"
[[ -n "$TOOL" ]] || emit_payload_schema_block "tool_name was missing"
[[ "$TOOL" == "Bash" ]] || exit 0

COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || emit_payload_schema_block "tool_input.command could not be parsed"
[[ -n "$COMMAND" ]] || emit_payload_schema_block "tool_input.command was missing"

normalize_command_segments() {
  local command_text="$1"
  local current=""
  local char=""
  local next=""
  local in_single=0
  local in_double=0
  local escaped=0
  local i=0
  local length=${#command_text}

  flush_segment() {
    local segment="$1"

    segment=$(trim_leading_whitespace "$segment")
    segment=$(trim_trailing_whitespace "$segment")
    [[ -n "$segment" ]] && printf '%s\n' "$segment"
  }

  while [[ "$i" -lt "$length" ]]; do
    char="${command_text:$i:1}"
    next=""
    if [[ $(( i + 1 )) -lt "$length" ]]; then
      next="${command_text:$(( i + 1 )):1}"
    fi

    if [[ "$escaped" -eq 1 ]]; then
      current+="$char"
      escaped=0
      i=$(( i + 1 ))
      continue
    fi

    if [[ "$in_single" -eq 0 && "$char" == "\\" ]]; then
      current+="$char"
      escaped=1
      i=$(( i + 1 ))
      continue
    fi

    if [[ "$char" == "'" && "$in_double" -eq 0 ]]; then
      current+="$char"
      if [[ "$in_single" -eq 1 ]]; then
        in_single=0
      else
        in_single=1
      fi
      i=$(( i + 1 ))
      continue
    fi

    if [[ "$char" == '"' && "$in_single" -eq 0 ]]; then
      current+="$char"
      if [[ "$in_double" -eq 1 ]]; then
        in_double=0
      else
        in_double=1
      fi
      i=$(( i + 1 ))
      continue
    fi

    if [[ "$in_single" -eq 0 && "$in_double" -eq 0 ]]; then
      if [[ "$char" == "&" && "$next" == "&" ]]; then
        flush_segment "$current"
        current=""
        i=$(( i + 2 ))
        continue
      fi

      if [[ "$char" == "|" && "$next" == "|" ]]; then
        flush_segment "$current"
        current=""
        i=$(( i + 2 ))
        continue
      fi

      if [[ "$char" == "|" || "$char" == ";" || "$char" == $'\n' || "$char" == $'\r' ]]; then
        flush_segment "$current"
        current=""
        i=$(( i + 1 ))
        continue
      fi
    fi

    current+="$char"
    i=$(( i + 1 ))
  done

  flush_segment "$current"
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

strip_leading_shell_wrappers() {
  local segment
  local first=""
  local rest=""

  segment=$(trim_leading_whitespace "$1")

  while [[ -n "$segment" ]]; do
    first="${segment%%[[:space:]]*}"
    if [[ "$first" != "$segment" ]]; then
      rest="${segment#"$first"}"
    else
      rest=""
    fi

    case "$first" in
      command|builtin|exec)
        segment=$(trim_leading_whitespace "$rest")
        if [[ "$segment" == --[[:space:]]* ]]; then
          segment="${segment#--}"
          segment=$(trim_leading_whitespace "$segment")
        fi
        ;;
      *)
        break
        ;;
    esac
  done

  printf '%s\n' "$segment"
}

normalize_command_executable() {
  local segment
  local first=""
  local rest=""

  segment=$(strip_leading_shell_wrappers "$1")
  [[ -n "$segment" ]] || {
    printf '\n'
    return 0
  }

  first="${segment%%[[:space:]]*}"
  if [[ "$first" != "$segment" ]]; then
    rest="${segment#"$first"}"
  fi

  if [[ "$first" == */* ]]; then
    first="${first##*/}"
  fi

  printf '%s%s\n' "$first" "$rest"
}

to_ascii_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

extract_percent_literal_token() {
  local text="$1"
  local open_delim=""
  local close_delim=""
  local body=""
  local token=""
  local remainder=""

  case "$text" in
    %q\(*|%q\{*|%q\[*|%q\<*|%Q\(*|%Q\{*|%Q\[*|%Q\<*|%x\(*|%x\{*|%x\[*|%x\<*)
      ;;
    *)
      return 1
      ;;
  esac

  open_delim="${text:2:1}"
  case "$open_delim" in
    '(') close_delim=')' ;;
    '{') close_delim='}' ;;
    '[') close_delim=']' ;;
    '<') close_delim='>' ;;
    *) return 1 ;;
  esac

  body="${text:3}"
  [[ "$body" == *"$close_delim"* ]] || return 1
  token="${body%%"$close_delim"*}"
  remainder="${body#"$token"}"
  remainder="${remainder#"$close_delim"}"

  printf '%s\n' "$token"
  printf '%s\n' "$remainder"
}

join_literal_arguments_from_text() {
  local text="$1"
  local token=""
  local literals=()
  local percent_result=""
  local percent_token=""
  local percent_remainder=""

  while :; do
    text=$(trim_leading_whitespace "$text")

    while [[ -n "$text" ]]; do
      case "$text" in
        ,*|\[*|\]*|\(*|\)*|\{*|\}*)
          text="${text#?}"
          text=$(trim_leading_whitespace "$text")
          continue
          ;;
      esac
      break
    done

    [[ -n "$text" ]] || break

    if [[ "$text" =~ ^\'([^\']*)\'(.*)$ ]]; then
      token="${BASH_REMATCH[1]}"
      text="${BASH_REMATCH[2]}"
      literals+=("$token")
      continue
    fi

    if [[ "$text" =~ ^\"([^\"]*)\"(.*)$ ]]; then
      token="${BASH_REMATCH[1]}"
      text="${BASH_REMATCH[2]}"
      literals+=("$token")
      continue
    fi

    if percent_result=$(extract_percent_literal_token "$text" 2>/dev/null); then
      percent_token=$(printf '%s\n' "$percent_result" | sed -n '1p')
      percent_remainder=$(printf '%s\n' "$percent_result" | sed -n '2p')
      token="$percent_token"
      text="$percent_remainder"
      literals+=("$token")
      continue
    fi

    break
  done

  [[ "${#literals[@]}" -gt 0 ]] || return 1
  printf '%s\n' "${literals[*]}"
}

resolve_percent_literal_expression() {
  local expression="$1"
  local percent_result=""

  expression=$(trim_leading_whitespace "$expression")
  expression=$(trim_trailing_whitespace "$expression")

  if percent_result=$(extract_percent_literal_token "$expression" 2>/dev/null); then
    printf '%s\n' "$percent_result" | sed -n '1p'
    return 0
  fi

  return 1
}

extract_ruby_string_assignment() {
  local ruby_code="$1"
  local variable_name="$2"
  local assignment_pattern
  local assignment_tail=""
  local literal=""

  assignment_pattern="(^|[^[:alnum:]_])${variable_name}[[:space:]]*=[[:space:]]*"

  if [[ "$ruby_code" =~ $assignment_pattern\'([^\']*)\' ]]; then
    printf '%s\n' "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "$ruby_code" =~ $assignment_pattern\"([^\"]*)\" ]]; then
    printf '%s\n' "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "$ruby_code" =~ $assignment_pattern(%[qQx][\(\{\[<].*) ]]; then
    assignment_tail="${BASH_REMATCH[2]}"
    literal=$(resolve_percent_literal_expression "$assignment_tail" || true)
    [[ -n "$literal" ]] || return 1
    printf '%s\n' "$literal"
    return 0
  fi

  return 1
}

resolve_ruby_command_expression() {
  local expression="$1"
  local ruby_code="$2"
  local literal=""

  literal=$(join_literal_arguments_from_text "$expression" || true)
  if [[ -n "$literal" ]]; then
    printf '%s\n' "$literal"
    return 0
  fi

  expression=$(trim_leading_whitespace "$expression")
  expression=$(trim_trailing_whitespace "$expression")

  if [[ "$expression" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*(,.*)?$ ]]; then
    literal=$(extract_ruby_string_assignment "$ruby_code" "${BASH_REMATCH[1]}" || true)
    [[ -n "$literal" ]] || return 1
    printf '%s\n' "$literal"
    return 0
  fi

  return 1
}

extract_python_string_assignment() {
  local python_code="$1"
  local variable_name="$2"
  local assignment_pattern

  assignment_pattern="(^|[^[:alnum:]_])${variable_name}[[:space:]]*=[[:space:]]*"

  if [[ "$python_code" =~ $assignment_pattern\'([^\']*)\' ]]; then
    printf '%s\n' "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "$python_code" =~ $assignment_pattern\"([^\"]*)\" ]]; then
    printf '%s\n' "${BASH_REMATCH[2]}"
    return 0
  fi

  return 1
}

collapse_duplicate_leading_token() {
  local command_text="$1"
  local first=""
  local second=""
  local remainder=""

  [[ "$command_text" == *" "* ]] || {
    printf '%s\n' "$command_text"
    return 0
  }

  first="${command_text%% *}"
  remainder="${command_text#"$first"}"
  remainder="${remainder#" "}"
  second="${remainder%% *}"

  if [[ -n "$first" && -n "$second" && "$first" == "$second" ]]; then
    printf '%s\n' "$remainder"
  else
    printf '%s\n' "$command_text"
  fi
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
  local nested_command=""
  local call_body

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
      call_body=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\((.*)\).*/\2/p')
      if [[ -n "$call_body" ]]; then
        nested_command=$(resolve_ruby_command_expression "$call_body" "$ruby_code" || true)
      fi
      if [[ -z "$nested_command" ]]; then
        call_body=$(printf '%s' "$ruby_code" | sed -nE 's/.*((Kernel\.)?(send|__send__))\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,(.*)\).*/\5/p')
        if [[ -n "$call_body" ]]; then
          nested_command=$(resolve_ruby_command_expression "$call_body" "$ruby_code" || true)
        fi
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE "s/.*(system|exec|spawn)\\([[:space:]]*'([^']*)'([[:space:]]*,.*)?\\).*/\\2/p")
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\([[:space:]]*"([^"]*)"([[:space:]]*,.*)?\).*/\2/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\([[:space:]]*%[qQ]\{([^}]*)\}([[:space:]]*,.*)?\).*/\2/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\([[:space:]]*%[qQ]\(([^)]*)\)([[:space:]]*,.*)?\).*/\2/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\([[:space:]]*%[qQ]\[([^]]*)\]([[:space:]]*,.*)?\).*/\2/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*(system|exec|spawn)\([[:space:]]*%[qQ]<([^>]*)>([[:space:]]*,.*)?\).*/\2/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE "s/.*((Kernel\\.)?(send|__send__))\\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,[[:space:]]*'([^']*)'([[:space:]]*,.*)?\\).*/\\5/p")
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*((Kernel\.)?(send|__send__))\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,[[:space:]]*"([^"]*)"([[:space:]]*,.*)?\).*/\5/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*((Kernel\.)?(send|__send__))\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,[[:space:]]*%[qQ]\{([^}]*)\}([[:space:]]*,.*)?\).*/\5/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*((Kernel\.)?(send|__send__))\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,[[:space:]]*%[qQ]\(([^)]*)\)([[:space:]]*,.*)?\).*/\5/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*((Kernel\.)?(send|__send__))\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,[[:space:]]*%[qQ]\[([^]]*)\]([[:space:]]*,.*)?\).*/\5/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*((Kernel\.)?(send|__send__))\([[:space:]]*:?(system|exec|spawn)[[:space:]]*,[[:space:]]*%[qQ]<([^>]*)>([[:space:]]*,.*)?\).*/\5/p')
      fi
      if [[ -z "$nested_command" ]]; then
        # shellcheck disable=SC2016
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*`([^`]*)`.*/\1/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*%x\{([^}]*)\}.*/\1/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*%x\(([^)]*)\).*/\1/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*%x\[([^]]*)\].*/\1/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$ruby_code" | sed -nE 's/.*%x<([^>]*)>.*/\1/p')
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

extract_python_wrapper_payload() {
  local segment
  local rest
  local token
  local python_code
  local nested_command=""
  local call_body

  segment=$(trim_enclosing_grouping "$1")
  [[ "$segment" =~ ^python([0-9]+(\.[0-9]+)?)?([[:space:]]|$) ]] || return 1

  rest="${segment#"${BASH_REMATCH[0]}"}"
  while :; do
    rest=$(trim_leading_whitespace "$rest")
    [[ -n "$rest" ]] || return 1

    token="${rest%%[[:space:]]*}"
    if [[ "$token" == "$rest" ]]; then
      return 1
    fi

    if [[ "$token" == "-c" ]]; then
      rest="${rest#"$token"}"
      python_code=$(trim_matching_outer_quotes "$rest")
      nested_command=$(printf '%s' "$python_code" | sed -nE "s/.*os\\.system\\([[:space:]]*'([^']*)'([[:space:]]*)\\).*/\\1/p")
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$python_code" | sed -nE 's/.*os\.system\([[:space:]]*"([^"]*)"([[:space:]]*)\).*/\1/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$python_code" | sed -nE "s/.*getattr\\([[:space:]]*os[[:space:]]*,[[:space:]]*'system'[[:space:]]*\\)\\([[:space:]]*'([^']*)'([[:space:]]*)\\).*/\\1/p")
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$python_code" | sed -nE 's/.*getattr\([[:space:]]*os[[:space:]]*,[[:space:]]*"system"[[:space:]]*\)\([[:space:]]*"([^"]*)"([[:space:]]*)\).*/\1/p')
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$python_code" | sed -nE "s/.*(([A-Za-z_][A-Za-z0-9_]*)\\.)?(run|call|Popen|check_call|check_output)\\([[:space:]]*'([^']*)'([[:space:]]*,[^)]*shell[[:space:]]*=[[:space:]]*True[^)]*)?\\).*/\\4/p")
      fi
      if [[ -z "$nested_command" ]]; then
        nested_command=$(printf '%s' "$python_code" | sed -nE 's/.*(([A-Za-z_][A-Za-z0-9_]*)\.)?(run|call|Popen|check_call|check_output)\([[:space:]]*"([^"]*)"([[:space:]]*,[^)]*shell[[:space:]]*=[[:space:]]*True[^)]*)?\).*/\4/p')
      fi
      if [[ -z "$nested_command" ]]; then
        if [[ "$python_code" =~ os\.system\([[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*\) ]]; then
          nested_command=$(extract_python_string_assignment "$python_code" "${BASH_REMATCH[1]}" || true)
        fi
      fi
      if [[ -z "$nested_command" ]]; then
        if [[ "$python_code" =~ getattr\([[:space:]]*os[[:space:]]*,[[:space:]]*['\"]system['\"][[:space:]]*\)\([[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*\) ]]; then
          nested_command=$(extract_python_string_assignment "$python_code" "${BASH_REMATCH[1]}" || true)
        fi
      fi
      if [[ -z "$nested_command" ]]; then
        token=$(printf '%s' "$python_code" | sed -nE 's/.*(([A-Za-z_][A-Za-z0-9_]*)\.)?(run|call|Popen|check_call|check_output)\([[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*,[^)]*shell[[:space:]]*=[[:space:]]*True[^)]*\).*/\4/p')
        if [[ -n "$token" ]]; then
          nested_command=$(extract_python_string_assignment "$python_code" "$token" || true)
        fi
      fi
      if [[ -z "$nested_command" ]]; then
        call_body=$(printf '%s' "$python_code" | sed -nE 's/.*(([A-Za-z_][A-Za-z0-9_]*)\.)?(run|call|Popen|check_call|check_output)\((.*)\).*/\4/p')
        if [[ -n "$call_body" ]]; then
          nested_command=$(join_literal_arguments_from_text "$call_body" || true)
        fi
      fi
      if [[ -z "$nested_command" ]]; then
        call_body=$(printf '%s' "$python_code" | sed -nE 's/.*os\.execv[p]?\((.*)\).*/\1/p')
        if [[ -n "$call_body" ]]; then
          nested_command=$(join_literal_arguments_from_text "$call_body" || true)
          nested_command=$(collapse_duplicate_leading_token "$nested_command")
        fi
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

emit_command_variants_for_stream() {
  local command_text="$1"
  local segment=""

  emit_command_variants "$command_text"

  while IFS= read -r segment; do
    segment=$(strip_leading_env_prefixes "$segment")
    [[ -n "$segment" ]] || continue
    emit_command_variants "$segment"
  done < <(normalize_command_segments "$command_text")
}

emit_command_variants() {
  local command_text="$1"
  local depth="${2:-2}"
  local nested=""
  local normalized=""

  normalized=$(trim_enclosing_grouping "$command_text")
  normalized=$(normalize_command_executable "$normalized")
  [[ -n "$normalized" ]] || return 0

  printf '%s\n' "$normalized"

  [[ "$depth" -gt 0 ]] || return 0

  if nested=$(extract_shell_wrapper_payload "$normalized"); then
    emit_command_variants "$nested" $(( depth - 1 ))
  fi

  if nested=$(extract_ruby_wrapper_payload "$normalized"); then
    emit_command_variants "$nested" $(( depth - 1 ))
  fi

  if nested=$(extract_python_wrapper_payload "$normalized"); then
    emit_command_variants "$nested" $(( depth - 1 ))
  fi
}

is_destructive_db_command() {
  local command_text="$1"
  local candidate

  while IFS= read -r candidate; do
    if [[ "$candidate" =~ ^((bundle[[:space:]]+exec[[:space:]]+)?((\./)?bin/)?(rails|rake))([[:space:]]|$) ]] &&
      printf '%s' "$candidate" | grep -qE "(^|[[:space:]])['\"]?db:(drop|reset|purge)(:[[:alnum:]_:-]+)?['\"]?([[:space:]]|$)"; then
      return 0
    fi
  done < <(emit_command_variants_for_stream "$command_text")

  return 1
}

is_destructive_redis_command() {
  local command_text="$1"
  local candidate
  local lowered

  while IFS= read -r candidate; do
    lowered=$(to_ascii_lower "$candidate")
    if [[ "$lowered" =~ ^redis-cli([[:space:]]+[^[:space:]]+)*[[:space:]]+flush(all|db)([[:space:]]|$) ]]; then
      return 0
    fi
  done < <(emit_command_variants_for_stream "$command_text")

  return 1
}

is_force_push_command() {
  local command_text="$1"
  local candidate

  while IFS= read -r candidate; do
    if [[ "$candidate" =~ ^git([[:space:]]+-c[[:space:]]+[^[:space:]]+)*[[:space:]]+push([[:space:]]|$) ]] &&
      printf '%s' "$candidate" | grep -qE '(^|[[:space:]])((--force|-f)([[:space:]]|$)|\+[^[:space:]]+($|[[:space:]])|[^[:space:]]+:\+[^[:space:]]+($|[[:space:]]))'; then
      return 0
    fi
  done < <(emit_command_variants_for_stream "$command_text")

  return 1
}

is_harmless_env_probe() {
  printf '%s' "$1" | grep -qE '^(echo|printf|cat|env|export|declare|typeset|readonly|unset|true|false)([[:space:]]|$)'
}

candidate_mentions_production_env() {
  printf '%s' "$1" | grep -qiE '(^|[[:space:]])(RAILS_ENV|RACK_ENV)=["'\'']?(prod|production)["'\'']?([[:space:]]|$)'
}

segment_exports_production_env() {
  printf '%s' "$1" | grep -qiE '^[[:space:]]*export([[:space:]]+[^[:space:]]+)*[[:space:]]+(RAILS_ENV|RACK_ENV)=["'\'']?(prod|production)["'\'']?([[:space:]]|$)'
}

segment_clears_production_env() {
  local segment="$1"

  if printf '%s' "$segment" | grep -qiE '^[[:space:]]*unset[[:space:]]+(RAILS_ENV|RACK_ENV)([[:space:]]|$)'; then
    return 0
  fi

  if printf '%s' "$segment" | grep -qiE '^[[:space:]]*export([[:space:]]+[^[:space:]]+)*[[:space:]]+(RAILS_ENV|RACK_ENV)=' &&
    ! segment_exports_production_env "$segment"; then
    return 0
  fi

  return 1
}

is_production_env_command() {
  local command_text="$1"
  local candidate
  local production_env_active=false
  local segment

  while IFS= read -r candidate; do
    split_leading_env_prefixes "$candidate"
    if [[ -n "$LEADING_ENV_PREFIXES_RESULT" && -n "$STRIPPED_COMMAND_RESULT" ]] &&
      printf '%s' "$LEADING_ENV_PREFIXES_RESULT" | grep -qiE '(^|[[:space:]])(RAILS_ENV|RACK_ENV)=["'\'']?(prod|production)["'\'']?([[:space:]]|$)' &&
      ! is_harmless_env_probe "$STRIPPED_COMMAND_RESULT"; then
      return 0
    fi

    if candidate_mentions_production_env "$candidate" && ! is_harmless_env_probe "$candidate"; then
      return 0
    fi
  done < <(emit_command_variants_for_stream "$command_text")

  while IFS= read -r segment; do
    if segment_exports_production_env "$segment"; then
      production_env_active=true
    elif segment_clears_production_env "$segment"; then
      production_env_active=false
    elif [[ "$production_env_active" == "true" ]] && ! is_harmless_env_probe "$segment"; then
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
