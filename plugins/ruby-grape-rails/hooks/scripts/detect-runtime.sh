#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Detect Ruby runtime environment and available tooling
# This hook runs at SessionStart to populate context

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
PROJECT_GEMFILE="${REPO_ROOT}/Gemfile"
PROJECT_LOCKFILE="${REPO_ROOT}/Gemfile.lock"
CLAUDE_DIR="${REPO_ROOT}/.claude"

STACK=()
TOOLS=()
RUNTIME_INFO=()
RUBY_VERSION=""
RAILS_VERSION=""
FALLBACK_RAILS_VERSION=""
ACTIVERECORD_VERSION=""
SEQUEL_VERSION=""
DETECTED_ORMS=""
PRIMARY_ORM="unknown"
RAILS_COMPONENTS="false"
FULL_RAILS_APP="false"
PACKAGE_LAYOUT="single_app"
PACKAGE_LOCATIONS=""
PACKAGE_QUERY_NEEDED="false"
HAS_PACKWERK="false"
HOOK_MODE=$(resolve_hook_mode "$REPO_ROOT")
BETTERLEAKS_PATH=""
RTK_PATH=""
RTK_VERSION=""
RTK_GAIN_AVAILABLE=false
PSQL_AVAILABLE=false
REDIS_CLI_AVAILABLE=false
BUNDLE_AVAILABLE=false
STANDARDRB_AVAILABLE=false
STANDARDRB_VERSION=""
RUBOCOP_AVAILABLE=false
RUBOCOP_VERSION=""
BRAKEMAN_AVAILABLE=false
BRAKEMAN_VERSION=""
PRONTO_AVAILABLE=false
PRONTO_VERSION=""
LEFTHOOK_AVAILABLE=false
LEFTHOOK_VERSION=""
LEFTHOOK_CONFIG_PRESENT=false
LEFTHOOK_CONFIG_PATH=""
LEFTHOOK_LINT_COVERED=false
LEFTHOOK_DIFF_LINT_COVERED=false
LEFTHOOK_SECURITY_COVERED=false
LEFTHOOK_LINT_SECURITY_COVERED=false
LEFTHOOK_PRONTO_COVERED=false
LEFTHOOK_COMMAND=""
VERIFY_COMPOSITE_AVAILABLE=false
VERIFY_COMPOSITE_COMMAND=""
VERIFY_COMPOSITE_SOURCE=""

emit_shell_assignment() {
  local key="$1"
  local value="${2-}"
  printf '%s=' "$key"
  printf '%q\n' "$value"
}

escape_ere() {
  printf '%s' "$1" | sed 's/[][(){}.^$?+*|\\/]/\\&/g'
}

gem_declared() {
  local gem_name="$1"
  local escaped_name

  [[ -f "$PROJECT_GEMFILE" ]] || return 1
  escaped_name=$(escape_ere "$gem_name")
  grep -Eq "^[[:space:]]*gem[[:space:]]+['\"]${escaped_name}['\"]([[:space:]]*(,|#|$))" "$PROJECT_GEMFILE"
}

gemfile_declares_pattern() {
  local pattern="$1"

  [[ -f "$PROJECT_GEMFILE" ]] || return 1
  grep -Eq "$pattern" "$PROJECT_GEMFILE"
}

lock_version() {
  local gem_name="$1"
  local escaped_name

  [[ -f "$PROJECT_LOCKFILE" ]] || return 1
  escaped_name=$(escape_ere "$gem_name")
  grep -m 1 -E "^[[:space:]]{4}${escaped_name} \([^)]+\)$" "$PROJECT_LOCKFILE" |
    sed -E 's/.*\(([^)]+)\).*/\1/'
}

lock_has_gem() {
  local gem_name="$1"
  local version

  version=$(lock_version "$gem_name" || true)
  [[ -n "$version" ]]
}

add_tool() {
  local tool_name="$1"
  [[ " ${TOOLS[*]} " == *" ${tool_name} "* ]] || TOOLS+=("$tool_name")
}

find_first_repo_file() {
  local candidate

  for candidate in "$@"; do
    if [[ -f "${REPO_ROOT}/${candidate}" && ! -L "${REPO_ROOT}/${candidate}" ]]; then
      printf '%s' "${REPO_ROOT}/${candidate}"
      return 0
    fi
  done

  return 1
}

