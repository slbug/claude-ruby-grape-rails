#!/usr/bin/env bash
# Blocks dynamic context injection syntax (!`command`) in tracked plugin and
# contributor docs/config surfaces when git metadata is available. In non-git
# contexts, it falls back to a best-effort scan of the same target paths.
# This feature executes shell commands at skill load time. The Ruby plugin does
# not use it and treats it as unsafe in these surfaces.

set -euo pipefail

SCAN_TARGETS=(plugins .claude .claude-plugin README.md CLAUDE.md)
# shellcheck disable=SC2016
PATTERN='(^|[^[:alnum:]_`])!`[^`]+`'
FOUND=0

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

if git rev-parse --git-dir >/dev/null 2>&1; then
  while IFS= read -r -d '' file; do
    case "$file" in
      *.md|*.json) ;;
      *) continue ;;
    esac
    [[ -f "$file" ]] || continue
    scan_file "$file"
  done < <(git ls-files -z -- "${SCAN_TARGETS[@]}")
else
  for target in "${SCAN_TARGETS[@]}"; do
    if [[ ! -e "$target" ]]; then
      continue
    fi

    while IFS= read -r -d '' file; do
      [[ -n "$file" && -f "$file" ]] || continue
      scan_file "$file"
    done < <(find "$target" -type f \( -name '*.md' -o -name '*.json' \) -print0 2>/dev/null || true)
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

echo "No dynamic context injection found."
