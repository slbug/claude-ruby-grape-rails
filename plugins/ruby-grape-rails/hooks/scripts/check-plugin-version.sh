#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: warn when the project memory file pins a different plugin
# version than the installed plugin. Outdated pin emits a refresh reminder;
# newer pin flags a possible plugin downgrade.
# Policy: advisory — silent on missing memory file, missing plugin marker,
# missing plugin.json, tool unavailability, or lock conflicts. Degraded
# payload/root resolution must not block session startup. Fires at most once
# per session via atomic per-session lock directory under CLAUDE_PLUGIN_DATA
# (or the workspace `.claude/.hook-state/` fallback).
command -v jq >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0
command -v sed >/dev/null 2>&1 || exit 0
command -v tr >/dev/null 2>&1 || exit 0
command -v head >/dev/null 2>&1 || exit 0
command -v tail >/dev/null 2>&1 || exit 0
# sort -V (natural version sort) is required. Commonly available via GNU
# coreutils; on macOS the brew `coreutils` package ships it as `gsort`
# rather than replacing `sort`. Prefer bare `sort -V`; fall back to
# `gsort -V`; exit silently if neither supports it.
SORT_BIN=""
if command -v sort >/dev/null 2>&1 && printf 'a\n' | sort -V >/dev/null 2>&1; then
  SORT_BIN="sort"
elif command -v gsort >/dev/null 2>&1 && printf 'a\n' | gsort -V >/dev/null 2>&1; then
  SORT_BIN="gsort"
else
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

read_hook_input
# Do NOT gate on empty INPUT — resolve_workspace_root falls back to
# CLAUDE_PROJECT_DIR and then PWD per workspace-root-lib.sh, so the drift
# warning still works when SessionStart payload is missing/truncated/invalid
# (e.g. some resume paths). session_id extraction below defaults to
# "default" via jq's `||` fallback in degraded-input cases.
INPUT="${HOOK_INPUT_VALUE:-}"

REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0

# Strict-validate every extracted pin against the official semver regex from
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
# translated to POSIX ERE:
#   - MAJOR/MINOR/PATCH: `0` or a positive integer with no leading zeros
#   - pre-release (optional): `-` + dot-separated identifiers. Numeric
#     identifiers have no leading zeros; alphanumeric identifiers must
#     contain at least one non-digit.
#   - build metadata (optional): `+` + dot-separated [0-9A-Za-z-] groups.
# NB: `grep -oE` alone would extract the longest PREFIX match, silently
# truncating non-semver input like `1.2.3rc1` down to `1.2.3`. We instead
# extract the greedy version token (chars until first non-semver-ish char)
# and anchor-validate with the strict regex so non-semver stays silent.
SEMVER_CORE='(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
SEMVER_PRE='(-((0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
SEMVER_BUILD='(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?'
ANCHORED_SEMVER="^${SEMVER_CORE}${SEMVER_PRE}${SEMVER_BUILD}$"

# A memory file is usable only as a readable regular non-symlink file — the
# same validity contract /rb:init applies before writing.
usable_memory_file() {
  local file="$1"
  [[ -f "$file" && ! -L "$file" && -r "$file" ]]
}

# Print the managed block, or fail. `sed` prints from START to EOF when the
# range never closes, which covers both a missing END and an END that precedes
# START, so require an END sentinel inside the emitted range — otherwise
# trailing prose outside any block could supply a version token.
managed_block() {
  local file="$1" block
  usable_memory_file "$file" || return 1
  block=$(sed -n '/<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->/,/<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->/p' "$file" 2>/dev/null) || return 1
  [[ -n "$block" ]] || return 1
  printf '%s\n' "$block" | grep -q '<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->' || return 1
  printf '%s\n' "$block"
}