makefile_has_target() {
  local target_name="$1"
  local makefile_path
  local escaped_target

  makefile_path=$(find_first_repo_file GNUmakefile Makefile makefile || true)
  [[ -n "$makefile_path" ]] || return 1

  escaped_target=$(escape_ere "$target_name")
  grep -Eq "^[[:space:]]*${escaped_target}[[:space:]]*:" "$makefile_path"
}

rake_task_declared_in_file() {
  local task_name="$1"
  local target_file="$2"
  local escaped_task

  [[ -f "$target_file" && ! -L "$target_file" ]] || return 1

  escaped_task=$(escape_ere "$task_name")
  grep -Eq "task[[:space:]]*(\\(|:|['\"])${escaped_task}([[:space:][:punct:]]|$)|${escaped_task}:[[:space:]]" "$target_file"
}

rake_task_declared() {
  local task_name="$1"
  local task_file

  if rake_task_declared_in_file "$task_name" "${REPO_ROOT}/Rakefile"; then
    return 0
  fi

  [[ -d "${REPO_ROOT}/lib/tasks" ]] || return 1

  while IFS= read -r task_file; do
    if rake_task_declared_in_file "$task_name" "$task_file"; then
      return 0
    fi
  done < <(find "${REPO_ROOT}/lib/tasks" -type f -name '*.rake' ! -lname '*' 2>/dev/null)

  return 1
}

justfile_has_recipe() {
  local recipe_name="$1"
  local justfile_path
  local escaped_recipe

  justfile_path=$(find_first_repo_file justfile .justfile Justfile || true)
  [[ -n "$justfile_path" ]] || return 1
  command -v just >/dev/null 2>&1 || return 1

  escaped_recipe=$(escape_ere "$recipe_name")
  grep -Eq "^[[:space:]]*${escaped_recipe}[[:space:]]*:" "$justfile_path"
}

detect_verify_composite() {
  local candidate

  for candidate in bin/check bin/ci bin/verify script/check script/ci script/verify; do
    if [[ -f "${REPO_ROOT}/${candidate}" && ! -L "${REPO_ROOT}/${candidate}" ]]; then
      VERIFY_COMPOSITE_AVAILABLE=true
      VERIFY_COMPOSITE_COMMAND="./${candidate}"
      VERIFY_COMPOSITE_SOURCE="$candidate"
      return 0
    fi
  done

  if makefile_has_target ci; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="make ci"
    VERIFY_COMPOSITE_SOURCE="Makefile:ci"
    return 0
  fi

  if makefile_has_target check; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="make check"
    VERIFY_COMPOSITE_SOURCE="Makefile:check"
    return 0
  fi

  if makefile_has_target verify; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="make verify"
    VERIFY_COMPOSITE_SOURCE="Makefile:verify"
    return 0
  fi

  if justfile_has_recipe ci; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="just ci"
    VERIFY_COMPOSITE_SOURCE="justfile:ci"
    return 0
  fi

  if justfile_has_recipe check; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="just check"
    VERIFY_COMPOSITE_SOURCE="justfile:check"
    return 0
  fi

  if justfile_has_recipe verify; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="just verify"
    VERIFY_COMPOSITE_SOURCE="justfile:verify"
    return 0
  fi

  if rake_task_declared ci; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="bundle exec rake ci"
    VERIFY_COMPOSITE_SOURCE="rake:ci"
    return 0
  fi

  if rake_task_declared check; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="bundle exec rake check"
    VERIFY_COMPOSITE_SOURCE="rake:check"
    return 0
  fi

  if rake_task_declared verify; then
    VERIFY_COMPOSITE_AVAILABLE=true
    VERIFY_COMPOSITE_COMMAND="bundle exec rake verify"
    VERIFY_COMPOSITE_SOURCE="rake:verify"
    return 0
  fi

  return 1
}

# Detect Ruby version
if command -v ruby >/dev/null 2>&1; then
  RUBY_VERSION=$(ruby -v 2>/dev/null | awk '{print $2}')
  RUNTIME_INFO+=("Ruby $RUBY_VERSION")
fi

