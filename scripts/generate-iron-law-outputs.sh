#!/usr/bin/env bash
#
# Generate Iron Law outputs from canonical YAML source
# Usage: ./scripts/generate-iron-law-outputs.sh [target]
#   target: optional specific target to regenerate
#           (readme|canonical|init|tutorial|injector|judge|all)
#
# This script delegates to generate-iron-law-content.rb for actual content generation
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT_REAL="$(cd "${REPO_ROOT}" && pwd -P)"
RUBY_SCRIPT="${SCRIPT_DIR}/generate-iron-law-content.rb"
YAML_SOURCE="${REPO_ROOT}/plugins/ruby-grape-rails/references/iron-laws.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
  printf '%b %s\n' "${GREEN}[INFO]${NC}" "$1"
}

log_warn() {
  printf '%b %s\n' "${YELLOW}[WARN]${NC}" "$1"
}

log_error() {
  printf '%b %s\n' "${RED}[ERROR]${NC}" "$1"
}

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    log_error "Required command not found: ${command_name}"
    exit 1
  fi
}

show_usage() {
  cat <<'EOF'
Usage: ./scripts/generate-iron-law-outputs.sh [target]

Regenerate Iron Law projections from plugins/ruby-grape-rails/references/iron-laws.yml.

Targets:
  readme     Update bounded Iron Laws section in README.md
  canonical  Regenerate canonical-registry.md
  init       Update bounded Iron Laws section in init injectable template
  tutorial   Update bounded Iron Laws section in intro tutorial content
  injector   Regenerate inject-iron-laws.sh
  judge      Update bounded Iron Laws section in iron-law-judge.md
  all        Regenerate all supported targets

Options:
  -h, --help Show this help
EOF
}

valid_target() {
  case "$1" in
    readme|canonical|init|tutorial|injector|judge|all) return 0 ;;
    *) return 1 ;;
  esac
}

require_command ruby
require_command grep
require_command mktemp
require_command mv
require_command chmod
require_command rm

canonicalize_dir() {
  local path="$1"
  [[ -d "$path" && ! -L "$path" ]] || return 1
  (cd "$path" >/dev/null 2>&1 && pwd -P) || return 1
}

validate_destination_path() {
  local target="$1"
  local parent_dir
  local canonical_parent

  [[ "$target" == "${REPO_ROOT}/"* ]] || {
    log_error "Destination outside repository root: $target"
    return 1
  }

  parent_dir="${target%/*}"
  canonical_parent=$(canonicalize_dir "$parent_dir") || {
    log_error "Destination parent is missing or unsafe: $parent_dir"
    return 1
  }

  [[ "$canonical_parent" == "$REPO_ROOT_REAL" || "$canonical_parent" == "${REPO_ROOT_REAL}/"* ]] || {
    log_error "Destination parent resolves outside repository root: $target"
    return 1
  }

  if [[ -e "$target" ]]; then
    [[ -f "$target" ]] || {
      log_error "Destination exists and is not a regular file: $target"
      return 1
    }
    [[ ! -L "$target" ]] || {
      log_error "Destination is a symlink (refusing to overwrite): $target"
      return 1
    }
  fi
}

safe_remove_temp_output() {
  local path="$1"
  local parent_dir="$2"

  [[ -n "$path" ]] || return 0
  [[ "$path" == "${parent_dir}/.tmp."* ]] || return 1
  [[ -f "$path" && ! -L "$path" ]] || return 1
  rm -f -- "${path:?}"
}

new_output_temp_file() {
  local target="$1"
  local parent_dir="${target%/*}"
  local base_name

  validate_destination_path "$target" || return 1
  base_name="${target##*/}"
  mktemp "${parent_dir}/.tmp.${base_name}.XXXXXX"
}

atomic_move_into_target() {
  local temp_file="$1"
  local target="$2"

  validate_destination_path "$target" || return 1
  mv -f -- "$temp_file" "$target"
}