# Print the block's strict-semver pin, or fail. Require a word-boundary before
# `plugin v` so foreign markers like `some-plugin v1.0.0` or `iplugin v2`
# inside the managed block do not hijack the match (POSIX ERE has no portable
# `\b`; we approximate via `(^|[^A-Za-z0-9_-])`).
pinned_version() {
  local file="$1" block raw
  block=$(managed_block "$file") || return 1
  raw=$(printf '%s\n' "$block" \
    | grep -oE '(^|[^A-Za-z0-9_-])plugin v[0-9A-Za-z.+-]+' \
    | head -1 \
    | sed -E 's/.*plugin v//' || true)
  [[ -n "$raw" ]] || return 1
  printf '%s' "$raw" | grep -qE "$ANCHORED_SEMVER" || return 1
  printf '%s' "$raw"
}

LOCAL_MD="${REPO_ROOT}/CLAUDE.local.md"
ROOT_MD="${REPO_ROOT}/CLAUDE.md"

# A block in `CLAUDE.md` while the project has a usable `CLAUDE.local.md` is a
# pre-`CLAUDE.local.md` install that /rb:init --update migrates. Detect the
# `CLAUDE.md` block independently of which file supplies the pin: when both
# files carry one, the pin comes from `CLAUDE.local.md` and the `CLAUDE.md`
# copy is a leftover duplicate that still loads into context. Surface either
# shape even when the pinned version matches, and only when `--update` could
# actually perform the move.
MIGRATION_PENDING=false
if usable_memory_file "$LOCAL_MD" && managed_block "$ROOT_MD" >/dev/null; then
  MIGRATION_PENDING=true
fi

# /rb:init writes its managed block into `CLAUDE.local.md` when the project
# has one and falls back to `CLAUDE.md`. Take the pin from the first candidate
# that yields a valid one, `CLAUDE.local.md` first, so a stale block left in
# `CLAUDE.md` does not shadow the file /rb:init --update maintains — and a
# malformed or unpinned local block does not shadow a `CLAUDE.md` block that
# still reports real drift.
MEMORY_FILE=""
PINNED=""
for CANDIDATE in "$LOCAL_MD" "$ROOT_MD"; do
  CANDIDATE_PIN=$(pinned_version "$CANDIDATE") || continue
  MEMORY_FILE="$CANDIDATE"
  PINNED="$CANDIDATE_PIN"
  break
done

# No readable pin anywhere: still report a pending migration, which needs no
# version comparison. Same for a plugin.json we cannot read.
if [[ -z "$PINNED" ]]; then
  [[ "$MIGRATION_PENDING" == "true" ]] || exit 0
  DIRECTION="migrate"
fi
MEMORY_NAME="${MEMORY_FILE##*/}"

if [[ -z "${DIRECTION:-}" ]]; then
  CURRENT=""
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
    PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
    if [[ -f "$PLUGIN_JSON" && ! -L "$PLUGIN_JSON" && -r "$PLUGIN_JSON" ]]; then
      CURRENT=$(jq -r '.version // empty' "$PLUGIN_JSON" 2>/dev/null) || CURRENT=""
    fi
  fi
  if [[ -z "$CURRENT" ]]; then
    [[ "$MIGRATION_PENDING" == "true" ]] || exit 0
    DIRECTION="migrate"
  fi
fi

# Semver build metadata (`+...`) MUST NOT affect equality or precedence per
# https://semver.org/#spec-item-10. Strip it before comparison, keep the
# original strings for the user-facing message.
if [[ -z "${DIRECTION:-}" ]]; then
  PINNED_COMPARE="${PINNED%%+*}"
  CURRENT_COMPARE="${CURRENT%%+*}"
  [[ -n "$PINNED_COMPARE" && -n "$CURRENT_COMPARE" ]] || exit 0

  # Semver-aware compare via `sort -V` (natural version sort). Handles semver
  # pre-release precedence correctly: `1.13.1-rc1` sorts below `1.13.1`.
  if [[ "$PINNED_COMPARE" == "$CURRENT_COMPARE" ]]; then
    [[ "$MIGRATION_PENDING" == "true" ]] || exit 0
    DIRECTION="migrate"
  else
    HIGHEST=$(printf '%s\n%s\n' "$PINNED_COMPARE" "$CURRENT_COMPARE" | "$SORT_BIN" -V | tail -n 1)
    [[ -n "$HIGHEST" ]] || exit 0
    if [[ "$HIGHEST" == "$CURRENT_COMPARE" ]]; then
      DIRECTION="outdated"
    else
      DIRECTION="newer"
    fi
  fi
