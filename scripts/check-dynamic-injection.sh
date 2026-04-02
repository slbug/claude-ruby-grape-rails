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

manifest_entry_must_be_tracked() {
  local resolved_path="$1"
  local relative_path=""

  command -v git >/dev/null 2>&1 || return 0
  git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 || return 0

  relative_path="${resolved_path#"${REPO_ROOT_REAL}"/}"
  git -C "$REPO_ROOT" ls-files --error-unmatch -- "$relative_path" >/dev/null 2>&1
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
  local matches=""

  case "$file" in
    *.md)
      matches="$(scan_markdown_file "$file" 2>/dev/null || true)"
      ;;
    *.json|*.yml|*.yaml)
      matches="$(scan_data_file "$file" 2>/dev/null || true)"
      ;;
  esac

  if [[ -n "$matches" ]]; then
    echo "BLOCKED: Dynamic context injection found:"
    echo "$matches"
    echo
    FOUND=1
  fi
}

scan_markdown_file() {
  local file="$1"

  python3 - "$file" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

in_fence = False
fence_char = ""
fence_len = 0

for line_no, line in enumerate(text.splitlines(), start=1):
    stripped = line.lstrip()
    fence_match = re.match(r"^([`~]{3,})", stripped)

    if not in_fence and fence_match:
        fence = fence_match.group(1)
        in_fence = True
        fence_char = fence[0]
        fence_len = len(fence)
        continue

    if in_fence:
        close_match = re.match(rf"^({re.escape(fence_char)}{{{fence_len},}})", stripped)
        if close_match:
            in_fence = False
            fence_char = ""
            fence_len = 0
        continue

    spans = []
    open_start = None
    open_len = 0
    i = 0
    while i < len(line):
        if line[i] != "`":
            i += 1
            continue
        j = i
        while j < len(line) and line[j] == "`":
            j += 1
        run_len = j - i
        if open_start is None:
            open_start = i
            open_len = run_len
        elif run_len == open_len:
            spans.append((open_start, j))
            open_start = None
            open_len = 0
        i = j

    def in_safe_span(index):
        return any(start <= index < end for start, end in spans)

    for idx in range(len(line) - 1):
        if line[idx] == "!" and line[idx + 1] == "`":
            if open_start is not None or not in_safe_span(idx):
                print(f"{line_no}:{line}")
                break
PY
}

scan_data_file() {
  local file="$1"

  python3 - "$file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
    if "!`" in line:
        print(f"{line_no}:{line}")
PY
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
    if ! manifest_entry_must_be_tracked "$resolved_path"; then
      echo "ERROR: manifest entry is not tracked by git and cannot be used for a comparable scan: ${listed_path}" >&2
      MANIFEST_SKIPPED=$((MANIFEST_SKIPPED + 1))
      continue
    fi
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

require_command python3 "dynamic-injection scanning"

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
