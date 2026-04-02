#!/usr/bin/env bash
set -euo pipefail

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for JSON validation." >&2
    exit 1
  fi
}

require_command git
require_command python3

git ls-files -z '*.json' | while IFS= read -r -d '' file; do
  echo "Validating $file"
  python3 -m json.tool "$file" > /dev/null
done
