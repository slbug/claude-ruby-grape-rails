#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Run betterleaks scan on changed files to detect secrets
# This hook runs after file writes to check for accidentally committed secrets
#
# Hook input: JSON via stdin with .tool_input.file_path
# Exit 2 with stderr message to surface warning to Claude
# Policy: security-sensitive — secret scanning fails closed when
# payload/root/scanner coverage cannot be trusted.

HOOK_NAME="${BASH_SOURCE[0]##*/}"

RUBY_PLUGIN_BETTERLEAKS_TIMEOUT="${RUBY_PLUGIN_BETTERLEAKS_TIMEOUT:-60}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

emit_root_resolution_block() {
  echo "BLOCKED: ${HOOK_NAME} could not resolve the workspace root for secret scanning." >&2
  echo "Fix the hook payload or workspace layout before continuing." >&2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
command -v grep >/dev/null 2>&1 || emit_missing_dependency_block "grep"
command -v cat >/dev/null 2>&1 || emit_missing_dependency_block "cat"
command -v cp >/dev/null 2>&1 || emit_missing_dependency_block "cp"
command -v find >/dev/null 2>&1 || emit_missing_dependency_block "find"
command -v mkdir >/dev/null 2>&1 || emit_missing_dependency_block "mkdir"
command -v mktemp >/dev/null 2>&1 || emit_missing_dependency_block "mktemp"
command -v sed >/dev/null 2>&1 || emit_missing_dependency_block "sed"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMEOUT_LIB="${SCRIPT_DIR}/timeout-lib.sh"
if [[ -r "$TIMEOUT_LIB" && ! -L "$TIMEOUT_LIB" ]]; then
  # shellcheck disable=SC1090,SC1091
  source "$TIMEOUT_LIB"
else
  TIMEOUT_CMD=""
  run_with_timeout() { shift; "$@"; }
fi
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
REPO_ROOT=$(resolve_workspace_root "$INPUT") || {
  emit_root_resolution_block
  exit 2
}
if [[ -z "$REPO_ROOT" ]]; then
  emit_root_resolution_block
  exit 2
fi
HOOK_MODE=$(resolve_hook_mode "$REPO_ROOT")
STRICT_SCAN_MAX_FILES="${RUBY_PLUGIN_SECRET_SCAN_MAX_FILES:-200}"

if [[ ! "$STRICT_SCAN_MAX_FILES" =~ ^[0-9]+$ ]] || [[ "$STRICT_SCAN_MAX_FILES" -le 0 ]]; then
  STRICT_SCAN_MAX_FILES=200
fi

FILE_PATH=""
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || printf '')
if [[ -n "$FILE_PATH" ]]; then
  FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || FILE_PATH=""
fi

# Check if betterleaks is available
BETTERLEAKS_PATH="${BETTERLEAKS_PATH:-}"
if [[ -z "$BETTERLEAKS_PATH" ]] && command -v betterleaks >/dev/null 2>&1; then
  BETTERLEAKS_PATH=$(command -v betterleaks)
fi
BETTERLEAKS_RESULT=""
BETTERLEAKS_ERROR=""

emit_missing_betterleaks_block() {
  local target="$1"

  echo "BLOCKED: Betterleaks is unavailable; ${HOOK_NAME} cannot scan ${target} for secrets." >&2
  echo "Install betterleaks or set BETTERLEAKS_PATH to restore secret scanning." >&2
}

payload_secret_snippet() {
  printf '%s' "$INPUT" | jq -r '(.tool_input.content // .tool_input.new_string // empty)' 2>/dev/null
}

input_has_secret_indicators() {
  local snippet

  snippet=$(payload_secret_snippet 2>/dev/null) || snippet=""
  [[ -n "$snippet" ]] || return 1

  printf '%s' "$snippet" | grep -Eqi \
    '(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|api[_-]?key[[:space:]]*[:=]|client_secret[[:space:]]*[:=]|aws_secret_access_key[[:space:]]*[:=]|authorization[[:space:]]*:[[:space:]]*bearer[[:space:]]+[A-Za-z0-9._-]+|xox[baprs]-|ghp_[A-Za-z0-9]{20,})'
}

