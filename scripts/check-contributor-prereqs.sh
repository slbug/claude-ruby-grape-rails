#!/usr/bin/env bash
set -euo pipefail

MISSING=0

check_required() {
  local command_name="$1"
  local hint="$2"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "MISSING: ${command_name} — ${hint}" >&2
    MISSING=1
  fi
}

check_optional() {
  local command_name="$1"
  local hint="$2"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "OPTIONAL: ${command_name} — ${hint}" >&2
  fi
}

check_required git "required for tracked-file lint, eval changed-mode, and contributor workflows"
check_required bash "required for hook and validation scripts"
check_required python3 "required for eval tests and release checks (python3 3.10+)"
check_required ruby "required for YAML validation and Ruby maintenance scripts"
check_required jq "required for shipped hook payload parsing"
check_required grep "required by hook scripts for pattern matching"
check_required sed "required by hook scripts for text processing"
check_required awk "required by hook scripts for field extraction"
check_required mktemp "required by hook scripts for safe temp file creation"
check_required readlink "required by workspace-root-lib.sh for path resolution"
check_required cksum "required by error-critic.sh for dedup hashing"
check_required cat "required by secret-scan.sh for file content handling"
check_required cp "required by secret-scan.sh for file staging"
check_required find "required by secret-scan.sh for file discovery"
check_required mkdir "required by secret-scan.sh for temp directory creation"
check_required head "required by block-dangerous-ops.sh for input parsing"
check_required tr "required by block-dangerous-ops.sh for text normalization"
check_required wc "required by block-dangerous-ops.sh for size checks"
check_required shellcheck "required for local shell linting and pre-commit shell validation"
check_required claude "required for 'npm run validate' and 'make validate' (install with: npm install -g @anthropic-ai/claude-code)"
check_optional betterleaks "optional for local secret-scan coverage outside CI"

if [[ "$MISSING" -eq 1 ]]; then
  echo "ERROR: contributor prerequisites are incomplete." >&2
  exit 1
fi

echo "Contributor prerequisites look good."
