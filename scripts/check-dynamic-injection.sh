#!/usr/bin/env bash
# Blocks dynamic context injection syntax (!`command`) in tracked markdown, JSON,
# and YAML surfaces. Default mode scans tracked files from `git ls-files`.
# `--manifest` provides a deterministic fallback manifest for changed-only or
# non-git environments without broad filesystem scans.
# This feature executes shell commands at skill load time. The Ruby plugin does
# not use it and treats it as unsafe in these surfaces.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT_REAL="$(cd "${REPO_ROOT}" && pwd -P)"
TRACKED_PATTERNS=('*.md' '*.json' '*.yml' '*.yaml')
FOUND=0
MANIFEST_FILE=""
MANIFEST_SKIPPED=0

show_usage() {
  cat <<'EOF'
Usage: bash scripts/check-dynamic-injection.sh [--manifest PATH]

Default behavior scans tracked Markdown/JSON/YAML files from `git ls-files`.
Use `--manifest PATH` with a newline-delimited file list to run the same
Markdown/JSON/YAML scan set without Git metadata or on a narrowed changed-file
set.
EOF
}

require_command() {
  local command_name="$1"
  local reason="${2:-dynamic-injection scanning}"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for ${reason}." >&2
    exit 1
  fi
}

canonicalize_existing_file() {
  local path="$1"
  local parent_dir=""
  local canonical_parent=""

  [[ -f "$path" && ! -L "$path" ]] || return 1
  parent_dir="$(dirname "$path")"
  canonical_parent="$(cd "$parent_dir" >/dev/null 2>&1 && pwd -P)" || return 1
  printf '%s/%s\n' "$canonical_parent" "$(basename "$path")"
}

resolve_manifest_path() {
  local candidate="$1"
  local resolved=""

  [[ -n "$candidate" ]] || return 1
  if [[ "$candidate" != /* ]]; then
    candidate="${REPO_ROOT}/${candidate}"
  fi

  resolved="$(canonicalize_existing_file "$candidate")" || return 1
  [[ "$resolved" == "${REPO_ROOT_REAL}/"* ]] || return 1
  printf '%s\n' "$resolved"
}

scan_file() {
  local file="$1"
  local matches

  matches=$(
    awk '
      BEGIN {
        in_fence = 0
        fence_marker = ""
      }

      {
        line = $0
        trimmed = line
        sub(/^[[:space:]]+/, "", trimmed)

        if (!in_fence && (trimmed ~ /^```/ || trimmed ~ /^~~~/)) {
          fence_marker = substr(trimmed, 1, 3)
          in_fence = 1
          next
        }

        if (in_fence) {
          if ((fence_marker == "```" && trimmed ~ /^```/) || (fence_marker == "~~~" && trimmed ~ /^~~~/)) {
            in_fence = 0
            fence_marker = ""
          }
          next
        }

        in_inline_code = 0
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

scan_manifest() {
  local listed_path=""
  local resolved_path=""

  [[ -n "$MANIFEST_FILE" ]] || return 1
  [[ -f "$MANIFEST_FILE" && ! -L "$MANIFEST_FILE" ]] || {
    echo "ERROR: manifest file is missing or unsafe: ${MANIFEST_FILE}" >&2
    exit 1
  }

  while IFS= read -r listed_path; do
    [[ -n "$listed_path" ]] || continue
    resolved_path="$(resolve_manifest_path "$listed_path")" || {
      echo "ERROR: manifest entry could not be resolved inside the repository: ${listed_path}" >&2
      MANIFEST_SKIPPED=$((MANIFEST_SKIPPED + 1))
      continue
    }
    case "$resolved_path" in
      *.md|*.json|*.yml|*.yaml) ;;
      *)
        echo "ERROR: manifest entry is outside the supported markdown/json/yaml scan set: ${listed_path}" >&2
        MANIFEST_SKIPPED=$((MANIFEST_SKIPPED + 1))
        continue
        ;;
    esac
    scan_file "$resolved_path"
  done < "$MANIFEST_FILE"

  if [[ "$MANIFEST_SKIPPED" -gt 0 ]]; then
    echo "ERROR: dynamic-injection manifest skipped ${MANIFEST_SKIPPED} invalid or unsupported entry(s)." >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      shift
      [[ $# -gt 0 ]] || {
        echo "ERROR: --manifest requires a file path." >&2
        exit 1
      }
      MANIFEST_FILE="$1"
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      show_usage >&2
      exit 1
      ;;
  esac
  shift
done

require_command awk "dynamic-injection scanning"

if [[ -n "$MANIFEST_FILE" ]]; then
  scan_manifest
else
  require_command git "tracked dynamic-injection scanning"
  if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    while IFS= read -r -d '' file; do
      [[ -f "${REPO_ROOT}/${file}" ]] || continue
      scan_file "${REPO_ROOT}/${file}"
    done < <(git -C "$REPO_ROOT" ls-files -z -- "${TRACKED_PATTERNS[@]}")
  else
    echo "ERROR: tracked dynamic-injection scan requires git metadata or an explicit --manifest <file>." >&2
    echo "ERROR: rerun from a repository checkout with Git metadata, or pass a newline-delimited manifest for a comparable file set." >&2
    exit 1
  fi
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
