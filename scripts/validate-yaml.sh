#!/usr/bin/env bash
set -euo pipefail

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for YAML validation." >&2
    exit 1
  fi
}

require_command git
require_command ruby

git ls-files -z '*.yml' '*.yaml' | while IFS= read -r -d '' file; do
  echo "Validating $file"
  ruby -e 'require "psych"; Psych.parse_stream(File.read(ARGV[0], encoding: "UTF-8"))' "$file" > /dev/null
done
