#!/usr/bin/env bash
# Fetch Claude Code documentation for plugin validation.
# Downloads all relevant pages, skips if cached and fresh.
#
# Usage:
#   ./scripts/fetch-claude-docs.sh              # Fetch all doc pages
#   ./scripts/fetch-claude-docs.sh --force      # Re-download even if cached
#   ./scripts/fetch-claude-docs.sh --index-only # Just fetch llms.txt index
#   ./scripts/fetch-claude-docs.sh --allow-partial # Best-effort refresh
#
# Output: .claude/docs-check/docs-cache/*.md
# These files are gitignored and used by /docs-check validation.

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
case "$SCRIPT_PATH" in
  */*) SCRIPT_BASE_DIR="${SCRIPT_PATH%/*}" ;;
  *) SCRIPT_BASE_DIR="." ;;
esac
SCRIPT_DIR="$(cd "${SCRIPT_BASE_DIR}" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCS_BASE_URL="https://code.claude.com/docs/en"
INDEX_URL="https://code.claude.com/docs/llms.txt"
CACHE_DIR="${REPO_ROOT}/.claude/docs-check/docs-cache"
MAX_AGE_HOURS=24
FORCE=false
INDEX_ONLY=false
ALLOW_PARTIAL=false
CURL_CONNECT_TIMEOUT=10
CURL_MAX_TIME=60

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $command_name" >&2
    exit 1
  fi
}

emit_curl_failure_details() {
  local err_file="${1:-}"

  [[ -n "$err_file" && -s "$err_file" ]] || return 0
  echo "  [curl] failure details:" >&2
  sed -n '1,5p' "$err_file" >&2 || true
}

# All pages needed for plugin validation
PAGES=(
  "sub-agents.md"               # Agent frontmatter schema
  "skills.md"                   # Skill format and structure
  "hooks.md"                    # Hook events and types
  "hooks-guide.md"              # Hook patterns and examples
  "plugins-reference.md"        # plugin.json schema
  "plugin-marketplaces.md"      # marketplace.json schema
  "plugins.md"                  # General plugin creation
  "plugin-dependencies.md"      # plugin.json dependency version constraints
  "settings.md"                 # Permission modes
  "mcp.md"                      # MCP server config
  "tools-reference.md"          # Tool schema and examples
  "agent-teams.md"              # Agent teams and collaboration features
  "how-claude-code-works.md"    # Overview of Claude Code architecture and concepts
  "third-party-integrations.md" # Supported third-party integrations and how to use them
  "features-overview.md"        # Overview of key features and capabilities of Claude Code for plugin developers
  "memory.md"                   # Memory types and usage guidelines
  "overview.md"                 # High-level overview of Claude Code and its components
  "permission-modes.md"         # Details on different permission modes and their implications for plugin behavior
  "permissions.md"              # Comprehensive guide to permissions, including best practices for requesting and using them in plugins
  "claude-directory.md"         # .claude/ layout authority (CLAUDE.md, settings.json, hooks, skills, commands, subagents, rules, auto memory)
  "commands.md"                 # Slash command reference and bundled skills — name/namespace surface
  "env-vars.md"                 # Environment variables including CLAUDE_PLUGIN_ROOT, CLAUDE_PLUGIN_DATA, CLAUDE_PROJECT_DIR
  "errors.md"                   # Error reference — hook failure classification and StopFailure taxonomy
  "cli-reference.md"            # `claude plugin validate`, `--plugin-dir` contract used by eval/doctor scripts
  "statusline.md"               # Plugin-level subagentStatusLine setting
  "discover-plugins.md"         # Marketplace install flow and git-subdir path resolution
  "sandboxing.md"               # Bash sandboxing semantics impacting hook side-effect guarantees
  "context-window.md"           # PreCompact/PostCompact hook timing and payload context
  "code-review.md"              # Built-in /code-review flow — overlap check with plugin /rb:review
)

# Parse arguments
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=true ;;
    --index-only) INDEX_ONLY=true ;;
    --allow-partial) ALLOW_PARTIAL=true ;;
    --help|-h)
      echo "Usage: $0 [--force] [--index-only] [--allow-partial]"
      echo ""
      echo "  --force       Re-download even if cached within ${MAX_AGE_HOURS}h"
      echo "  --index-only  Only fetch the llms.txt index file"
      echo "  --allow-partial  Keep best-effort behavior on missing docs"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

require_command curl
require_command date
require_command grep
require_command mkdir
require_command mktemp
require_command mv
require_command rm
require_command sed
require_command stat
require_command wc

cd "$REPO_ROOT"
mkdir -p "$CACHE_DIR"

validate_cache_target() {
  local target="$1"
  local parent_dir="${target%/*}"
  local canonical_parent=""

  [[ "$target" == "${CACHE_DIR}/"* ]] || {
    echo "ERROR: cache target outside docs cache: $target" >&2
    return 1
  }

  canonical_parent=$(cd "$parent_dir" >/dev/null 2>&1 && pwd -P) || {
    echo "ERROR: cache target parent is missing or unsafe: $parent_dir" >&2
    return 1
  }

  [[ "$canonical_parent" == "$CACHE_DIR" || "$canonical_parent" == "${CACHE_DIR}/"* ]] || {
    echo "ERROR: cache target parent resolves outside docs cache: $target" >&2
    return 1
  }

  if [[ -e "$target" ]]; then
    [[ -f "$target" ]] || {
      echo "ERROR: cache target exists and is not a regular file: $target" >&2
      return 1
    }
    [[ ! -L "$target" ]] || {
      echo "ERROR: cache target is a symlink (refusing to overwrite): $target" >&2
      return 1
    }
  fi
}

new_cache_temp_file() {
  local target="$1"
  local parent_dir="${target%/*}"
  local base_name="${target##*/}"

  validate_cache_target "$target" || return 1
  mktemp "${parent_dir}/.tmp.${base_name}.XXXXXX"
}

