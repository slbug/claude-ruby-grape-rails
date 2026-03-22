#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Detect Ruby runtime environment and available tooling
# This hook runs at SessionStart to populate context

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi
PROJECT_GEMFILE="${REPO_ROOT}/Gemfile"
PROJECT_LOCKFILE="${REPO_ROOT}/Gemfile.lock"
CLAUDE_DIR="${REPO_ROOT}/.claude"

STACK=()
TOOLS=()
RUNTIME_INFO=()
RUBY_VERSION=""
RAILS_VERSION=""

# Detect Ruby version
if command -v ruby >/dev/null 2>&1; then
  RUBY_VERSION=$(ruby -v 2>/dev/null | awk '{print $2}')
  RUNTIME_INFO+=("Ruby $RUBY_VERSION")
fi

# Detect Rails version from Gemfile.lock
if [[ -f "$PROJECT_LOCKFILE" ]]; then
  RAILS_VERSION=$(grep -E "^    rails " "$PROJECT_LOCKFILE" | head -1 | sed 's/.*(\(.*\)).*/\1/')
  if [[ -n "$RAILS_VERSION" ]]; then
    RUNTIME_INFO+=("Rails $RAILS_VERSION")
    STACK+=("Rails")
  fi
fi

# Detect stack gems
[[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]grape['\"]" "$PROJECT_GEMFILE" && STACK+=("Grape")
[[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]sidekiq['\"]" "$PROJECT_GEMFILE" && STACK+=("Sidekiq")
[[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]redis['\"]|gem ['\"]redis-client['\"]" "$PROJECT_GEMFILE" && STACK+=("Redis")
[[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]pg['\"]" "$PROJECT_GEMFILE" && STACK+=("PostgreSQL")
[[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]solid_queue['\"]" "$PROJECT_GEMFILE" && STACK+=("SolidQueue")
[[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]karafka['\"]" "$PROJECT_GEMFILE" && STACK+=("Karafka")

# Detect local runtime tools
command -v psql >/dev/null 2>&1 && TOOLS+=("psql")
command -v redis-cli >/dev/null 2>&1 && TOOLS+=("redis-cli")
command -v bundle >/dev/null 2>&1 && TOOLS+=("bundle")

# Detect Tidewave Rails gem (MCP-based runtime integration)
TIDEWAVE_GEM_PRESENT=false
if [[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]tidewave['\"]" "$PROJECT_GEMFILE"; then
  TIDEWAVE_GEM_PRESENT=true
  STACK+=("Tidewave")
fi

# Detect RTK (CLI proxy for LLM token optimization)
if command -v rtk >/dev/null 2>&1; then
  TOOLS+=("rtk")
fi

# Report runtime info
if [[ ${#RUNTIME_INFO[@]} -gt 0 ]]; then
  echo "✓ Runtime: ${RUNTIME_INFO[*]}"
fi

if [[ ${#STACK[@]} -gt 0 ]]; then
  echo "✓ Stack: ${STACK[*]}"
fi

if [[ ${#TOOLS[@]} -gt 0 ]]; then
  echo "✓ Tools: ${TOOLS[*]}"
fi

if [[ ${#RUNTIME_INFO[@]} -eq 0 && ${#STACK[@]} -eq 0 ]]; then
  echo "○ Ruby plugin loaded — minimal stack detected"
fi

# Export runtime environment to file for other scripts
RUNTIME_ENV_FILE="${CLAUDE_DIR}/.runtime_env"
mkdir -p -- "$CLAUDE_DIR" || exit 0

if [[ -L "$RUNTIME_ENV_FILE" ]]; then
  exit 0
fi

if [[ -e "$RUNTIME_ENV_FILE" && ! -f "$RUNTIME_ENV_FILE" ]]; then
  exit 0
fi

TMP_RUNTIME_ENV=$(mktemp "${CLAUDE_DIR}/.runtime_env.XXXXXX") || exit 0
[[ -n "$TMP_RUNTIME_ENV" ]] || exit 0
trap 'rm -f -- "$TMP_RUNTIME_ENV"' EXIT HUP INT TERM

{
  # Export detected values
  [[ -n "$RUBY_VERSION" ]] && echo "RUBY_VERSION=$RUBY_VERSION"
  [[ -n "$RAILS_VERSION" ]] && echo "RAILS_VERSION=$RAILS_VERSION"
  [[ ${#STACK[@]} -gt 0 ]] && echo "STACK_GEMS=\"${STACK[*]}\""
  [[ ${#TOOLS[@]} -gt 0 ]] && echo "TOOLS=\"${TOOLS[*]}\""

  # Tool availability booleans
  if [[ "$TIDEWAVE_GEM_PRESENT" == "true" ]]; then
    echo "TIDEWAVE_GEM_PRESENT=true"
    echo "TIDEWAVE_PROJECT_CAPABLE=true"
  else
    echo "TIDEWAVE_GEM_PRESENT=false"
    echo "TIDEWAVE_PROJECT_CAPABLE=false"
  fi

  if [[ " ${TOOLS[*]} " =~ " rtk " ]]; then
    echo "RTK_AVAILABLE=true"
  else
    echo "RTK_AVAILABLE=false"
  fi

  if command -v psql >/dev/null 2>&1; then
    echo "PSQL_AVAILABLE=true"
  else
    echo "PSQL_AVAILABLE=false"
  fi

  if command -v redis-cli >/dev/null 2>&1; then
    echo "REDIS_CLI_AVAILABLE=true"
  else
    echo "REDIS_CLI_AVAILABLE=false"
  fi

  # Ruby tool availability
  if command -v bundle >/dev/null 2>&1; then
    echo "BUNDLE_AVAILABLE=true"
  else
    echo "BUNDLE_AVAILABLE=false"
  fi
} > "$TMP_RUNTIME_ENV"

mv -f -- "$TMP_RUNTIME_ENV" "$RUNTIME_ENV_FILE"
trap - EXIT HUP INT TERM
