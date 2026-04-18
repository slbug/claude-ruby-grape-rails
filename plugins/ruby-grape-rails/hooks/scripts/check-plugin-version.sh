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
INPUT="$HOOK_INPUT_VALUE"
[[ -n "$INPUT" ]] || exit 0

REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0

CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"
[[ -f "$CLAUDE_MD" && ! -L "$CLAUDE_MD" && -r "$CLAUDE_MD" ]] || exit 0

# Extract pinned version between plugin sentinels. Accept semver + optional
# pre-release/build suffix (`plugin v1.2.3-rc1`, `plugin v1.2.3+build.5`).
PINNED=$(sed -n '/<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->/,/<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->/p' "$CLAUDE_MD" 2>/dev/null \
  | grep -oE 'plugin v[0-9]+\.[0-9]+\.[0-9]+[A-Za-z0-9.+-]*' \
  | head -1 \
  | sed 's/^plugin v//' || true)
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

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // .sessionId // "default"' 2>/dev/null) || SESSION_ID="default"
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

# SessionStart stdout IS added to Claude's context.
case "$DIRECTION" in
outdated)
  echo "⚠ Ruby/Rails/Grape plugin v${CURRENT} active; project CLAUDE.md pinned to v${PINNED}. Run /rb:init --update to refresh."
  ;;
newer)
  echo "⚠ Project CLAUDE.md pinned to Ruby/Rails/Grape plugin v${PINNED}, but installed plugin is v${CURRENT}. Plugin may have been downgraded — verify before running /rb:init --update (it would overwrite newer marker content)."
  ;;
esac