# Detect Rails version from Gemfile.lock as a fallback only.
if [[ -f "$PROJECT_LOCKFILE" ]]; then
  FALLBACK_RAILS_VERSION=$(grep -m 1 -E "^    rails " "$PROJECT_LOCKFILE" | sed 's/.*(\(.*\)).*/\1/')
fi

# Detect richer stack/package signals via the shared init detector.
STACK_DETECTOR="${SCRIPT_DIR}/../../scripts/detect-stack.rb"
DETECTED_STACK_RAW=""
STACK_DETECTOR_OK=false
if command -v ruby >/dev/null 2>&1 && [[ -f "$STACK_DETECTOR" && ! -L "$STACK_DETECTOR" ]]; then
  if STACK_DETECTOR_OUTPUT=$(cd "$REPO_ROOT" && ruby "$STACK_DETECTOR" 2>/dev/null); then
    STACK_DETECTOR_OK=true
  fi
fi

if [[ "$STACK_DETECTOR_OK" == "true" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    [[ "$line" == \#* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"

    case "$key" in
      DETECTED_STACK) DETECTED_STACK_RAW="$value" ;;
      RAILS_VERSION) [[ -n "$value" ]] && RAILS_VERSION="$value" ;;
      ACTIVERECORD_VERSION) ACTIVERECORD_VERSION="$value" ;;
      SEQUEL_VERSION) SEQUEL_VERSION="$value" ;;
      DETECTED_ORMS) DETECTED_ORMS="$value" ;;
      PRIMARY_ORM) [[ -n "$value" ]] && PRIMARY_ORM="$value" ;;
      RAILS_COMPONENTS) RAILS_COMPONENTS="$value" ;;
      FULL_RAILS_APP) FULL_RAILS_APP="$value" ;;
      PACKAGE_LAYOUT) [[ -n "$value" ]] && PACKAGE_LAYOUT="$value" ;;
      PACKAGE_LOCATIONS) PACKAGE_LOCATIONS="$value" ;;
      PACKAGE_QUERY_NEEDED) PACKAGE_QUERY_NEEDED="$value" ;;
      HAS_PACKWERK) HAS_PACKWERK="$value" ;;
    esac
  done <<< "$STACK_DETECTOR_OUTPUT"
