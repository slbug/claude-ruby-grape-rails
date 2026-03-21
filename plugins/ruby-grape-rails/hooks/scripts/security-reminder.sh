#!/usr/bin/env bash

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0

if echo "$FILE_PATH" | grep -qiE '(auth|session|password|token|permission|admin|payment|login|credential|secret|oauth|policy|ability|grape|api)'; then
  cat >&2 <<MSG
SECURITY-SENSITIVE FILE: $(basename "$FILE_PATH")
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
