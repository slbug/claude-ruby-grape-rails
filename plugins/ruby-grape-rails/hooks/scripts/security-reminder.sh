#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0

FILE_NAME="${FILE_PATH##*/}"
if printf '%s' "$FILE_PATH" | grep -qiE '(auth|session|password|token|permission|admin|payment|login|credential|secret|oauth|policy|ability)'; then
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
