#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: warn when project CLAUDE.md pins a different plugin
# version than the installed plugin. Outdated pin emits a refresh reminder;
# newer pin flags a possible plugin downgrade.
# Policy: advisory — silent on missing CLAUDE.md, missing plugin marker,
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

CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"
[[ -f "$CLAUDE_MD" && ! -L "$CLAUDE_MD" && -r "$CLAUDE_MD" ]] || exit 0

# Extract pinned version between plugin sentinels and strict-validate against
# the official semver regex from
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

# Require a word-boundary before `plugin v` so foreign markers like
# `some-plugin v1.0.0` or `iplugin v2` inside the managed block do not
# hijack the match (POSIX ERE has no portable `\b`; we approximate via
# `(^|[^A-Za-z0-9_-])`).
RAW=$(sed -n '/<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->/,/<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->/p' "$CLAUDE_MD" 2>/dev/null \
  | grep -oE '(^|[^A-Za-z0-9_-])plugin v[0-9A-Za-z.+-]+' \
  | head -1 \
  | sed -E 's/.*plugin v//' || true)
[[ -n "$RAW" ]] || exit 0
printf '%s' "$RAW" | grep -qE "$ANCHORED_SEMVER" || exit 0
PINNED="$RAW"
[[ -n "$PINNED" ]] || exit 0

[[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]] || exit 0
PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
[[ -f "$PLUGIN_JSON" && ! -L "$PLUGIN_JSON" && -r "$PLUGIN_JSON" ]] || exit 0

CURRENT=$(jq -r '.version // empty' "$PLUGIN_JSON" 2>/dev/null) || exit 0
[[ -n "$CURRENT" ]] || exit 0

# Semver build metadata (`+...`) MUST NOT affect equality or precedence per
# https://semver.org/#spec-item-10. Strip it before comparison, keep the
# original strings for the user-facing message.
PINNED_COMPARE="${PINNED%%+*}"
CURRENT_COMPARE="${CURRENT%%+*}"
[[ -n "$PINNED_COMPARE" && -n "$CURRENT_COMPARE" ]] || exit 0

# Semver-aware compare via `sort -V` (natural version sort). Handles semver
# pre-release precedence correctly: `1.13.1-rc1` sorts below `1.13.1`.
[[ "$PINNED_COMPARE" == "$CURRENT_COMPARE" ]] && exit 0
HIGHEST=$(printf '%s\n%s\n' "$PINNED_COMPARE" "$CURRENT_COMPARE" | "$SORT_BIN" -V | tail -n 1)
[[ -n "$HIGHEST" ]] || exit 0

if [[ "$HIGHEST" == "$CURRENT_COMPARE" ]]; then
  DIRECTION="outdated"
else
  DIRECTION="newer"
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
case "$DIRECTION" in
outdated)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
Installed plugin v${CURRENT} is ahead of project CLAUDE.md pinned at v${PINNED}.
Tell the user at the start of your next response, then recommend:
/rb:init --update
NOTICE
  ;;
newer)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
Installed plugin v${CURRENT} is OLDER than project CLAUDE.md pinned at v${PINNED}.
The plugin may have been downgraded. Tell the user at the start of your next
response; recommend verifying the install before running /rb:init --update
(it would overwrite the newer marker content with the older template).
NOTICE
  ;;
esac
