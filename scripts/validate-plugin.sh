#!/usr/bin/env bash
set -euo pipefail

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for plugin validation." >&2
    if [[ "$command_name" == "claude" ]]; then
      echo "Install the Claude Code CLI with: npm install -g @anthropic-ai/claude-code" >&2
    fi
    exit 1
  fi
}

require_command claude

exec claude plugin validate plugins/ruby-grape-rails
