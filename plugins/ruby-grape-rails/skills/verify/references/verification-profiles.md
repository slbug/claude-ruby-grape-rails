# Verification Profiles

Use these profiles as canonical examples for CI, pre-release checks, and fast
local feedback loops.

## Quick Check (CI)

```bash
#!/bin/bash
# Example workflow step in your app repo: .github/workflows/ruby.yml or similar

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
RUNTIME_ENV_FILE="$REPO_ROOT/.claude/.runtime_env"
cd "$REPO_ROOT"

runtime_flag() {
  local key="$1"
  [[ -f "$RUNTIME_ENV_FILE" && ! -L "$RUNTIME_ENV_FILE" ]] || return 0
  grep -E "^${key}=" "$RUNTIME_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

find_first_repo_file() {
  local candidate

  for candidate in "$@"; do
    if [[ -f "$REPO_ROOT/$candidate" && ! -L "$REPO_ROOT/$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

gem_or_lock_has() {
  local gem_name="$1"
  grep -Eq "gem ['\"]${gem_name}['\"]|^[[:space:]]{4}${gem_name} " \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

gem_prefix_has() {
  local gem_prefix="$1"
  grep -Eq "gem ['\"]${gem_prefix}-|^[[:space:]]{4}${gem_prefix}-" \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

makefile_has_target() {
  local target_name="$1"
  local makefile_path

  makefile_path=$(find_first_repo_file GNUmakefile Makefile makefile || true)
  [[ -n "$makefile_path" ]] || return 1
  grep -Eq "^[[:space:]]*${target_name}[[:space:]]*:" "$REPO_ROOT/$makefile_path"
}

rake_task_declared() {
  local task_name="$1"

  grep -REq "task[[:space:]]*(\\(|:|['\"])${task_name}([[:space:][:punct:]]|$)|${task_name}:[[:space:]]" \
    "$REPO_ROOT/Rakefile" "$REPO_ROOT/lib/tasks" 2>/dev/null
}

justfile_has_recipe() {
  local recipe_name="$1"
  local justfile_path

  justfile_path=$(find_first_repo_file justfile .justfile Justfile || true)
  [[ -n "$justfile_path" ]] || return 1
  grep -Eq "^[[:space:]]*${recipe_name}[[:space:]]*:" "$REPO_ROOT/$justfile_path"
}

detect_verify_composite() {
  local candidate

  for candidate in bin/check bin/ci bin/verify script/check script/ci script/verify; do
    if [[ -f "$REPO_ROOT/$candidate" && ! -L "$REPO_ROOT/$candidate" ]]; then
      printf './%s\n' "$candidate"
      return 0
    fi
  done

  if makefile_has_target ci; then
    echo "make ci"
    return 0
  fi

  if makefile_has_target check; then
    echo "make check"
    return 0
  fi

  if makefile_has_target verify; then
    echo "make verify"
    return 0
  fi

  if justfile_has_recipe ci; then
    echo "just ci"
    return 0
  fi

  if justfile_has_recipe check; then
    echo "just check"
    return 0
  fi

  if justfile_has_recipe verify; then
    echo "just verify"
    return 0
  fi

  if rake_task_declared ci; then
    echo "bundle exec rake ci"
    return 0
  fi

  if rake_task_declared check; then
    echo "bundle exec rake check"
    return 0
  fi

  if rake_task_declared verify; then
    echo "bundle exec rake verify"
    return 0
  fi

  return 1
}

wrapper_failure_is_fallback() {
  grep -Eq '(^[^:]+: .*: command not found$)|(^[^:]+: .*: No such file or directory$)|(^[^:]+: .*: Permission denied$)|(^make(\[[0-9]+\])?: \*\*\* No rule to make target)|(^make(\[[0-9]+\])?: \*\*\* Don'\''t know how to build target)|(^rake aborted! Don'\''t know how to build task)|(^Could not find command )|(^Could not find gem )|(^bundler: command not found: )|(^bundle: command not found: )'
}

FULL_RAILS_APP=$(runtime_flag FULL_RAILS_APP)
STANDARDRB_AVAILABLE=$(runtime_flag STANDARDRB_AVAILABLE)
RUBOCOP_AVAILABLE=$(runtime_flag RUBOCOP_AVAILABLE)
BRAKEMAN_AVAILABLE=$(runtime_flag BRAKEMAN_AVAILABLE)
PRONTO_AVAILABLE=$(runtime_flag PRONTO_AVAILABLE)
VERIFY_COMPOSITE_HINT=$(runtime_flag VERIFY_COMPOSITE_AVAILABLE)

if [[ ! -f "$RUNTIME_ENV_FILE" || -L "$RUNTIME_ENV_FILE" ]]; then
  echo "Runtime cache missing, falling back to repo detection."
fi

if [[ -z "$FULL_RAILS_APP" ]]; then
  if [[ -f "$REPO_ROOT/bin/rails" && ! -L "$REPO_ROOT/bin/rails" ]] || \
     [[ -f "$REPO_ROOT/script/rails" && ! -L "$REPO_ROOT/script/rails" ]] || \
     { [[ -f "$REPO_ROOT/config/application.rb" && ! -L "$REPO_ROOT/config/application.rb" ]] && \
       [[ -f "$REPO_ROOT/config/environment.rb" && ! -L "$REPO_ROOT/config/environment.rb" ]] && \
       [[ -f "$REPO_ROOT/config/boot.rb" && ! -L "$REPO_ROOT/config/boot.rb" ]] && \
       [[ -d "$REPO_ROOT/app" && ! -L "$REPO_ROOT/app" ]] && \
       [[ -d "$REPO_ROOT/config/environments" && ! -L "$REPO_ROOT/config/environments" ]]; }; then
    FULL_RAILS_APP=true
  else
    FULL_RAILS_APP=false
  fi
fi

if [[ -z "$STANDARDRB_AVAILABLE" ]] && gem_or_lock_has standard; then
  STANDARDRB_AVAILABLE=true
fi

if [[ -z "$RUBOCOP_AVAILABLE" ]]; then
  if gem_or_lock_has rubocop || gem_prefix_has rubocop; then
    RUBOCOP_AVAILABLE=true
  fi
fi

if [[ -z "$BRAKEMAN_AVAILABLE" ]] && gem_or_lock_has brakeman; then
  BRAKEMAN_AVAILABLE=true
fi

if [[ -z "$PRONTO_AVAILABLE" ]]; then
  if gem_or_lock_has pronto || gem_prefix_has pronto; then
    PRONTO_AVAILABLE=true
  fi
fi

VERIFY_COMPOSITE_COMMAND=$(detect_verify_composite || true)
if [[ -n "$VERIFY_COMPOSITE_COMMAND" ]]; then
  VERIFY_COMPOSITE_AVAILABLE=true
else
  VERIFY_COMPOSITE_AVAILABLE=false
  if [[ "$VERIFY_COMPOSITE_HINT" == "true" ]]; then
    echo "Runtime cache suggested a project-native verification wrapper, but no supported wrapper was re-detected from the working tree."
  fi
fi

if [[ "$VERIFY_COMPOSITE_AVAILABLE" == "true" && -n "$VERIFY_COMPOSITE_COMMAND" ]]; then
  echo "=== Project-native Verification ==="
  echo "Trying: $VERIFY_COMPOSITE_COMMAND"

  WRAPPER_LOG=$(mktemp "${TMPDIR:-/tmp}/rb-verify-wrapper.XXXXXX")
  trap 'rm -f -- "${WRAPPER_LOG:?}"' EXIT

  set +e
  bash -lc "$VERIFY_COMPOSITE_COMMAND" 2>&1 | tee "$WRAPPER_LOG"
  WRAPPER_STATUS=${PIPESTATUS[0]}
  set -e

  if [[ $WRAPPER_STATUS -eq 0 ]]; then
    exit 0
  fi

  if wrapper_failure_is_fallback < "$WRAPPER_LOG"; then
    echo "Project-native wrapper unavailable locally, falling back to direct checks."
  else
    exit "$WRAPPER_STATUS"
  fi
fi

echo "=== Zeitwerk Check ==="
if [[ "$FULL_RAILS_APP" == "true" ]]; then
  bundle exec rails zeitwerk:check
fi

echo "=== Linting ==="
if [[ "$STANDARDRB_AVAILABLE" == "true" ]]; then
  bundle exec standardrb
elif [[ "$RUBOCOP_AVAILABLE" == "true" ]]; then
  bundle exec rubocop
fi

echo "=== Security ==="
if [[ "$BRAKEMAN_AVAILABLE" == "true" ]]; then
  bundle exec brakeman -q -w2 --no-pager
fi

echo "=== Tests ==="
if [[ -d "spec" ]]; then
  bundle exec rspec --format progress
elif [[ -d "test" ]]; then
  if [[ "$FULL_RAILS_APP" == "true" ]]; then
    bundle exec rails test
  else
    bundle exec rake test
  fi
else
  echo "No spec/ or test/ directory found, skipping tests."
fi

echo "=== Diff Review (optional) ==="
if [[ "$PRONTO_AVAILABLE" == "true" ]]; then
  eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref 2>/dev/null)" || true
  if [[ -n "$BASE_REF" ]]; then
    MERGE_BASE=$(git merge-base HEAD "$BASE_REF" 2>/dev/null || echo "$BASE_REF")
    if ! bundle exec pronto run -c "$MERGE_BASE"; then
      echo "Pronto diff review reported issues (non-blocking); review the output above."
    fi
  else
    echo "No suitable base ref found for Pronto diff review, skipping."
  fi
else
  echo "Pronto not available, skipping diff review."
fi
```