else
  fallback_stack=()
  fallback_orms=()
  full_rails_markers=(config/application.rb config/environment.rb bin/rails)

  if gem_declared 'rails'; then
    fallback_stack+=("rails")
  fi

  if gem_declared 'grape'; then
    fallback_stack+=("grape")
  fi

  if gem_declared 'sidekiq'; then
    fallback_stack+=("sidekiq")
  fi

  if gem_declared 'redis' || gem_declared 'redis-client'; then
    fallback_stack+=("redis")
  fi

  if gem_declared 'pg'; then
    fallback_stack+=("postgres")
  fi

  if gem_declared 'mysql2'; then
    fallback_stack+=("mysql")
  fi

  if gem_declared 'solid_queue'; then
    fallback_stack+=("solid_queue")
  fi

  if gem_declared 'karafka'; then
    fallback_stack+=("karafka")
  fi

  if gem_declared 'hotwire-rails'; then
    fallback_stack+=("hotwire")
  fi

  if gem_declared 'rails' || gem_declared 'activerecord'; then
    fallback_orms+=("active_record")
  fi

  if gem_declared 'sequel' || gem_declared 'sequel-rails'; then
    fallback_orms+=("sequel")
  fi

  rails_component_gems=(activesupport activemodel activerecord actionpack actionview actionmailer actioncable activejob railties)
  for component_gem in "${rails_component_gems[@]}"; do
    if gem_declared "$component_gem"; then
      RAILS_COMPONENTS="true"
      break
    fi
  done

  for marker in "${full_rails_markers[@]}"; do
    if [[ -e "${REPO_ROOT}/${marker}" ]]; then
      FULL_RAILS_APP="true"
      break
    fi
  done

  if gem_declared 'rails'; then
    RAILS_COMPONENTS="true"
  fi

  if [[ ${#fallback_stack[@]} -gt 0 ]]; then
    DETECTED_STACK_RAW=$(IFS=,; printf '%s' "${fallback_stack[*]}")
  fi

  if [[ ${#fallback_orms[@]} -gt 0 ]]; then
    DETECTED_ORMS=$(IFS=,; printf '%s' "${fallback_orms[*]}")
    if [[ ${#fallback_orms[@]} -eq 1 ]]; then
      PRIMARY_ORM="${fallback_orms[0]}"
    else
      PRIMARY_ORM="mixed"
    fi
  fi
fi

if [[ -z "$RAILS_VERSION" && "$FULL_RAILS_APP" == "true" && -n "$FALLBACK_RAILS_VERSION" ]]; then
  RAILS_VERSION="$FALLBACK_RAILS_VERSION"
fi

if [[ "$FULL_RAILS_APP" == "true" ]]; then
  if [[ -n "$RAILS_VERSION" ]]; then
    RUNTIME_INFO+=("Rails $RAILS_VERSION")
  else
    RUNTIME_INFO+=("Rails")
  fi
  STACK+=("Rails")
fi

for component in ${DETECTED_STACK_RAW//,/ }; do
  case "$component" in
    grape) STACK+=("Grape") ;;
    sidekiq) STACK+=("Sidekiq") ;;
    redis) STACK+=("Redis") ;;
    postgres) STACK+=("PostgreSQL") ;;
    mysql) STACK+=("MySQL") ;;
    solid_queue) STACK+=("SolidQueue") ;;
    karafka) STACK+=("Karafka") ;;
    hotwire) STACK+=("Hotwire") ;;
    rails) : ;;
  esac
done

if [[ -n "$DETECTED_ORMS" ]]; then
  [[ "$DETECTED_ORMS" == *"active_record"* ]] && STACK+=("ActiveRecord")
  [[ "$DETECTED_ORMS" == *"sequel"* ]] && STACK+=("Sequel")
fi

if [[ "$HAS_PACKWERK" == "true" ]]; then
  STACK+=("Packwerk")
elif [[ "$PACKAGE_LAYOUT" != "single_app" ]]; then
  STACK+=("ModularMonolith")
fi

# Detect local runtime tools
if command -v psql >/dev/null 2>&1; then
  PSQL_AVAILABLE=true
  TOOLS+=("psql")
fi
if command -v redis-cli >/dev/null 2>&1; then
  REDIS_CLI_AVAILABLE=true
  TOOLS+=("redis-cli")
fi
if command -v bundle >/dev/null 2>&1; then
  BUNDLE_AVAILABLE=true
  add_tool "bundle"
fi

# Detect Tidewave Rails gem (MCP-based runtime integration)
TIDEWAVE_GEM_PRESENT=false
if [[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]tidewave['\"]" "$PROJECT_GEMFILE"; then
  TIDEWAVE_GEM_PRESENT=true
  STACK+=("Tidewave")
fi

# Detect project verification tools
if gem_declared 'standard' || lock_has_gem 'standard'; then
  STANDARDRB_AVAILABLE=true
  STANDARDRB_VERSION=$(lock_version 'standard' || true)
  add_tool "standardrb"
fi

if gem_declared 'rubocop' || lock_has_gem 'rubocop' || gemfile_declares_pattern "^[[:space:]]*gem[[:space:]]+['\"]rubocop-" ; then
  RUBOCOP_AVAILABLE=true
  RUBOCOP_VERSION=$(lock_version 'rubocop' || true)
  add_tool "rubocop"
fi

if gem_declared 'brakeman' || lock_has_gem 'brakeman'; then
  BRAKEMAN_AVAILABLE=true
  BRAKEMAN_VERSION=$(lock_version 'brakeman' || true)
  add_tool "brakeman"
fi

if gem_declared 'pronto' || lock_has_gem 'pronto' || gemfile_declares_pattern "^[[:space:]]*gem[[:space:]]+['\"]pronto-" ; then
  PRONTO_AVAILABLE=true
  PRONTO_VERSION=$(lock_version 'pronto' || true)
  add_tool "pronto"
fi

# Detect Lefthook as either a configured project gem or an installed command.
if gem_declared 'lefthook' || lock_has_gem 'lefthook'; then
  LEFTHOOK_AVAILABLE=true
  LEFTHOOK_VERSION=$(lock_version 'lefthook' || true)
  LEFTHOOK_COMMAND="bundle exec lefthook"
fi

if command -v lefthook >/dev/null 2>&1; then
  LEFTHOOK_AVAILABLE=true
  [[ -n "$LEFTHOOK_COMMAND" ]] || LEFTHOOK_COMMAND="lefthook"
  add_tool "lefthook"
  if [[ -z "$LEFTHOOK_VERSION" ]]; then
    LEFTHOOK_VERSION=$(lefthook version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
    [[ -n "$LEFTHOOK_VERSION" ]] || LEFTHOOK_VERSION=$(lefthook --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)
  fi
fi

if [[ "$LEFTHOOK_AVAILABLE" == "true" ]]; then
  add_tool "lefthook"
fi

LEFTHOOK_CONFIG_PATH=$(find_first_repo_file \
  lefthook.yml \
  lefthook.yaml \
  .lefthook.yml \
  .lefthook.yaml \
  lefthook-local.yml \
  lefthook-local.yaml \
  .lefthook-local.yml \
  .lefthook-local.yaml || true)

if [[ -n "$LEFTHOOK_CONFIG_PATH" ]]; then
  LEFTHOOK_CONFIG_PRESENT=true

  if grep -Eq '(^|[^[:alnum:]_])(standard|standardrb|rubocop)([^[:alnum:]_]|$)' "$LEFTHOOK_CONFIG_PATH"; then
    LEFTHOOK_LINT_COVERED=true
  fi

  if grep -Eq '(^|[^[:alnum:]_])pronto([^[:alnum:]_]|$)' "$LEFTHOOK_CONFIG_PATH" && { lock_has_gem 'pronto-rubocop' || gemfile_declares_pattern "^[[:space:]]*gem[[:space:]]+['\"]pronto-rubocop['\"]"; }; then
    LEFTHOOK_DIFF_LINT_COVERED=true
  fi

  if grep -Eq '(brakeman|betterleaks|bundler[ -]?audit|flog|debride)' "$LEFTHOOK_CONFIG_PATH"; then
    LEFTHOOK_SECURITY_COVERED=true
  fi

  if grep -Eq '(^|[^[:alnum:]_])pronto([^[:alnum:]_]|$)' "$LEFTHOOK_CONFIG_PATH"; then
    LEFTHOOK_PRONTO_COVERED=true
  fi
fi

if [[ "$LEFTHOOK_LINT_COVERED" == "true" && "$LEFTHOOK_SECURITY_COVERED" == "true" ]]; then
  LEFTHOOK_LINT_SECURITY_COVERED=true
fi

detect_verify_composite || true

# Detect RTK (CLI proxy for LLM token optimization)
if command -v rtk >/dev/null 2>&1; then
  RTK_PATH=$(command -v rtk)
  add_tool "rtk"
fi

# Detect Betterleaks executable
if command -v betterleaks >/dev/null 2>&1; then
  BETTERLEAKS_PATH=$(command -v betterleaks)
  add_tool "betterleaks"
elif [[ -x "$HOME/.local/bin/betterleaks" ]]; then
  BETTERLEAKS_PATH="$HOME/.local/bin/betterleaks"
  add_tool "betterleaks"
elif [[ -x "/usr/local/bin/betterleaks" ]]; then
  BETTERLEAKS_PATH="/usr/local/bin/betterleaks"
  add_tool "betterleaks"
elif [[ -x "/opt/homebrew/bin/betterleaks" ]]; then
  BETTERLEAKS_PATH="/opt/homebrew/bin/betterleaks"
  add_tool "betterleaks"
fi

if [[ -n "$RTK_PATH" ]]; then
  RTK_VERSION=$("$RTK_PATH" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || printf '%s' "unknown")
  if "$RTK_PATH" gain --help >/dev/null 2>&1; then
    RTK_GAIN_AVAILABLE=true
  fi
fi

# Report runtime info
if [[ ${#RUNTIME_INFO[@]} -gt 0 ]]; then
  echo "✓ Runtime: ${RUNTIME_INFO[*]}"
fi

echo "✓ Hook mode: $HOOK_MODE"

if [[ ${#STACK[@]} -gt 0 ]]; then
  echo "✓ Stack: ${STACK[*]}"
fi

if [[ ${#TOOLS[@]} -gt 0 ]]; then
  echo "✓ Tools: ${TOOLS[*]}"
fi

if [[ "$VERIFY_COMPOSITE_AVAILABLE" == "true" && -n "$VERIFY_COMPOSITE_COMMAND" ]]; then
  echo "✓ Verify wrapper: ${VERIFY_COMPOSITE_COMMAND}"
fi

if [[ ${#RUNTIME_INFO[@]} -eq 0 && ${#STACK[@]} -eq 0 ]]; then
  echo "○ Ruby plugin loaded — minimal stack detected"
fi

# Export runtime environment to file for other scripts
RUNTIME_ENV_FILE="${CLAUDE_DIR}/.runtime_env"
[[ ! -L "$CLAUDE_DIR" ]] || exit 0
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
  emit_shell_assignment "HOOK_MODE" "$HOOK_MODE"
  [[ -n "$RUBY_VERSION" ]] && emit_shell_assignment "RUBY_VERSION" "$RUBY_VERSION"
  [[ -n "$RAILS_VERSION" ]] && emit_shell_assignment "RAILS_VERSION" "$RAILS_VERSION"
  [[ -n "$ACTIVERECORD_VERSION" ]] && emit_shell_assignment "ACTIVERECORD_VERSION" "$ACTIVERECORD_VERSION"
  [[ -n "$SEQUEL_VERSION" ]] && emit_shell_assignment "SEQUEL_VERSION" "$SEQUEL_VERSION"
  [[ ${#STACK[@]} -gt 0 ]] && emit_shell_assignment "STACK_GEMS" "${STACK[*]}"
  [[ -n "$DETECTED_ORMS" ]] && emit_shell_assignment "DETECTED_ORMS" "$DETECTED_ORMS"
  emit_shell_assignment "PRIMARY_ORM" "$PRIMARY_ORM"
  emit_shell_assignment "RAILS_COMPONENTS" "$RAILS_COMPONENTS"
  emit_shell_assignment "FULL_RAILS_APP" "$FULL_RAILS_APP"
  emit_shell_assignment "PACKAGE_LAYOUT" "$PACKAGE_LAYOUT"
  [[ -n "$PACKAGE_LOCATIONS" ]] && emit_shell_assignment "PACKAGE_LOCATIONS" "$PACKAGE_LOCATIONS"
  emit_shell_assignment "PACKAGE_QUERY_NEEDED" "$PACKAGE_QUERY_NEEDED"
  emit_shell_assignment "HAS_PACKWERK" "$HAS_PACKWERK"
  [[ ${#TOOLS[@]} -gt 0 ]] && emit_shell_assignment "TOOLS" "${TOOLS[*]}"

  # Tool availability booleans
  if [[ "$TIDEWAVE_GEM_PRESENT" == "true" ]]; then
    emit_shell_assignment "TIDEWAVE_GEM_PRESENT" "true"
    emit_shell_assignment "TIDEWAVE_PROJECT_CAPABLE" "true"
  else
    emit_shell_assignment "TIDEWAVE_GEM_PRESENT" "false"
    emit_shell_assignment "TIDEWAVE_PROJECT_CAPABLE" "false"
  fi

  if [[ " ${TOOLS[*]} " =~ " rtk " ]]; then
    emit_shell_assignment "RTK_AVAILABLE" "true"
    [[ -n "$RTK_PATH" ]] && emit_shell_assignment "RTK_PATH" "$RTK_PATH"
    [[ -n "$RTK_VERSION" ]] && emit_shell_assignment "RTK_VERSION" "$RTK_VERSION"
    if [[ "$RTK_GAIN_AVAILABLE" == "true" ]]; then
      emit_shell_assignment "RTK_GAIN_AVAILABLE" "true"
    else
      emit_shell_assignment "RTK_GAIN_AVAILABLE" "false"
    fi
  else
    emit_shell_assignment "RTK_AVAILABLE" "false"
  fi

  if [[ -n "$BETTERLEAKS_PATH" ]]; then
    emit_shell_assignment "BETTERLEAKS_AVAILABLE" "true"
    emit_shell_assignment "BETTERLEAKS_PATH" "$BETTERLEAKS_PATH"
  else
    emit_shell_assignment "BETTERLEAKS_AVAILABLE" "false"
  fi

  if [[ "$STANDARDRB_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "STANDARDRB_AVAILABLE" "true"
    [[ -n "$STANDARDRB_VERSION" ]] && emit_shell_assignment "STANDARDRB_VERSION" "$STANDARDRB_VERSION"
  else
    emit_shell_assignment "STANDARDRB_AVAILABLE" "false"
  fi

  if [[ "$RUBOCOP_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "RUBOCOP_AVAILABLE" "true"
    [[ -n "$RUBOCOP_VERSION" ]] && emit_shell_assignment "RUBOCOP_VERSION" "$RUBOCOP_VERSION"
  else
    emit_shell_assignment "RUBOCOP_AVAILABLE" "false"
  fi

  if [[ "$BRAKEMAN_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "BRAKEMAN_AVAILABLE" "true"
    [[ -n "$BRAKEMAN_VERSION" ]] && emit_shell_assignment "BRAKEMAN_VERSION" "$BRAKEMAN_VERSION"
  else
    emit_shell_assignment "BRAKEMAN_AVAILABLE" "false"
  fi

  if [[ "$PRONTO_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "PRONTO_AVAILABLE" "true"
    [[ -n "$PRONTO_VERSION" ]] && emit_shell_assignment "PRONTO_VERSION" "$PRONTO_VERSION"
  else
    emit_shell_assignment "PRONTO_AVAILABLE" "false"
  fi

  if [[ "$LEFTHOOK_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "LEFTHOOK_AVAILABLE" "true"
    [[ -n "$LEFTHOOK_VERSION" ]] && emit_shell_assignment "LEFTHOOK_VERSION" "$LEFTHOOK_VERSION"
    [[ -n "$LEFTHOOK_COMMAND" ]] && emit_shell_assignment "LEFTHOOK_COMMAND" "$LEFTHOOK_COMMAND"
  else
    emit_shell_assignment "LEFTHOOK_AVAILABLE" "false"
  fi

  if [[ "$LEFTHOOK_CONFIG_PRESENT" == "true" ]]; then
    emit_shell_assignment "LEFTHOOK_CONFIG_PRESENT" "true"
    emit_shell_assignment "LEFTHOOK_CONFIG_PATH" "$LEFTHOOK_CONFIG_PATH"
  else
    emit_shell_assignment "LEFTHOOK_CONFIG_PRESENT" "false"
  fi

  emit_shell_assignment "LEFTHOOK_LINT_COVERED" "$LEFTHOOK_LINT_COVERED"
  emit_shell_assignment "LEFTHOOK_DIFF_LINT_COVERED" "$LEFTHOOK_DIFF_LINT_COVERED"
  emit_shell_assignment "LEFTHOOK_SECURITY_COVERED" "$LEFTHOOK_SECURITY_COVERED"
  emit_shell_assignment "LEFTHOOK_LINT_SECURITY_COVERED" "$LEFTHOOK_LINT_SECURITY_COVERED"
  emit_shell_assignment "LEFTHOOK_PRONTO_COVERED" "$LEFTHOOK_PRONTO_COVERED"

  if [[ "$VERIFY_COMPOSITE_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "VERIFY_COMPOSITE_AVAILABLE" "true"
    [[ -n "$VERIFY_COMPOSITE_COMMAND" ]] && emit_shell_assignment "VERIFY_COMPOSITE_COMMAND" "$VERIFY_COMPOSITE_COMMAND"
    [[ -n "$VERIFY_COMPOSITE_SOURCE" ]] && emit_shell_assignment "VERIFY_COMPOSITE_SOURCE" "$VERIFY_COMPOSITE_SOURCE"
  else
    emit_shell_assignment "VERIFY_COMPOSITE_AVAILABLE" "false"
  fi

  if [[ "$PSQL_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "PSQL_AVAILABLE" "true"
  else
    emit_shell_assignment "PSQL_AVAILABLE" "false"
  fi

  if [[ "$REDIS_CLI_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "REDIS_CLI_AVAILABLE" "true"
  else
    emit_shell_assignment "REDIS_CLI_AVAILABLE" "false"
  fi

  # Ruby tool availability
  if [[ "$BUNDLE_AVAILABLE" == "true" ]]; then
    emit_shell_assignment "BUNDLE_AVAILABLE" "true"
  else
    emit_shell_assignment "BUNDLE_AVAILABLE" "false"
  fi
} > "$TMP_RUNTIME_ENV"

mv -f -- "$TMP_RUNTIME_ENV" "$RUNTIME_ENV_FILE" || exit 0
trap - EXIT HUP INT TERM