# Update file with bounded replacement
update_file() {
  local file="$1"
  local content_type="$2"
  local start_marker="<!-- IRON_LAWS_START -->"
  local end_marker="<!-- IRON_LAWS_END -->"
  local tmp_file=""

  validate_destination_path "$file" || return 1

  if [[ ! -f "$file" ]]; then
    log_error "File not found: $file"
    return 1
  fi

  if [[ ! -r "$file" ]]; then
    log_error "File not readable: $file"
    return 1
  fi

  if ! grep -q "$start_marker" "$file" || ! grep -q "$end_marker" "$file"; then
    log_error "Bounded replacement markers not found or malformed in $file"
    return 1
  fi

  # Generate content using Ruby
  local new_content
  local ruby_exit=0
  new_content=$(ruby "$RUBY_SCRIPT" "$content_type") || ruby_exit=$?
  if [[ $ruby_exit -ne 0 ]]; then
    log_error "Failed to generate content for type: $content_type (exit $ruby_exit)"
    return 1
  fi
  tmp_file=$(new_output_temp_file "$file") || return 1

  # Update file using Ruby, then move into place atomically.
  if ! ruby -e '
    file = ARGV[0]
    start_marker = ARGV[1]
    end_marker = ARGV[2]
    new_content = STDIN.read

    content = File.read(file)

    # Find and replace bounded section
    pattern = /(#{Regexp.escape(start_marker)}).*?(#{Regexp.escape(end_marker)})/m
    unless content.match?(pattern)
      warn "Bounded replacement markers not found or malformed in #{file}"
      exit 1
    end
    replacement = "#{start_marker}\n\n<!-- GENERATED FROM iron-laws.yml — DO NOT EDIT -->\n\n#{new_content}\n#{end_marker}"

    puts content.sub(pattern, replacement)
  ' "$file" "$start_marker" "$end_marker" <<< "$new_content" > "$tmp_file"; then
    safe_remove_temp_output "$tmp_file" "${file%/*}" || true
    return 1
  fi

  if ! atomic_move_into_target "$tmp_file" "$file"; then
    safe_remove_temp_output "$tmp_file" "${file%/*}" || true
    return 1
  fi

  log_info "Updated $file"
}

# Generate whole file (no markers)
generate_whole_file() {
  local output_file="$1"
  local content_type="$2"
  local tmp_file=""

  tmp_file=$(new_output_temp_file "$output_file") || return 1
  if ! ruby "$RUBY_SCRIPT" "$content_type" > "$tmp_file"; then
    safe_remove_temp_output "$tmp_file" "${output_file%/*}" || true
    log_error "Failed to generate ${output_file}"
    return 1
  fi
  if ! atomic_move_into_target "$tmp_file" "$output_file"; then
    safe_remove_temp_output "$tmp_file" "${output_file%/*}" || true
    return 1
  fi
  log_info "Generated $output_file"
}

update_judge_file() {
  local judge_file="${REPO_ROOT}/plugins/ruby-grape-rails/agents/iron-law-judge.md"
  local judge_start_marker="<!-- IRON_LAWS_JUDGE_START -->"
  local judge_end_marker="<!-- IRON_LAWS_JUDGE_END -->"
  local judge_content
  local tmp_file=""

  validate_destination_path "$judge_file" || return 1

  if [[ ! -f "$judge_file" ]]; then
    log_error "File not found: $judge_file"
    return 1
  fi

  if [[ ! -r "$judge_file" ]]; then
    log_error "File not readable: $judge_file"
    return 1
  fi

  if ! grep -q "$judge_start_marker" "$judge_file" || ! grep -q "$judge_end_marker" "$judge_file"; then
    log_error "Bounded replacement markers not found or malformed in $judge_file"
    return 1
  fi

  local ruby_exit=0
  judge_content=$(ruby "$RUBY_SCRIPT" judge) || ruby_exit=$?
  if [[ $ruby_exit -ne 0 ]]; then
    log_error "Failed to generate judge content (exit $ruby_exit)"
    return 1
  fi
  tmp_file=$(new_output_temp_file "$judge_file") || return 1

  if ! ruby -e '
    file = ARGV[0]
    start_marker = ARGV[1]
    end_marker = ARGV[2]
    new_content = STDIN.read

    content = File.read(file)

    pattern = /(#{Regexp.escape(start_marker)}).*?(#{Regexp.escape(end_marker)})/m
    unless content.match?(pattern)
      warn "Bounded replacement markers not found or malformed in #{file}"
      exit 1
    end
    replacement = "#{start_marker}\n\n<!-- GENERATED FROM iron-laws.yml — DO NOT EDIT -->\n\n#{new_content}\n#{end_marker}"

    puts content.sub(pattern, replacement)
  ' "$judge_file" "$judge_start_marker" "$judge_end_marker" <<< "$judge_content" > "$tmp_file"; then
    safe_remove_temp_output "$tmp_file" "${judge_file%/*}" || true
    return 1
  fi

  if ! atomic_move_into_target "$tmp_file" "$judge_file"; then
    safe_remove_temp_output "$tmp_file" "${judge_file%/*}" || true
    return 1
  fi

  log_info "Updated $judge_file"
}

# Main generation
generate_all() {
  local target="${1:-all}"

  log_info "Generating Iron Law outputs from ${YAML_SOURCE}"

  case "$target" in
    readme|all)
      log_info "Generating README.md section..."
      update_file "${REPO_ROOT}/README.md" "readme"
      ;;
  esac

  case "$target" in
    canonical|all)
      log_info "Generating canonical registry..."
      generate_whole_file "${REPO_ROOT}/plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md" "canonical"
      ;;
  esac

  case "$target" in
    init|all)
      log_info "Generating init injectable template..."
      update_file "${REPO_ROOT}/plugins/ruby-grape-rails/skills/init/references/injectable-template.md" "injectable"
      ;;
  esac

  case "$target" in
    tutorial|all)
      log_info "Generating tutorial content..."
      update_file "${REPO_ROOT}/plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md" "tutorial"
      ;;
  esac

  case "$target" in
    injector|all)
      log_info "Generating injector script..."
      generate_whole_file "${REPO_ROOT}/plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh" "injector"
      validate_destination_path "${REPO_ROOT}/plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh" || return 1
      chmod +x "${REPO_ROOT}/plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh"
      ;;
  esac

  case "$target" in
    judge|all)
      log_info "Generating iron-law-judge.md section..."
      update_judge_file
      ;;
  esac

  log_info "Generation complete!"
}

