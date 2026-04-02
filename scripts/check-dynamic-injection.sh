#!/usr/bin/env bash
# Blocks dynamic context injection syntax (!`command`) in tracked markdown, JSON,
# and YAML surfaces. The tracked manifest always comes from `git ls-files`; this
# script no longer broad-scans the filesystem because that produces
# non-comparable results and can block on unrelated untracked content.
# This feature executes shell commands at skill load time. The Ruby plugin does
# not use it and treats it as unsafe in these surfaces.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TRACKED_PATTERNS=('*.md' '*.json' '*.yml' '*.yaml')
FOUND=0

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for tracked dynamic-injection scanning." >&2
    exit 1
  fi
}

scan_file() {
  local file="$1"
  local matches

  matches=$(
    awk '
      {
        in_inline_code = 0
        line = $0
        line_length = length(line)

        for (i = 1; i <= line_length; i++) {
          char = substr(line, i, 1)
          if (char == "`") {
            in_inline_code = !in_inline_code
            continue
          }

          if (!in_inline_code && char == "!" && i < line_length && substr(line, i + 1, 1) == "`") {
            printf "%d:%s\n", NR, line
            next
          }
        }
      }
    ' "$file" 2>/dev/null || true
  )

  if [[ -n "$matches" ]]; then
    echo "BLOCKED: Dynamic context injection found:"
    echo "$matches"
    echo
    FOUND=1
  fi
}

require_command git
require_command awk

if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  while IFS= read -r -d '' file; do
    [[ -f "${REPO_ROOT}/${file}" ]] || continue
    scan_file "${REPO_ROOT}/${file}"
  done < <(git -C "$REPO_ROOT" ls-files -z -- "${TRACKED_PATTERNS[@]}")
else
  echo "ERROR: tracked dynamic-injection scan requires git when .git metadata is present." >&2
  echo "ERROR: install git and rerun from a repository checkout with comparable tracked-file metadata." >&2
  exit 1
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
