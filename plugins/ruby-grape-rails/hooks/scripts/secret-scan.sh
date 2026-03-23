#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Run betterleaks scan on changed files to detect secrets
# This hook runs after file writes to check for accidentally committed secrets
#
# Hook input: JSON via stdin with .tool_input.file_path
# Exit 2 with stderr message to surface warning to Claude

command -v jq >/dev/null 2>&1 || exit 0
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
REPO_ROOT=$(resolve_workspace_root "$INPUT")
HOOK_MODE=$(resolve_hook_mode "$REPO_ROOT")

FILE_PATH=""
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || printf '')
if [[ -n "$FILE_PATH" && "$FILE_PATH" != /* ]]; then
  FILE_PATH="${REPO_ROOT}/${FILE_PATH#./}"
fi

# Check if betterleaks is available
BETTERLEAKS_PATH="${BETTERLEAKS_PATH:-}"
if [[ -z "$BETTERLEAKS_PATH" ]] && command -v betterleaks >/dev/null 2>&1; then
  BETTERLEAKS_PATH=$(command -v betterleaks)
fi

if [[ -z "$BETTERLEAKS_PATH" || ! -x "$BETTERLEAKS_PATH" ]]; then
  # Betterleaks not available, skip silently
  exit 0
fi

is_secret_relevant_path() {
  local path="$1"
  case "$path" in
    *.env|*.env.*|*.key|*.pem|*.p12|*.pfx|*.jks|*.crt|*.cer|*.csr|*.tfvars|*.tfvars.json|*.kubeconfig|*.properties|*.toml|*.ini|*.conf|*.yaml|*.yml|*.json|*.log|*secret*|*credential*|*token*|*api_key*|*apikey*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

input_has_secret_indicators() {
  local snippet

  snippet=$(printf '%s' "$INPUT" | jq -r '(.tool_input.content // .tool_input.new_string // empty)' 2>/dev/null) || snippet=""
  [[ -n "$snippet" ]] || return 1

  printf '%s' "$snippet" | grep -Eqi \
    '(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|api[_-]?key|secret|token|client_secret|aws_secret_access_key|xox[baprs]-|ghp_[A-Za-z0-9]{20,})'
}

emit_secret_warning() {
  local target="$1"
  local result="$2"

  echo "⚠️  Potential secret detected in $target"
  printf '%s\n' "$result"
  echo
  echo "To ignore: add '#betterleaks:allow' comment to the line"
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
  target_file="${target_dir}/$(basename -- "$source_file")"
  cp "$source_path" "$target_file"
}

if [[ -z "$FILE_PATH" ]]; then
  # No specific file: only strict mode does broader recent-change scans.
  [[ "$HOOK_MODE" == "strict" ]] || exit 0

  if (cd "$REPO_ROOT" && git rev-parse --git-dir >/dev/null 2>&1); then
    TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/rb-secret-scan.XXXXXX") || exit 0
    [[ -n "$TMP_DIR" ]] || exit 0

    trap 'rm -rf -- "$TMP_DIR"' EXIT HUP INT TERM

    if (cd "$REPO_ROOT" && git rev-parse --verify HEAD >/dev/null 2>&1); then
      while IFS= read -r file; do
        [[ -n "$file" ]] || continue
        copy_into_tmpdir "${REPO_ROOT}/${file#./}" "$TMP_DIR" 2>/dev/null || true
      done < <(cd "$REPO_ROOT" && git diff --name-only --diff-filter=ACMR HEAD -- 2>/dev/null | head -20)
    else
      while IFS= read -r file; do
        [[ -n "$file" ]] || continue
        copy_into_tmpdir "${REPO_ROOT}/${file#./}" "$TMP_DIR" 2>/dev/null || true
      done < <(cd "$REPO_ROOT" && git ls-files 2>/dev/null | head -20)
    fi

    if find "$TMP_DIR" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
      RESULT=$("$BETTERLEAKS_PATH" dir "$TMP_DIR" --no-banner --redact=100 2>/dev/null || true)
      if [[ -n "$RESULT" ]]; then
        emit_secret_warning "recent changes" "$RESULT"
        exit 2
      fi
    fi
  fi
else
  if [[ "$HOOK_MODE" != "strict" ]] && ! is_secret_relevant_path "$FILE_PATH" && ! input_has_secret_indicators; then
    exit 0
  fi

  if [[ -f "$FILE_PATH" && ! -L "$FILE_PATH" ]]; then
    RESULT=$("$BETTERLEAKS_PATH" dir "$FILE_PATH" --no-banner --redact=100 2>/dev/null || true)
    if [[ -n "$RESULT" ]]; then
      emit_secret_warning "$FILE_PATH" "$RESULT"
      exit 2
    fi
  fi
fi

exit 0