safe_remove_cache_temp_file() {
  local path="${1:-}"
  local parent_dir="${2:-}"

  [[ -n "$path" && -n "$parent_dir" ]] || return 0
  [[ "$path" == "${parent_dir}/.tmp."* ]] || return 1
  [[ -f "$path" && ! -L "$path" ]] || return 1
  rm -f -- "${path:?}"
}

atomic_move_cache_file() {
  local temp_file="$1"
  local target="$2"

  validate_cache_target "$target" || return 1
  mv -f -- "$temp_file" "$target"
}

# Get file modification time (portable: Linux + macOS)
file_mtime() {
  if stat -c %Y "$1" >/dev/null 2>&1; then
    stat -c %Y "$1"     # Linux
  else
    stat -f %m "$1"     # macOS
  fi
}

# Check if a cached file is still fresh
is_fresh() {
  local file="$1"
  [ "$FORCE" = true ] && return 1
  [ ! -f "$file" ] && return 1
  local file_age=$(( $(date +%s) - $(file_mtime "$file") ))
  [ "$file_age" -lt $(( MAX_AGE_HOURS * 3600 )) ]
}

safe_remove_cache_file() {
  local path="${1:-}"
  [[ -n "$path" ]] || return 0
  [[ "$path" == "${CACHE_DIR}/"* ]] || return 1
  [[ ! -e "$path" ]] && return 0
  [[ -f "$path" && ! -L "$path" ]] || return 1
  rm -f -- "${path:?}"
}

# Download a single page with retry
fetch_page() {
  local page="$1"
  local dest="${CACHE_DIR}/${page}"
  local url="${DOCS_BASE_URL}/${page}"
  local err_file=""
  local tmp_file=""

  if is_fresh "$dest"; then
    echo "  [cached] $page (< ${MAX_AGE_HOURS}h old)"
    return 0
  fi

  validate_cache_target "$dest" || return 1
  err_file=$(mktemp "${TMPDIR:-/tmp}/claude-docs-fetch.err.XXXXXX" 2>/dev/null || printf '')
  tmp_file=$(new_cache_temp_file "$dest") || {
    [[ -n "$err_file" ]] && rm -f -- "$err_file"
    return 1
  }

  for attempt in 1 2 3; do
    if curl -sfL --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" "$url" -o "$tmp_file" 2>"${err_file:-/dev/null}"; then
      if ! atomic_move_cache_file "$tmp_file" "$dest"; then
        emit_curl_failure_details "$err_file"
        safe_remove_cache_temp_file "$tmp_file" "${dest%/*}" || true
        [[ -n "$err_file" ]] && rm -f -- "$err_file"
        return 1
      fi
      local size
      size=$(wc -c < "$dest")
      echo "  [fetched] $page (${size} bytes)"
      [[ -n "$err_file" ]] && rm -f -- "$err_file"
      return 0
    fi
    [ "$attempt" -lt 3 ] && sleep $(( attempt * 2 ))
  done

  echo "  [FAILED] $page — could not download after 3 attempts"
  emit_curl_failure_details "$err_file"
  [[ -n "$err_file" ]] && rm -f -- "$err_file"
  safe_remove_cache_temp_file "$tmp_file" "${dest%/*}" || true
  safe_remove_cache_file "$dest" || true
  return 1
}

