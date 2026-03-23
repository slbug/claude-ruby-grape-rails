#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || exit 0
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || exit 0

FILE_NAME=$(path_basename "$FILE_PATH")
LOWER_PATH=$(printf '%s' "$FILE_PATH" | tr '[:upper:]' '[:lower:]')
if printf '%s' "$LOWER_PATH" | grep -qiE '(^|/|[._-])(auth|authentication|session|sessions|password|passwords|token|tokens|login|credential|credentials|secret|secrets|oauth|policy|policies|ability|abilities|admin|payment|payments|permission|permissions)(/|[._-]|$)'; then
  cat >&2 <<MSG
SECURITY-SENSITIVE FILE: ${FILE_NAME}
Check these before moving on:
- authorization/policy coverage
- explicit params shaping (strong params or Grape declared params)
- no SQL interpolation
- no html_safe/raw on untrusted content
- Sidekiq enqueue-after-commit discipline for security-sensitive writes
Consider: /rb:review security
MSG
  exit 2
fi
