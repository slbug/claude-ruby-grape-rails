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

# Prefer Ruby (Psych) when available, fall back to Python (yaml.safe_load_all)
if command -v ruby >/dev/null 2>&1; then
  VALIDATOR='ruby'
elif command -v python3 >/dev/null 2>&1; then
  VALIDATOR='python3'
else
  echo "ERROR: ruby or python3 is required for YAML validation." >&2
  exit 1
fi

git ls-files -z '*.yml' '*.yaml' | while IFS= read -r -d '' file; do
  echo "Validating $file"
  if [[ "$VALIDATOR" == "ruby" ]]; then
    ruby -e 'require "psych"; Psych.parse_stream(File.read(ARGV[0], encoding: "UTF-8"))' "$file" >/dev/null
  else
    python3 -c "import yaml, sys; list(yaml.safe_load_all(open(sys.argv[1])))" "$file" >/dev/null
  fi
done