if [[ -z "$BETTERLEAKS_PATH" || ! -x "$BETTERLEAKS_PATH" ]]; then
  emit_missing_betterleaks_block "${FILE_PATH:-this change}"
  exit 2
fi

is_binaryish_path() {
  local path="$1"
  case "$path" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.ico|*.bmp|*.tif|*.tiff|*.mp3|*.mp4|*.mov|*.avi|*.mkv|*.wav|*.flac|*.zip|*.gz|*.tgz|*.bz2|*.xz|*.7z|*.rar|*.pdf|*.sqlite|*.sqlite3|*.db|*.bin|*.exe|*.dll|*.so|*.dylib|*.class|*.jar|*.war|*.ear|*.woff|*.woff2|*.ttf|*.eot)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

emit_secret_warning() {
  local target="$1"
  local result="$2"

  echo "⚠️  Potential secret detected in $target" >&2
  printf '%s\n' "$result" >&2
  echo >&2
  echo "To ignore: add '#betterleaks:allow' comment to the line" >&2
}

emit_scanner_failure_warning() {
  local target="$1"
  local status="$2"
  local err_preview="$3"

  echo "⚠️  Betterleaks failed while scanning ${target} (exit ${status})." >&2
  if [[ -n "$err_preview" ]]; then
    printf 'Scanner output:\n%s\n' "$err_preview" >&2
  fi
}

emit_truncation_warning() {
  local source_label="$1"
  local limit="$2"

  echo "⚠️  Strict secret scan truncated after ${limit} files from ${source_label}" >&2
  echo "Run betterleaks manually for full coverage if needed." >&2
}

emit_scan_setup_failure_warning() {
  local target="$1"

  echo "⚠️  Betterleaks setup failed for ${target}; secret scan could not create a temporary workspace." >&2
  echo "Fix TMPDIR permissions or disk space to restore secret scanning." >&2
}

emit_recent_changes_scan_unavailable_warning() {
  local reason="$1"

  echo "BLOCKED: ${HOOK_NAME} could not perform strict recent-change scanning because ${reason}." >&2
  echo "Provide a specific file path or restore Git access before continuing." >&2
}

emit_scan_staging_failure_warning() {
  local source_label="$1"
  local failures="$2"

  echo "BLOCKED: ${HOOK_NAME} could not stage ${failures} file(s) for strict secret scanning from ${source_label}." >&2
  echo "Recent-change coverage is incomplete; fix the filesystem permissions and retry." >&2
}

new_secret_scan_tmpdir() {
  local tmp_dir

  tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/rb-secret-scan.XXXXXX") || return 1
  [[ -n "$tmp_dir" ]] || return 1
  [[ "$tmp_dir" == "${TMPDIR:-/tmp}/rb-secret-scan."* ]] || return 1

  printf '%s\n' "$tmp_dir"
}

run_betterleaks_dir() {
  local target_dir="$1"
  local result_file
  local err_file
  local status

  result_file=$(mktemp "${TMPDIR:-/tmp}/rb-secret-scan.result.XXXXXX") || return 1
  err_file=$(mktemp "${TMPDIR:-/tmp}/rb-secret-scan.err.XXXXXX") || {
    safe_remove_temp_file "${result_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.result.*" || true
    return 1
  }

  BETTERLEAKS_RESULT=""
  BETTERLEAKS_ERROR=""

  run_with_timeout "$RUBY_PLUGIN_BETTERLEAKS_TIMEOUT" "$BETTERLEAKS_PATH" dir "$target_dir" --no-banner --redact=100 >"$result_file" 2>"$err_file"
  status=$?
  if [[ -n "$TIMEOUT_CMD" && "$status" -eq 124 ]]; then
    echo "WARNING: betterleaks timed out after ${RUBY_PLUGIN_BETTERLEAKS_TIMEOUT}s. Failing closed." >&2
    safe_remove_temp_file "${result_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.result.*" || true
    safe_remove_temp_file "${err_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.err.*" || true
    return 2
  fi
  BETTERLEAKS_RESULT=$(cat "$result_file" 2>/dev/null || true)
  BETTERLEAKS_ERROR=$(sed -n '1,5p' "$err_file" 2>/dev/null || true)

  if [[ -n "$BETTERLEAKS_RESULT" || "$status" -eq 0 ]]; then
    safe_remove_temp_file "${result_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.result.*" || true
    safe_remove_temp_file "${err_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.err.*" || true
    return 0
  fi

  safe_remove_temp_file "${result_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.result.*" || true
  safe_remove_temp_file "${err_file:-}" "${TMPDIR:-/tmp}/rb-secret-scan.err.*" || true
  return "$status"
}