## Full Verification

```bash
#!/bin/bash
# Pre-commit or release check

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
RUNTIME_ENV_FILE="$REPO_ROOT/.claude/.runtime_env"
cd "$REPO_ROOT"

runtime_flag() {
  local key="$1"
  [[ -f "$RUNTIME_ENV_FILE" && ! -L "$RUNTIME_ENV_FILE" ]] || return 0
  grep -E "^${key}=" "$RUNTIME_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

find_first_repo_file() {
  local candidate

  for candidate in "$@"; do
    if [[ -f "$REPO_ROOT/$candidate" && ! -L "$REPO_ROOT/$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

gem_or_lock_has() {
  local gem_name="$1"
  grep -Eq "gem ['\"]${gem_name}['\"]|^[[:space:]]{4}${gem_name} " \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

gem_prefix_has() {
  local gem_prefix="$1"
  grep -Eq "gem ['\"]${gem_prefix}-|^[[:space:]]{4}${gem_prefix}-" \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

makefile_has_target() {
  local target_name="$1"
  local makefile_path

  makefile_path=$(find_first_repo_file GNUmakefile Makefile makefile || true)
  [[ -n "$makefile_path" ]] || return 1
  grep -Eq "^[[:space:]]*${target_name}[[:space:]]*:" "$REPO_ROOT/$makefile_path"
}

rake_task_declared() {
  local task_name="$1"

  grep -REq "task[[:space:]]*(\\(|:|['\"])${task_name}([[:space:][:punct:]]|$)|${task_name}:[[:space:]]" \
    "$REPO_ROOT/Rakefile" "$REPO_ROOT/lib/tasks" 2>/dev/null
}

justfile_has_recipe() {
  local recipe_name="$1"
  local justfile_path

  justfile_path=$(find_first_repo_file justfile .justfile Justfile || true)
  [[ -n "$justfile_path" ]] || return 1
  grep -Eq "^[[:space:]]*${recipe_name}[[:space:]]*:" "$REPO_ROOT/$justfile_path"
}

detect_verify_composite() {
  local candidate

  for candidate in bin/check bin/ci bin/verify script/check script/ci script/verify; do
    if [[ -f "$REPO_ROOT/$candidate" && ! -L "$REPO_ROOT/$candidate" ]]; then
      printf './%s\n' "$candidate"
      return 0
    fi
  done

  if makefile_has_target ci; then
    echo "make ci"
    return 0
  fi

  if makefile_has_target check; then
    echo "make check"
    return 0
  fi

  if makefile_has_target verify; then
    echo "make verify"
    return 0
  fi

  if justfile_has_recipe ci; then
    echo "just ci"
    return 0
  fi

  if justfile_has_recipe check; then
    echo "just check"
    return 0
  fi

  if justfile_has_recipe verify; then
    echo "just verify"
    return 0
  fi

  if rake_task_declared ci; then
    echo "bundle exec rake ci"
    return 0
  fi

  if rake_task_declared check; then
    echo "bundle exec rake check"
    return 0
  fi

  if rake_task_declared verify; then
    echo "bundle exec rake verify"
    return 0
  fi

  return 1
}

wrapper_failure_is_fallback() {
  grep -Eq '(^[^:]+: .*: command not found$)|(^[^:]+: .*: No such file or directory$)|(^[^:]+: .*: Permission denied$)|(^make(\[[0-9]+\])?: \*\*\* No rule to make target)|(^make(\[[0-9]+\])?: \*\*\* Don'\''t know how to build target)|(^rake aborted! Don'\''t know how to build task)|(^Could not find command )|(^Could not find gem )|(^bundler: command not found: )|(^bundle: command not found: )'
}

FULL_RAILS_APP=$(runtime_flag FULL_RAILS_APP)
STANDARDRB_AVAILABLE=$(runtime_flag STANDARDRB_AVAILABLE)
RUBOCOP_AVAILABLE=$(runtime_flag RUBOCOP_AVAILABLE)
BRAKEMAN_AVAILABLE=$(runtime_flag BRAKEMAN_AVAILABLE)
PRONTO_AVAILABLE=$(runtime_flag PRONTO_AVAILABLE)
VERIFY_COMPOSITE_HINT=$(runtime_flag VERIFY_COMPOSITE_AVAILABLE)

if [[ ! -f "$RUNTIME_ENV_FILE" || -L "$RUNTIME_ENV_FILE" ]]; then
  echo "Runtime cache missing, falling back to repo detection."
fi

if [[ -z "$FULL_RAILS_APP" ]]; then
  if [[ -f "$REPO_ROOT/bin/rails" && ! -L "$REPO_ROOT/bin/rails" ]] || \
     [[ -f "$REPO_ROOT/script/rails" && ! -L "$REPO_ROOT/script/rails" ]] || \
     { [[ -f "$REPO_ROOT/config/application.rb" && ! -L "$REPO_ROOT/config/application.rb" ]] && \
       [[ -f "$REPO_ROOT/config/environment.rb" && ! -L "$REPO_ROOT/config/environment.rb" ]] && \
       [[ -f "$REPO_ROOT/config/boot.rb" && ! -L "$REPO_ROOT/config/boot.rb" ]] && \
       [[ -d "$REPO_ROOT/app" && ! -L "$REPO_ROOT/app" ]] && \
       [[ -d "$REPO_ROOT/config/environments" && ! -L "$REPO_ROOT/config/environments" ]]; }; then
    FULL_RAILS_APP=true
  else
    FULL_RAILS_APP=false
  fi
fi

if [[ -z "$STANDARDRB_AVAILABLE" ]] && gem_or_lock_has standard; then
  STANDARDRB_AVAILABLE=true
fi

if [[ -z "$RUBOCOP_AVAILABLE" ]]; then
  if gem_or_lock_has rubocop || gem_prefix_has rubocop; then
    RUBOCOP_AVAILABLE=true
  fi
fi

if [[ -z "$BRAKEMAN_AVAILABLE" ]] && gem_or_lock_has brakeman; then
  BRAKEMAN_AVAILABLE=true
fi

if [[ -z "$PRONTO_AVAILABLE" ]]; then
  if gem_or_lock_has pronto || gem_prefix_has pronto; then
    PRONTO_AVAILABLE=true
  fi
fi

VERIFY_COMPOSITE_COMMAND=$(detect_verify_composite || true)
if [[ -n "$VERIFY_COMPOSITE_COMMAND" ]]; then
  VERIFY_COMPOSITE_AVAILABLE=true
else
  VERIFY_COMPOSITE_AVAILABLE=false
  if [[ "$VERIFY_COMPOSITE_HINT" == "true" ]]; then
    echo "Runtime cache suggested a project-native verification wrapper, but no supported wrapper was re-detected from the working tree."
  fi
fi

if [[ "$VERIFY_COMPOSITE_AVAILABLE" == "true" && -n "$VERIFY_COMPOSITE_COMMAND" ]]; then
  echo "0/7 Project-native Verification..."
  echo "Trying: $VERIFY_COMPOSITE_COMMAND"

  WRAPPER_LOG=$(mktemp "${TMPDIR:-/tmp}/rb-verify-wrapper.XXXXXX")
  trap 'rm -f -- "${WRAPPER_LOG:?}"' EXIT

  set +e
  bash -lc "$VERIFY_COMPOSITE_COMMAND" 2>&1 | tee "$WRAPPER_LOG"
  WRAPPER_STATUS=${PIPESTATUS[0]}
  set -e

  if [[ $WRAPPER_STATUS -eq 0 ]]; then
    echo "✅ Project-native verification wrapper passed!"
    exit 0
  fi

  if wrapper_failure_is_fallback < "$WRAPPER_LOG"; then
    echo "Project-native wrapper unavailable locally, falling back to direct checks."
  else
    exit "$WRAPPER_STATUS"
  fi
fi

echo "1/7 Zeitwerk Check..."
if [[ "$FULL_RAILS_APP" == "true" ]]; then
  bundle exec rails zeitwerk:check
fi

echo "2/7 Linting..."
if [[ "$STANDARDRB_AVAILABLE" == "true" ]]; then
  bundle exec standardrb --format progress
elif [[ "$RUBOCOP_AVAILABLE" == "true" ]]; then
  bundle exec rubocop
fi

echo "3/7 Security Scan..."
if [[ "$BRAKEMAN_AVAILABLE" == "true" ]]; then
  bundle exec brakeman -q --no-pager
fi

echo "4/7 Type Check..."
if [[ -f "$REPO_ROOT/sorbet/config" ]] || gem_or_lock_has sorbet || gem_prefix_has sorbet; then
  bundle exec srb tc
else
  echo "No Sorbet configured"
fi

echo "5/7 Database..."
if [[ "$FULL_RAILS_APP" == "true" ]]; then
  bundle exec rails db:migrate:status
else
  echo "Non-Rails project detected, skipping database migration status."
fi

echo "6/7 Tests..."
if [[ -d "spec" ]]; then
  bundle exec rspec --format documentation
elif [[ -d "test" ]]; then
  if [[ "$FULL_RAILS_APP" == "true" ]]; then
    bundle exec rails test
  else
    bundle exec rake test
  fi
else
  echo "No spec/ or test/ directory found, skipping tests."
fi

echo "7/7 Diff Review (optional)..."
if [[ "$PRONTO_AVAILABLE" == "true" ]]; then
  eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref 2>/dev/null)" || true
  if [[ -n "$BASE_REF" ]]; then
    MERGE_BASE=$(git merge-base HEAD "$BASE_REF" 2>/dev/null || echo "$BASE_REF")
    if ! bundle exec pronto run -c "$MERGE_BASE"; then
      echo "Pronto diff review reported issues (non-blocking); review the output above."
    fi
  else
    echo "No suitable base ref found for Pronto diff review, skipping."
  fi
else
  echo "Pronto not available, skipping diff review."
fi

echo "✅ All checks passed!"
```

## Fast Feedback (Development)

```bash
# While iterating on code - skip heavy checks
bundle exec standardrb --fix && \
  bundle exec rspec spec/models/user_spec.rb
```
