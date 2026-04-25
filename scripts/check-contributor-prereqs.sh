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
check_required python3 "required for eval tests and release checks (python3 3.14+)"

# Verify python3 actually meets the floor (3.14+) — `command -v python3`
# alone passes for older interpreters and `lab/eval/run_eval.sh` would
# hard-fail later. Mirror the predicate used by
# `lab/eval/run_eval.sh::require_python_314`.
check_python_version_314() {
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)' >/dev/null 2>&1; then
    return
  fi
  local actual
  actual="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  if [[ -z "$actual" ]]; then
    echo "MISSING: python3 is on PATH but its version cannot be determined; lab/eval/ requires 3.14+" >&2
  else
    echo "MISSING: python3 ${actual} is below the 3.14 floor required by lab/eval/" >&2
  fi
  MISSING=1
}

# Verify the required Python modules. Module names are hardcoded — never
# pass a function argument here; the module name flows into a `python3 -c`
# string and would be a code-injection vector if user-influenced.
check_dev_python_modules() {
  if ! python3 -c "import yaml" >/dev/null 2>&1; then
    echo "MISSING: python3 module 'yaml' — install with: python3 -m pip install -r requirements-dev.txt" >&2
    MISSING=1
  fi
}

if command -v python3 >/dev/null 2>&1; then
  check_python_version_314
  check_dev_python_modules
fi
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
check_required mv "required by hook scripts for atomic file moves"
check_required rm "required by hook scripts for temp file cleanup"
check_required curl "required by fetch-cc-changelog.sh and fetch-claude-docs.sh"
check_required npm "required for lint, pre-commit hooks, and package scripts"
check_required npx "required by pre-commit hook for markdownlint"
check_required shellcheck "required for local shell linting and pre-commit shell validation"
check_required claude "required for 'npm run validate' and 'make validate' (install with: npm install -g @anthropic-ai/claude-code)"
check_optional betterleaks "optional for local secret-scan coverage outside CI"
check_optional ollama "optional unless you run fresh behavioral/neighbor evals with the default Ollama provider; default model is gemma4:26b-a4b-it-q8_0 (~28GB RAM). Set RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest for low-RAM fallback (10GB)."
check_optional apfel "optional only if you run behavioral/neighbor evals with --provider apfel or RUBY_PLUGIN_EVAL_PROVIDER=apfel"

if [[ "$MISSING" -eq 1 ]]; then
  echo "ERROR: contributor prerequisites are incomplete." >&2
  exit 1
fi

echo "Contributor prerequisites look good."