copy_into_tmpdir() {
  local source_file="$1"
  local tmp_dir="$2"
  local source_path="$source_file"
  local target_dir
  local target_file

  [[ -f "$source_file" && ! -L "$source_file" ]] || return 1

  if [[ "$source_path" != /* ]]; then
    source_path="./${source_path#./}"
  fi

  case "$source_file" in
    */*) target_dir="${tmp_dir}/${source_file%/*}" ;;
    *) target_dir="$tmp_dir" ;;
  esac

  mkdir -p -- "$target_dir" || return 1
  target_file="${target_dir}/$(path_basename "$source_file")"
  cp "$source_path" "$target_file"
}

write_inline_payload_to_tmpdir() {
  local snippet="$1"
  local tmp_dir="$2"
  local target_dir="${tmp_dir}/inline"
  local target_file="${target_dir}/payload.txt"

  [[ -n "$snippet" ]] || return 1
  mkdir -p -- "$target_dir" || return 1
  printf '%s\n' "$snippet" > "$target_file"
}

copy_strict_scan_input() {
  local tmp_dir="$1"
  local source_label="$2"
  local file
  local local_resolved
  local scanned=0
  local truncated=false
  local copy_failures=0

  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    scanned=$((scanned + 1))
    if [[ "$scanned" -gt "$STRICT_SCAN_MAX_FILES" ]]; then
      truncated=true
      break
    fi

    local_resolved=$(resolve_workspace_file_path "$REPO_ROOT" "$file") || continue
    is_path_within_root "$REPO_ROOT" "$local_resolved" || continue
    if ! copy_into_tmpdir "$local_resolved" "$tmp_dir" 2>/dev/null; then
      copy_failures=$((copy_failures + 1))
    fi
  done

  if [[ "$truncated" == "true" ]]; then
    emit_truncation_warning "$source_label" "$STRICT_SCAN_MAX_FILES"
  fi

  if [[ "$copy_failures" -gt 0 ]]; then
    emit_scan_staging_failure_warning "$source_label" "$copy_failures"
    return 1
  fi
}