fi

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // .sessionId // "default"' 2>/dev/null) || SESSION_ID=""
# jq on empty stdin returns empty+exit-0 (so `||` doesn't fire). Coerce any
# empty/null result to the `default` key — degraded-input sessions share
# one lock, trading session-isolation for resilient delivery.
[[ -z "$SESSION_ID" || "$SESSION_ID" == "null" ]] && SESSION_ID="default"
SESSION_KEY=$(printf '%s' "$SESSION_ID" | tr -c '[:alnum:]_-' '_')
[[ -n "$SESSION_KEY" ]] || exit 0

LOCK_BASE="${CLAUDE_PLUGIN_DATA:-}"
if [[ -z "$LOCK_BASE" ]]; then
  CLAUDE_DIR="${REPO_ROOT}/.claude"
  [[ ! -L "$CLAUDE_DIR" ]] || exit 0
  mkdir -p -- "$CLAUDE_DIR" 2>/dev/null || exit 0
  [[ -d "$CLAUDE_DIR" && ! -L "$CLAUDE_DIR" ]] || exit 0
  HOOK_STATE_DIR="${CLAUDE_DIR}/.hook-state"
  [[ ! -L "$HOOK_STATE_DIR" ]] || exit 0
  mkdir -p -- "$HOOK_STATE_DIR" 2>/dev/null || exit 0
  [[ -d "$HOOK_STATE_DIR" && ! -L "$HOOK_STATE_DIR" ]] || exit 0
  LOCK_BASE="$HOOK_STATE_DIR"
fi
[[ ! -L "$LOCK_BASE" ]] || exit 0
LOCK_DIR="${LOCK_BASE}/version-check"
[[ ! -L "$LOCK_DIR" ]] || exit 0
mkdir -p -- "$LOCK_DIR" 2>/dev/null || exit 0
[[ -d "$LOCK_DIR" && ! -L "$LOCK_DIR" ]] || exit 0

SESSION_LOCK="${LOCK_DIR}/${SESSION_KEY}"
[[ ! -L "$SESSION_LOCK" ]] || exit 0
# mkdir is atomic: exits non-zero if the lock already exists.
mkdir -- "$SESSION_LOCK" 2>/dev/null || exit 0

# SessionStart stdout is added to Claude's context (hooks.md §SessionStart).
# Phrase the message as an imperative instruction so Claude surfaces the
# drift to the user at the start of the next response instead of silently
# reading the fact.
MIGRATION_LINE=""
if [[ "$MIGRATION_PENDING" == "true" ]]; then
  MIGRATION_LINE="A managed block also remains in CLAUDE.md while this project has a
CLAUDE.local.md; /rb:init --update moves it there and removes the CLAUDE.md copy."
fi

case "$DIRECTION" in
outdated)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
Installed plugin v${CURRENT} is ahead of project ${MEMORY_NAME} pinned at v${PINNED}.
${MIGRATION_LINE}
Tell the user at the start of your next response, then recommend:
/rb:init --update
NOTICE
  ;;
newer)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
Installed plugin v${CURRENT} is OLDER than project ${MEMORY_NAME} pinned at v${PINNED}.
The plugin may have been downgraded. Tell the user at the start of your next
response; recommend verifying the install before running /rb:init --update
(it would overwrite the newer marker content with the older template).
NOTICE
  ;;
migrate)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
A managed block remains in CLAUDE.md while this project has a CLAUDE.local.md,
which the plugin prefers for its stack notes. Both files load into context, so
a second copy wastes context and drifts into conflicting stack notes once one
copy is refreshed. Tell the user at the start of your next response, then
recommend:
/rb:init --update
NOTICE
  ;;
esac
