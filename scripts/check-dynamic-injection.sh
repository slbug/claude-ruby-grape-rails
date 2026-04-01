#!/usr/bin/env bash
# Blocks dynamic context injection syntax (!`command`) in tracked plugin and
# contributor docs/config surfaces when git metadata is available. In non-git
# contexts, it falls back to a best-effort scan of the same target paths.
# This feature executes shell commands at skill load time. The Ruby plugin does
# not use it and treats it as unsafe in these surfaces.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCAN_TARGETS=(plugins .claude .claude-plugin README.md CLAUDE.md)
MAX_FALLBACK_FILES="${RUBY_PLUGIN_DYNAMIC_INJECTION_MAX_FILES:-500}"
MAX_FALLBACK_BYTES="${RUBY_PLUGIN_DYNAMIC_INJECTION_MAX_BYTES:-5242880}"
# shellcheck disable=SC2016
PATTERN='(^|[^[:alnum:]_`])!`[^`]+`'
FOUND=0
FALLBACK_PARTIAL=0
FALLBACK_FILES_SCANNED=0
FALLBACK_BYTES_SCANNED=0

positive_int_or_default() {
  local raw="$1"
  local fallback="$2"
  if [[ "$raw" =~ ^[1-9][0-9]*$ ]]; then
    printf '%s\n' "$raw"
  else
    printf '%s\n' "$fallback"
  fi
}

MAX_FALLBACK_FILES="$(positive_int_or_default "$MAX_FALLBACK_FILES" 500)"
MAX_FALLBACK_BYTES="$(positive_int_or_default "$MAX_FALLBACK_BYTES" 5242880)"

scan_file() {
  local file="$1"
  local matches

  matches=$(grep -En -- "$PATTERN" "$file" 2>/dev/null || true)

  if [[ -n "$matches" ]]; then
    echo "BLOCKED: Dynamic context injection found:"
    echo "$matches"
    echo
    FOUND=1
  fi
}

if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  while IFS= read -r -d '' file; do
    case "$file" in
      *.md|*.json|*.yml|*.yaml) ;;
      *) continue ;;
    esac
    [[ -f "${REPO_ROOT}/${file}" ]] || continue
    scan_file "${REPO_ROOT}/${file}"
  done < <(git -C "$REPO_ROOT" ls-files -z -- "${SCAN_TARGETS[@]}")
else
  for target in "${SCAN_TARGETS[@]}"; do
    if [[ ! -e "${REPO_ROOT}/${target}" ]]; then
      continue
    fi

    while IFS= read -r -d '' file; do
      [[ -n "$file" && -f "$file" ]] || continue
      file_size=$(wc -c < "$file" 2>/dev/null || echo 0)
      if [[ "$FALLBACK_FILES_SCANNED" -ge "$MAX_FALLBACK_FILES" ]] ||
        [[ $(( FALLBACK_BYTES_SCANNED + file_size )) -gt "$MAX_FALLBACK_BYTES" ]]; then
        FALLBACK_PARTIAL=1
        break
      fi
      FALLBACK_FILES_SCANNED=$((FALLBACK_FILES_SCANNED + 1))
      FALLBACK_BYTES_SCANNED=$((FALLBACK_BYTES_SCANNED + file_size))
      scan_file "$file"
    done < <(find "${REPO_ROOT}/${target}" -type f \( -name '*.md' -o -name '*.json' -o -name '*.yml' -o -name '*.yaml' \) -print0 2>/dev/null || true)

    [[ "$FALLBACK_PARTIAL" -eq 1 ]] && break
  done
fi

if [[ "$FOUND" -eq 1 ]]; then
  echo "========================================="
  echo "ERROR: Dynamic context injection detected"
  echo "========================================="
  echo
  echo "The !\`command\` syntax executes shell commands and injects stdout into Claude context."
  echo "Do not use it in tracked plugin or contributor docs/config files. Use normal tools/agents instead."
  exit 1
fi

if [[ "$FALLBACK_PARTIAL" -eq 1 ]]; then
  echo "ERROR: fallback dynamic-injection scan hit file/size caps; results are partial." >&2
  echo "ERROR: a clean result cannot be trusted because only the scanned subset was checked." >&2
  exit 1
fi

echo "No dynamic context injection found."
