#!/usr/bin/env bash
# Detect Ruby runtime environment and available tooling
# This hook runs at SessionStart to populate context

STACK=()
TOOLS=()
RUNTIME_INFO=()

# Detect Ruby version
if command -v ruby >/dev/null 2>&1; then
  RUBY_VERSION=$(ruby -v 2>/dev/null | awk '{print $2}')
  RUNTIME_INFO+=("Ruby $RUBY_VERSION")
fi

# Detect Rails version from Gemfile.lock
if [[ -f Gemfile.lock ]]; then
  RAILS_VERSION=$(grep -E "^    rails " Gemfile.lock | head -1 | sed 's/.*(\(.*\)).*/\1/')
  if [[ -n "$RAILS_VERSION" ]]; then
    RUNTIME_INFO+=("Rails $RAILS_VERSION")
    STACK+=("Rails")
  fi
fi

# Detect stack gems
[[ -f Gemfile ]] && grep -Eq "gem ['\"]grape['\"]" Gemfile && STACK+=("Grape")
[[ -f Gemfile ]] && grep -Eq "gem ['\"]sidekiq['\"]" Gemfile && STACK+=("Sidekiq")
[[ -f Gemfile ]] && grep -Eq "gem ['\"]redis['\"]|gem ['\"]redis-client['\"]" Gemfile && STACK+=("Redis")
[[ -f Gemfile ]] && grep -Eq "gem ['\"]pg['\"]" Gemfile && STACK+=("PostgreSQL")
[[ -f Gemfile ]] && grep -Eq "gem ['\"]solid_queue['\"]" Gemfile && STACK+=("SolidQueue")
[[ -f Gemfile ]] && grep -Eq "gem ['\"]karafka['\"]" Gemfile && STACK+=("Karafka")

# Detect local runtime tools
command -v psql >/dev/null 2>&1 && TOOLS+=("psql")
command -v redis-cli >/dev/null 2>&1 && TOOLS+=("redis-cli")
command -v bundle >/dev/null 2>&1 && TOOLS+=("bundle")

# Detect Tidewave Rails gem (MCP-based runtime integration)
TIDEWAVE_GEM_PRESENT=false
if [[ -f Gemfile ]] && grep -Eq "gem ['\"]tidewave['\"]" Gemfile; then
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
RUNTIME_ENV_FILE=".claude/.runtime_env"
mkdir -p .claude

# Clear old values
: > "$RUNTIME_ENV_FILE"

# Export detected values
[[ -n "$RUBY_VERSION" ]] && echo "RUBY_VERSION=$RUBY_VERSION" >> "$RUNTIME_ENV_FILE"
[[ -n "$RAILS_VERSION" ]] && echo "RAILS_VERSION=$RAILS_VERSION" >> "$RUNTIME_ENV_FILE"
[[ ${#STACK[@]} -gt 0 ]] && echo "STACK_GEMS=\"${STACK[*]}\"" >> "$RUNTIME_ENV_FILE"
[[ ${#TOOLS[@]} -gt 0 ]] && echo "TOOLS=\"${TOOLS[*]}\"" >> "$RUNTIME_ENV_FILE"

# Tool availability booleans
if [[ "$TIDEWAVE_GEM_PRESENT" == "true" ]]; then
  echo "TIDEWAVE_GEM_PRESENT=true" >> "$RUNTIME_ENV_FILE"
  echo "TIDEWAVE_PROJECT_CAPABLE=true" >> "$RUNTIME_ENV_FILE"
else
  echo "TIDEWAVE_GEM_PRESENT=false" >> "$RUNTIME_ENV_FILE"
  echo "TIDEWAVE_PROJECT_CAPABLE=false" >> "$RUNTIME_ENV_FILE"
fi

if [[ " ${TOOLS[*]} " =~ " rtk " ]]; then
  echo "RTK_AVAILABLE=true" >> "$RUNTIME_ENV_FILE"
else
  echo "RTK_AVAILABLE=false" >> "$RUNTIME_ENV_FILE"
fi

if command -v psql >/dev/null 2>&1; then
  echo "PSQL_AVAILABLE=true" >> "$RUNTIME_ENV_FILE"
else
  echo "PSQL_AVAILABLE=false" >> "$RUNTIME_ENV_FILE"
fi

if command -v redis-cli >/dev/null 2>&1; then
  echo "REDIS_CLI_AVAILABLE=true" >> "$RUNTIME_ENV_FILE"
else
  echo "REDIS_CLI_AVAILABLE=false" >> "$RUNTIME_ENV_FILE"
fi

# Ruby tool availability
if command -v bundle >/dev/null 2>&1; then
  echo "BUNDLE_AVAILABLE=true" >> "$RUNTIME_ENV_FILE"
else
  echo "BUNDLE_AVAILABLE=false" >> "$RUNTIME_ENV_FILE"
fi
