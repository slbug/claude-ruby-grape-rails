#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Run betterleaks scan on changed files to detect secrets
# This hook runs after file writes to check for accidentally committed secrets
#
# Hook input: JSON via stdin with .tool_input.file_path
# Exit 2 with stderr message to surface warning to Claude

command -v jq >/dev/null 2>&1 || exit 0

# Parse hook input from stdin
FILE_PATH=""
if [[ ! -t 0 ]]; then
  FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null || printf '')
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
  # No specific file, check if we're in a git repo and scan last commit
  if git rev-parse --git-dir >/dev/null 2>&1; then
    TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/rb-secret-scan.XXXXXX") || exit 0
    [[ -n "$TMP_DIR" ]] || exit 0

    trap 'rm -rf -- "$TMP_DIR"' EXIT HUP INT TERM

    if git rev-parse --verify HEAD >/dev/null 2>&1; then
      git diff --name-only --diff-filter=ACMR HEAD -- 2>/dev/null | head -20 | while IFS= read -r file; do
        copy_into_tmpdir "$file" "$TMP_DIR" 2>/dev/null || true
      done
    else
      git ls-files 2>/dev/null | head -20 | while IFS= read -r file; do
        copy_into_tmpdir "$file" "$TMP_DIR" 2>/dev/null || true
      done
    fi

    if find "$TMP_DIR" -mindepth 1 -print -quit 2>/dev/null | grep -q .; then
      echo "🔒 Scanning recent changes for secrets..."
      "$BETTERLEAKS_PATH" dir "$TMP_DIR" --no-banner --redact=100 >/dev/null 2>&1 || true
    fi
  fi
else
  # Scan specific file that was just written
  if [[ -f "$FILE_PATH" && ! -L "$FILE_PATH" ]]; then
    # Quick scan on the single file
    RESULT=$("$BETTERLEAKS_PATH" dir "$FILE_PATH" --no-banner --redact=100 2>/dev/null || true)
    if [[ -n "$RESULT" ]]; then
      echo "⚠️  Potential secret detected in $FILE_PATH"
      echo "$RESULT"
      echo ""
      echo "To ignore: add '#betterleaks:allow' comment to the line"
      exit 2
    fi
  fi
fi

exit 0