# Fetch the index
echo "=== Claude Code Documentation Fetcher ==="
echo ""

echo "Fetching index..."
index_failed=0
index_err_file=""
index_tmp_file=""
if is_fresh "${CACHE_DIR}/llms.txt"; then
  echo "  [cached] llms.txt (< ${MAX_AGE_HOURS}h old)"
else
  validate_cache_target "${CACHE_DIR}/llms.txt" || exit 1
  index_err_file=$(mktemp "${TMPDIR:-/tmp}/claude-docs-index.err.XXXXXX" 2>/dev/null || printf '')
  index_tmp_file=$(new_cache_temp_file "${CACHE_DIR}/llms.txt") || {
    [[ -n "$index_err_file" ]] && rm -f -- "$index_err_file"
    exit 1
  }
  if curl -sfL --connect-timeout "$CURL_CONNECT_TIMEOUT" --max-time "$CURL_MAX_TIME" "$INDEX_URL" -o "$index_tmp_file" 2>"${index_err_file:-/dev/null}"; then
    if ! atomic_move_cache_file "$index_tmp_file" "${CACHE_DIR}/llms.txt"; then
      emit_curl_failure_details "$index_err_file"
      [[ -n "$index_err_file" ]] && rm -f -- "$index_err_file"
      safe_remove_cache_temp_file "$index_tmp_file" "$CACHE_DIR" || true
      exit 1
    fi
    page_count=$(grep -c '\.md' "${CACHE_DIR}/llms.txt" 2>/dev/null || true)
    [[ -n "$page_count" ]] || page_count="?"
    echo "  [fetched] llms.txt (${page_count} pages indexed)"
    [[ -n "$index_err_file" ]] && rm -f -- "$index_err_file"
  else
    echo "  [FAILED] Could not fetch llms.txt"
    echo "  [WARNING] Required-page coverage cannot be fully verified without the index." >&2
    emit_curl_failure_details "$index_err_file"
    [[ -n "$index_err_file" ]] && rm -f -- "$index_err_file"
    safe_remove_cache_temp_file "$index_tmp_file" "$CACHE_DIR" || true
    safe_remove_cache_file "${CACHE_DIR}/llms.txt" || true
    index_failed=1
  fi
fi

if [ "$INDEX_ONLY" = true ]; then
  echo ""
  echo "Done (index only)."
  if [ "$ALLOW_PARTIAL" != true ] && [ "$index_failed" -ne 0 ]; then
    exit 1
  fi
  exit 0
fi

# Fetch all pages
echo ""
echo "Fetching doc pages..."
failed=0
for page in "${PAGES[@]}"; do
  fetch_page "$page" || (( failed++ )) || true
done

# Summary
echo ""
echo "=== Summary ==="
total_files=$(find "$CACHE_DIR" -name "*.md" | wc -l)
total_size=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
required_present=0
for page in "${PAGES[@]}"; do
  if [ -f "${CACHE_DIR}/${page}" ]; then
    required_present=$(( required_present + 1 ))
  fi
done
extra_cached=$(( total_files - required_present ))
echo "  Cache: $CACHE_DIR"
echo "  Expected doc pages cached: ${required_present}/${#PAGES[@]}"
echo "  Extra cached markdown files: ${extra_cached}"
echo "  Size:  $total_size"
if [ "$index_failed" -gt 0 ]; then
  echo "  Index: failed"
fi
if [ "$failed" -gt 0 ]; then
  echo "  Failures: $failed (missing from cache — re-run or use --force)"
fi

# Show freshness of each cached file
echo ""
echo "=== Cache Status ==="
for page in "${PAGES[@]}"; do
  dest="${CACHE_DIR}/${page}"
  if [ ! -f "$dest" ]; then
    echo "  ❌ $page — missing (download failed)"
  else
    age_secs=$(( $(date +%s) - $(file_mtime "$dest") ))
    if [ "$age_secs" -lt 3600 ]; then
      echo "  ✅ $page — $(( age_secs / 60 ))m ago"
    elif [ "$age_secs" -lt 86400 ]; then
      echo "  ✅ $page — $(( age_secs / 3600 ))h ago"
    else
      echo "  ⚠️  $page — $(( age_secs / 86400 ))d ago (stale)"
    fi
  fi
done

if [ "$ALLOW_PARTIAL" != true ] && { [ "$index_failed" -gt 0 ] || [ "$failed" -gt 0 ] || [ "$required_present" -lt "${#PAGES[@]}" ]; }; then
  echo ""
  echo "ERROR: Claude docs cache refresh incomplete." >&2
  echo "Re-run the fetch or use --allow-partial only for best-effort local checks." >&2
  exit 1
fi
