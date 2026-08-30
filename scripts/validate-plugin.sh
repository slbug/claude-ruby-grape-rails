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

# --strict fails on unrecognized fields and missing metadata, which the
# runtime tolerates silently. Validate the marketplace manifest too: the
# plugin-directory run does not cover `.claude-plugin/marketplace.json`.
claude plugin validate --strict plugins/ruby-grape-rails
claude plugin validate --strict .

# Contributor-only components under `.claude/` ship to nobody but load into
# every in-repo session. A bare component directory is validated as
# components, not as a plugin manifest, and reports SKILL.md files whose
# frontmatter fails to parse.
exec claude plugin validate --strict .claude
