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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCS_BASE_URL="https://code.claude.com/docs/en"
INDEX_URL="https://code.claude.com/docs/llms.txt"
CACHE_DIR="${REPO_ROOT}/.claude/docs-check/docs-cache"
MAX_AGE_HOURS=24
FORCE=false
INDEX_ONLY=false
ALLOW_PARTIAL=false

# All pages needed for plugin validation (~420KB total)
PAGES=(
  "sub-agents.md"          # Agent frontmatter schema
  "skills.md"              # Skill format and structure
  "hooks.md"               # Hook events and types
  "hooks-guide.md"         # Hook patterns and examples
  "plugins-reference.md"   # plugin.json schema
  "plugin-marketplaces.md" # marketplace.json schema
  "plugins.md"             # General plugin creation
  "settings.md"            # Permission modes
  "mcp.md"                 # MCP server config
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
      echo "Unknown argument: $arg"
      exit 1
      ;;
  esac
done

cd "$REPO_ROOT"
mkdir -p "$CACHE_DIR"

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

  if is_fresh "$dest"; then
    echo "  [cached] $page (< ${MAX_AGE_HOURS}h old)"
    return 0
  fi

  for attempt in 1 2 3; do
    if curl -sfL "$url" -o "$dest" 2>/dev/null; then
      local size
      size=$(wc -c < "$dest")
      echo "  [fetched] $page (${size} bytes)"
      return 0
    fi
    [ "$attempt" -lt 3 ] && sleep $(( attempt * 2 ))
  done

  echo "  [FAILED] $page — could not download after 3 attempts"
  safe_remove_cache_file "$dest" || true
  return 1
}

# Fetch the index
echo "=== Claude Code Documentation Fetcher ==="
echo ""

echo "Fetching index..."
index_failed=0
if is_fresh "${CACHE_DIR}/llms.txt"; then
  echo "  [cached] llms.txt (< ${MAX_AGE_HOURS}h old)"
else
  if curl -sfL "$INDEX_URL" -o "${CACHE_DIR}/llms.txt" 2>/dev/null; then
    page_count=$(grep -c '\.md' "${CACHE_DIR}/llms.txt" 2>/dev/null || echo "?")
    echo "  [fetched] llms.txt (${page_count} pages indexed)"
  else
    echo "  [FAILED] Could not fetch llms.txt"
    echo "  [WARNING] Required-page coverage cannot be fully verified without the index." >&2
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
