#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: warn when the project memory file pins a different plugin
# version than the installed plugin, or when its managed block sits in a file
# /rb:init no longer targets. Outdated pin emits a refresh reminder; newer pin
# flags a possible plugin downgrade; a movable `CLAUDE.md` block emits a
# migration reminder even with no readable pin and no readable plugin.json.
# Policy: advisory — silent on missing memory file, missing plugin marker,
# tool unavailability, or lock conflicts. A missing plugin.json, an
# unreadable pin, and a missing `sort -V` on matching versions are silent too,
# EXCEPT when a migration is pending or a managed block sits in a file
# `/rb:init --update` cannot rewrite: those two need no version comparison and
# still report. Degraded payload/root resolution must not block session
# startup. Fires at most once per session via atomic per-session lock
# directory under CLAUDE_PLUGIN_DATA (or the workspace `.claude/.hook-state/`
# fallback).
command -v jq >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0
command -v sed >/dev/null 2>&1 || exit 0
command -v tr >/dev/null 2>&1 || exit 0
command -v head >/dev/null 2>&1 || exit 0
command -v tail >/dev/null 2>&1 || exit 0
# `sort -V` (natural version sort) is needed ONLY to order two differing
# versions. BSD `sort` on a stock macOS lacks it, and the brew `coreutils`
# package ships GNU sort as `gsort` rather than replacing `sort` — so resolve
# it lazily, at the comparison itself. Resolving it up front would suppress
# the migration and repair notices, which need no comparison, on every machine
# without GNU coreutils.
resolve_sort_bin() {
  if command -v sort >/dev/null 2>&1 && printf 'a\n' | sort -V >/dev/null 2>&1; then
    printf 'sort'
  elif command -v gsort >/dev/null 2>&1 && printf 'a\n' | gsort -V >/dev/null 2>&1; then
    printf 'gsort'
  else
    return 1
  fi
}

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

# A memory file is readable only as a regular non-symlink file. /rb:init also
# requires write access before it targets one, so keep the two predicates
# separate: the pin can still be read from a file `--update` cannot rewrite.
readable_memory_file() {
  local file="$1"
  [[ -f "$file" && ! -L "$file" && -r "$file" ]]
}

usable_memory_file() {
  local file="$1"
  readable_memory_file "$file" && [[ -w "$file" ]]
}