if [[ -z "$FILE_PATH" ]]; then
  inline_snippet=$(payload_secret_snippet 2>/dev/null || printf '')
  if [[ -n "$inline_snippet" ]]; then
    TMP_DIR=$(new_secret_scan_tmpdir) || {
      emit_scan_setup_failure_warning "inline hook payload"
      exit 2
    }

    # shellcheck disable=SC2317,SC2329 # invoked indirectly via trap
    cleanup_inline_secret_scan_tmpdir() {
      safe_remove_temp_dir "${TMP_DIR:-}" "${TMPDIR:-/tmp}/rb-secret-scan.*" || true
    }
    trap cleanup_inline_secret_scan_tmpdir EXIT HUP INT TERM

    write_inline_payload_to_tmpdir "$inline_snippet" "$TMP_DIR" || {
      emit_scan_setup_failure_warning "inline hook payload"
      exit 2
    }

    if run_betterleaks_dir "$TMP_DIR"; then
      if [[ -n "$BETTERLEAKS_RESULT" ]]; then
        emit_secret_warning "inline hook payload" "$BETTERLEAKS_RESULT"
        exit 2
      fi
    else
      emit_scanner_failure_warning "inline hook payload" "$?" "$BETTERLEAKS_ERROR"
      exit 2
    fi

    exit 0
  fi

  # No specific file: only strict mode does broader recent-change scans.
  [[ "$HOOK_MODE" == "strict" ]] || exit 0

  command -v git >/dev/null 2>&1 || {
    emit_recent_changes_scan_unavailable_warning "git is unavailable"
    exit 2
  }
  command -v awk >/dev/null 2>&1 || emit_missing_dependency_block "awk"

  if ! (cd "$REPO_ROOT" && git rev-parse --git-dir >/dev/null 2>&1); then
    emit_recent_changes_scan_unavailable_warning "Git metadata is unavailable"
    exit 2
  fi

  TMP_DIR=$(new_secret_scan_tmpdir) || {
    emit_scan_setup_failure_warning "recent changes"
    exit 2
  }

  # shellcheck disable=SC2317,SC2329 # invoked indirectly via trap
  cleanup_secret_scan_tmpdir() {
    safe_remove_temp_dir "${TMP_DIR:-}" "${TMPDIR:-/tmp}/rb-secret-scan.*" || true
  }
  trap cleanup_secret_scan_tmpdir EXIT HUP INT TERM

  if (cd "$REPO_ROOT" && git rev-parse --verify HEAD >/dev/null 2>&1); then
    copy_strict_scan_input "$TMP_DIR" "changed and untracked files" < <(
      cd "$REPO_ROOT" && {
        git diff --name-only --diff-filter=ACMR HEAD -- 2>/dev/null
        git ls-files --others --exclude-standard 2>/dev/null
      } | awk 'NF && !seen[$0]++'
    ) || exit 2
  else
    copy_strict_scan_input "$TMP_DIR" "tracked and untracked files" < <(
      cd "$REPO_ROOT" && git ls-files --cached --others --exclude-standard 2>/dev/null | awk 'NF && !seen[$0]++'
    ) || exit 2
  fi

  if find "$TMP_DIR" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
    if run_betterleaks_dir "$TMP_DIR"; then
      if [[ -n "$BETTERLEAKS_RESULT" ]]; then
        emit_secret_warning "recent changes" "$BETTERLEAKS_RESULT"
        exit 2
      fi
    else
      emit_scanner_failure_warning "recent changes" "$?" "$BETTERLEAKS_ERROR"
      exit 2
    fi
  fi
else
  if [[ "$HOOK_MODE" != "strict" ]] && is_binaryish_path "$FILE_PATH" && ! input_has_secret_indicators; then
    exit 0
  fi

  if [[ -f "$FILE_PATH" && ! -L "$FILE_PATH" ]] && is_path_within_root "$REPO_ROOT" "$FILE_PATH"; then
    TMP_DIR=$(new_secret_scan_tmpdir) || {
      emit_scan_setup_failure_warning "$FILE_PATH"
      exit 2
    }

    # shellcheck disable=SC2317,SC2329 # invoked indirectly via trap
    cleanup_single_secret_scan_tmpdir() {
      safe_remove_temp_dir "${TMP_DIR:-}" "${TMPDIR:-/tmp}/rb-secret-scan.*" || true
    }
    trap cleanup_single_secret_scan_tmpdir EXIT HUP INT TERM

    copy_into_tmpdir "$FILE_PATH" "$TMP_DIR" 2>/dev/null || {
      emit_scan_setup_failure_warning "$FILE_PATH"
      exit 2
    }

    if find "$TMP_DIR" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
      if run_betterleaks_dir "$TMP_DIR"; then
        if [[ -n "$BETTERLEAKS_RESULT" ]]; then
          emit_secret_warning "$FILE_PATH" "$BETTERLEAKS_RESULT"
          exit 2
        fi
      else
        status=$?
        emit_scanner_failure_warning "$FILE_PATH" "$status" "$BETTERLEAKS_ERROR"
        exit 2
      fi
    fi
  fi
fi

exit 0
