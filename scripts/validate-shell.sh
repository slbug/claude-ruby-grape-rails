#!/usr/bin/env bash
set -euo pipefail

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for shell validation." >&2
    if [[ "$command_name" == "shellcheck" ]]; then
      echo "Install shellcheck with your system package manager before running local lint or pre-commit checks." >&2
    fi
    exit 1
  fi
}

require_command git
require_command bash
require_command shellcheck

git ls-files -z '*.sh' '*.bash' '.husky/pre-commit' | while IFS= read -r -d '' file; do
  echo "Checking $file"
  bash -n "$file"
  shellcheck -x "$file"
done