# Print the managed block, or fail. `sed` prints from START to EOF when the
# range never closes, which covers both a missing END and an END that precedes
# START, so require an END sentinel inside the emitted range — otherwise
# trailing prose outside any block could supply a version token.
managed_block() {
  local file="$1" block
  readable_memory_file "$file" || return 1
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

# Which files actually carry a block, independently of which one supplies the
# pin below. Both answers drive the notice wording.
LOCAL_HAS_BLOCK=false
managed_block "$LOCAL_MD" >/dev/null 2>&1 && LOCAL_HAS_BLOCK=true
ROOT_HAS_BLOCK=false
managed_block "$ROOT_MD" >/dev/null 2>&1 && ROOT_HAS_BLOCK=true

# `CLAUDE.local.md` is a migration target only in personal scope, which means
# one of two CONFIRMED answers: git ignores the file, or the project is not a
# git repository at all. Anything else — a repository git cannot inspect, or a
# `check-ignore` that errors — is unknown, and unknown fails closed:
# recommending a move into a possibly tracked file is worse than staying
# quiet. Repo detection comes from workspace-root-lib.sh.
local_file_is_personal_scope() {
  if git_can_inspect_repo "$REPO_ROOT"; then
    # Exit 0 = ignored. Exit 1 = tracked. Anything else = inspection failure.
    git -C "$REPO_ROOT" check-ignore -q -- "$LOCAL_MD" 2>/dev/null
    return $(($? == 0 ? 0 : 1))
  fi
  git_metadata_present "$REPO_ROOT" && return 1
  return 0
}

# A block in `CLAUDE.md` while the project has a usable `CLAUDE.local.md` is a
# pre-`CLAUDE.local.md` install that /rb:init --update migrates. Surface it
# even when the pinned version matches — but only when `--update` can actually
# perform the move, which needs write access to the destination AND to the
# source it strips the block from. Recommending a move neither file permits
# would repeat every session with nothing the user can do about it.
MIGRATION_PENDING=false
if usable_memory_file "$LOCAL_MD" && usable_memory_file "$ROOT_MD" \
  && [[ "$ROOT_HAS_BLOCK" == "true" ]] && local_file_is_personal_scope; then
  MIGRATION_PENDING=true
fi

# `--update` rewrites whichever file holds the block, so a block `/rb:init`
# refuses to touch stops the run. Name the first such file and why, matching
# the skill's Target File contract: `CLAUDE.local.md` must be writable AND in
# personal scope; `CLAUDE.md` must be writable. Both checks are pin
# independent, so a block with no valid pin is still reported.
BLOCKED_NAME=""
BLOCKED_REASON=""
if [[ "$LOCAL_HAS_BLOCK" == "true" ]]; then
  if ! usable_memory_file "$LOCAL_MD"; then
    BLOCKED_NAME="CLAUDE.local.md"
    BLOCKED_REASON="is not writable"
  elif ! local_file_is_personal_scope; then
    BLOCKED_NAME="CLAUDE.local.md"
    BLOCKED_REASON="is not confirmed to be ignored by git"
  fi
fi
if [[ -z "$BLOCKED_NAME" && "$ROOT_HAS_BLOCK" == "true" ]] \
  && ! usable_memory_file "$ROOT_MD"; then
  BLOCKED_NAME="CLAUDE.md"
  BLOCKED_REASON="is not writable"
fi

# /rb:init writes its managed block into `CLAUDE.local.md` when the project
# has one and falls back to `CLAUDE.md`. Read BOTH pins: the preferred one
# drives the drift report, and the other still has to be checked for a newer
# version, or recommending a migration would silently delete a block newer
# than the installed plugin.
LOCAL_PIN=$(pinned_version "$LOCAL_MD") || LOCAL_PIN=""
ROOT_PIN=$(pinned_version "$ROOT_MD") || ROOT_PIN=""
MEMORY_FILE=""
PINNED=""
if [[ -n "$LOCAL_PIN" ]]; then
  MEMORY_FILE="$LOCAL_MD"
  PINNED="$LOCAL_PIN"
elif [[ -n "$ROOT_PIN" ]]; then
  MEMORY_FILE="$ROOT_MD"
  PINNED="$ROOT_PIN"
fi

# Whatever blocks the version comparison — no pin, no plugin.json, no version
# sort — a pending migration or an unwritable block is still worth reporting
# on its own. Print that direction, or fail when there is nothing to say.
# DIRECTION is initialized here so an exported variable of the same name from
# the environment cannot skip the comparison below.
DIRECTION=""
fallback_direction() {
  if [[ "$MIGRATION_PENDING" == "true" ]]; then
    printf 'migrate'
  elif [[ -n "$BLOCKED_NAME" ]]; then
    printf 'repair'
  else
    return 1
  fi
}

if [[ -z "$PINNED" ]]; then
  DIRECTION=$(fallback_direction) || exit 0
fi
MEMORY_NAME="${MEMORY_FILE##*/}"

if [[ -z "$DIRECTION" ]]; then
  CURRENT=""
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
    PLUGIN_JSON="${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"
    if [[ -f "$PLUGIN_JSON" && ! -L "$PLUGIN_JSON" && -r "$PLUGIN_JSON" ]]; then
      CURRENT=$(jq -r '.version // empty' "$PLUGIN_JSON" 2>/dev/null) || CURRENT=""
    fi
  fi
  if [[ -z "$CURRENT" ]]; then
    DIRECTION=$(fallback_direction) || exit 0
  fi
fi

# Semver build metadata (`+...`) MUST NOT affect equality or precedence per
# https://semver.org/#spec-item-10. Strip it before comparison, keep the
# original strings for the user-facing message.
version_exceeds_current() {
  local candidate="${1%%+*}" highest
  [[ -n "$candidate" ]] || return 1
  [[ "$candidate" != "$CURRENT_COMPARE" ]] || return 1
  # Semver-aware compare via `sort -V` (natural version sort). Handles semver
  # pre-release precedence correctly: `1.13.1-rc1` sorts below `1.13.1`.
  highest=$(printf '%s\n%s\n' "$candidate" "$CURRENT_COMPARE" | "$SORT_BIN" -V | tail -n 1)
  [[ "$highest" == "$candidate" ]]
}

if [[ -z "$DIRECTION" ]]; then
  PINNED_COMPARE="${PINNED%%+*}"
  CURRENT_COMPARE="${CURRENT%%+*}"
  [[ -n "$PINNED_COMPARE" && -n "$CURRENT_COMPARE" ]] || exit 0

  if [[ "$PINNED_COMPARE" == "$CURRENT_COMPARE" && "${ROOT_PIN%%+*}" == "$CURRENT_COMPARE" ]] \
    || [[ "$PINNED_COMPARE" == "$CURRENT_COMPARE" && -z "$ROOT_PIN" ]]; then
    # Nothing to order: every pin present equals the installed version.
    DIRECTION=$(fallback_direction) || exit 0
  else
    # Some pin differs but no `sort -V` can order them. Staying silent is the
    # only safe answer: the migration and repair notices both end in
    # `/rb:init --update`, which overwrites a newer managed block with an
    # older template — exactly what the `newer` branch exists to prevent.
    SORT_BIN=$(resolve_sort_bin) || exit 0
  fi
fi

# A pin newer than the installed plugin outranks every other direction, in
# EITHER file. `--update` deletes the `CLAUDE.md` copy during migration and
# rewrites the block during refresh, so a newer pin hiding behind the
# preferred pin would be destroyed by the very command those notices
# recommend. Report the highest such pin and its file.
if [[ -z "$DIRECTION" ]]; then
  if version_exceeds_current "$ROOT_PIN" \
    && { [[ -z "$LOCAL_PIN" ]] || ! version_exceeds_current "$LOCAL_PIN" \
      || [[ "$(printf '%s\n%s\n' "${ROOT_PIN%%+*}" "${LOCAL_PIN%%+*}" | "$SORT_BIN" -V | tail -n 1)" == "${ROOT_PIN%%+*}" ]]; }; then
    MEMORY_FILE="$ROOT_MD"
    MEMORY_NAME="CLAUDE.md"
    PINNED="$ROOT_PIN"
    DIRECTION="newer"
  elif version_exceeds_current "$LOCAL_PIN"; then
    MEMORY_FILE="$LOCAL_MD"
    MEMORY_NAME="CLAUDE.local.md"
    PINNED="$LOCAL_PIN"
    DIRECTION="newer"
  fi
fi

if [[ -z "$DIRECTION" ]]; then
  if [[ "$PINNED_COMPARE" == "$CURRENT_COMPARE" ]]; then
    DIRECTION=$(fallback_direction) || exit 0
  else
    DIRECTION="outdated"
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
# The migration covers two shapes with different costs: a duplicate copy (both
# files carry a block) wastes context and drifts once one copy is refreshed,
# while a lone `CLAUDE.md` block simply sits in the file /rb:init no longer
# targets. Do not claim duplicate cost for the lone-block case.
MIGRATION_LINE=""
if [[ "$MIGRATION_PENDING" == "true" ]]; then
  if [[ "$LOCAL_HAS_BLOCK" == "true" ]]; then
    MIGRATION_LINE="A second managed block also remains in CLAUDE.md, wasting context and drifting
from the CLAUDE.local.md copy once either is refreshed; /rb:init --update
deletes the CLAUDE.md copy."
  else
    MIGRATION_LINE="The managed block also still sits in CLAUDE.md rather than this project's
CLAUDE.local.md; /rb:init --update moves it there."
  fi
fi

WRITE_BLOCKED_LINE=""
REPAIR_HINT=""
if [[ -n "$BLOCKED_NAME" ]]; then
  if [[ "$BLOCKED_NAME" != "CLAUDE.local.md" ]]; then
    REPAIR_HINT="restore write access to ${BLOCKED_NAME}"
  elif [[ "$BLOCKED_REASON" == "is not writable" ]]; then
    REPAIR_HINT="restore write access to CLAUDE.local.md, or delete its managed block so
CLAUDE.md becomes the target"
  else
    REPAIR_HINT="add CLAUDE.local.md to .gitignore, or delete its managed block so CLAUDE.md
becomes the target"
  fi
  WRITE_BLOCKED_LINE="${BLOCKED_NAME} holds a managed block and ${BLOCKED_REASON}, so
/rb:init --update stops instead of refreshing it. Have the user ${REPAIR_HINT} first."
fi

case "$DIRECTION" in
outdated)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
Installed plugin v${CURRENT} is ahead of project ${MEMORY_NAME} pinned at v${PINNED}.
${MIGRATION_LINE}
${WRITE_BLOCKED_LINE}
Tell the user at the start of your next response, then recommend:
/rb:init --update
NOTICE
  ;;
newer)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
Installed plugin v${CURRENT} is OLDER than project ${MEMORY_NAME} pinned at v${PINNED}.
${WRITE_BLOCKED_LINE}
The plugin may have been downgraded. Tell the user at the start of your next
response; recommend verifying the install before running /rb:init --update
(it would overwrite the newer marker content with the older template).
NOTICE
  ;;
migrate)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
${MIGRATION_LINE}
CLAUDE.local.md is the file the plugin prefers for its stack notes. Tell the
user at the start of your next response, then recommend:
/rb:init --update
NOTICE
  ;;
repair)
  cat <<NOTICE
[Ruby/Rails/Grape plugin — user action required]
${WRITE_BLOCKED_LINE}
Tell the user at the start of your next response, then recommend running
/rb:init --update once that is done.
NOTICE
  ;;
esac