# Main
TARGET="${1:-all}"

case "$TARGET" in
  -h|--help|help)
    show_usage
    exit 0
    ;;
esac

if ! valid_target "$TARGET"; then
  log_error "Unknown target: $TARGET"
  show_usage
  exit 1
fi

if [[ ! -f "$YAML_SOURCE" ]]; then
  log_error "YAML source not found: $YAML_SOURCE"
  exit 1
fi

if [[ ! -f "$RUBY_SCRIPT" ]]; then
  log_error "Ruby script not found or not a regular file: $RUBY_SCRIPT"
  exit 1
fi

if [[ -L "$RUBY_SCRIPT" ]]; then
  log_error "Ruby script symlinks are not allowed: $RUBY_SCRIPT"
  exit 1
fi

if [[ ! -r "$RUBY_SCRIPT" ]]; then
  log_error "Ruby script is not readable: $RUBY_SCRIPT"
  exit 1
fi

generate_all "$TARGET"

# Post-generation drift check: SKILL.md is not generated, so verify it matches
DRIFT_CHECK="${SCRIPT_DIR}/check-iron-law-drift.sh"
if [[ -r "$DRIFT_CHECK" ]]; then
  if ! bash "$DRIFT_CHECK"; then
    log_error "SKILL.md drift detected — update plugins/ruby-grape-rails/skills/iron-laws/SKILL.md to match iron-laws.yml"
    exit 1
  fi
fi
