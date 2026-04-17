#!/usr/bin/env bash
# SessionStart hook: install/refresh a statusline wrapper in the user's home.
#
# Why this exists:
#   Plugin settings.json `subagentStatusLine.command` does NOT expand
#   ${CLAUDE_PLUGIN_ROOT} (unlike hooks.json, .mcp.json, monitors.json),
#   and CLAUDE_PLUGIN_ROOT is NOT exported as an env var to the statusline
#   subprocess. Scripts bundled in plugin bin/ therefore cannot be
#   referenced directly from plugin settings.json. We work around this by
#   writing a small wrapper at ~/.claude/ruby-grape-rails-subagent-statusline
#   whose sole job is to `exec` the current plugin's bin/subagent-statusline
#   using the now-resolved absolute path. The plugin settings.json points
#   at this stable wrapper path.
#
# The absolute path of the plugin install dir changes per version (see
# ${CLAUDE_PLUGIN_ROOT}, which points into the user's plugin cache). We
# rewrite the wrapper on every SessionStart, but only when its current
# content differs from the desired content — cheap no-op on unchanged
# sessions.
#
# Policy: advisory — any error path exits 0 silently. Never blocks session
# start. Plugin settings.json falls back to CC's default row when the
# wrapper is missing or broken.

set -o nounset
set -o pipefail

[[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]] || exit 0
[[ -n "${HOME:-}" ]] || exit 0
BIN_PATH="${CLAUDE_PLUGIN_ROOT}/bin/subagent-statusline"
[[ -x "$BIN_PATH" && ! -L "$BIN_PATH" ]] || exit 0

WRAPPER_DIR="${HOME}/.claude"
WRAPPER="${WRAPPER_DIR}/ruby-grape-rails-subagent-statusline"

[[ -d "$WRAPPER_DIR" && ! -L "$WRAPPER_DIR" ]] || exit 0
# Refuse to replace a symlink at the target path.
[[ ! -L "$WRAPPER" ]] || exit 0
# Refuse to replace anything other than a regular file (e.g. a directory
# would cause mv to move the temp file INTO it rather than replacing the
# wrapper).
[[ ! -e "$WRAPPER" || -f "$WRAPPER" ]] || exit 0

DESIRED=$(printf '#!/usr/bin/env bash\nexec %q "$@"\n' "$BIN_PATH")

if [[ -r "$WRAPPER" && -f "$WRAPPER" ]]; then
  CURRENT=$(cat -- "$WRAPPER" 2>/dev/null || true)
  if [[ "$CURRENT" == "$DESIRED" ]]; then
    exit 0
  fi
fi

TMP=$(mktemp "${WRAPPER_DIR}/.tmp.statusline-wrapper.XXXXXX" 2>/dev/null) || exit 0
if [[ ! -f "$TMP" || -L "$TMP" || "$TMP" != "${WRAPPER_DIR}/.tmp.statusline-wrapper."* ]]; then
  rm -f -- "${TMP:?}" 2>/dev/null || true
  exit 0
fi

if ! printf '%s' "$DESIRED" > "$TMP" 2>/dev/null; then
  rm -f -- "${TMP:?}" 2>/dev/null || true
  exit 0
fi
if ! chmod 0755 -- "$TMP" 2>/dev/null; then
  rm -f -- "${TMP:?}" 2>/dev/null || true
  exit 0
fi
mv -f -- "$TMP" "$WRAPPER" 2>/dev/null || {
  rm -f -- "${TMP:?}" 2>/dev/null || true
  exit 0
}

exit 0
