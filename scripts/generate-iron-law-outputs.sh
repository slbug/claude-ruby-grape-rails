#!/usr/bin/env bash
#
# Generate Iron Law outputs from canonical YAML source
# Usage: ./scripts/generate-iron-law-outputs.sh [target]
#   target: optional specific target to regenerate
#           (readme|claude|canonical|init|tutorial|injector|judge|all)
#
# This script delegates to generate-iron-law-content.rb for actual content generation
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUBY_SCRIPT="${SCRIPT_DIR}/generate-iron-law-content.rb"
YAML_SOURCE="${REPO_ROOT}/plugins/ruby-grape-rails/references/iron-laws.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
  cat <<'EOF'
Usage: ./scripts/generate-iron-law-outputs.sh [target]

Regenerate Iron Law projections from plugins/ruby-grape-rails/references/iron-laws.yml.

Targets:
  readme     Update bounded Iron Laws section in README.md
  claude     Update bounded Iron Laws section in CLAUDE.md
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
    readme|claude|canonical|init|tutorial|injector|judge|all) return 0 ;;
    *) return 1 ;;
  esac
}

# Update file with bounded replacement
update_file() {
  local file="$1"
  local content_type="$2"
  local start_marker="<!-- IRON_LAWS_START -->"
  local end_marker="<!-- IRON_LAWS_END -->"

  if [[ ! -f "$file" ]]; then
    log_error "File not found: $file"
    return 1
  fi

  if ! grep -q "$start_marker" "$file"; then
    log_warn "Markers not found in $file — skipping"
    return 0
  fi

  # Generate content using Ruby
  local new_content
  new_content=$(ruby "$RUBY_SCRIPT" "$content_type")

  # Update file using Ruby
  ruby -e '
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

    new_file_content = content.sub(pattern, replacement)

    File.write(file, new_file_content)
    puts "Updated #{file}"
  ' "$file" "$start_marker" "$end_marker" <<< "$new_content"

  log_info "Updated $file"
}

# Generate whole file (no markers)
generate_whole_file() {
  local output_file="$1"
  local content_type="$2"

  ruby "$RUBY_SCRIPT" "$content_type" > "$output_file"
  log_info "Generated $output_file"
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
    claude|all)
      log_info "Generating CLAUDE.md section..."
      update_file "${REPO_ROOT}/CLAUDE.md" "claude"
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
      chmod +x "${REPO_ROOT}/plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh"
      ;;
  esac

  case "$target" in
    judge|all)
      log_info "Generating iron-law-judge.md section..."
      # Use special markers for judge file (IRON_LAWS_JUDGE_START/END)
      local judge_file="${REPO_ROOT}/plugins/ruby-grape-rails/agents/iron-law-judge.md"
      local judge_start_marker="<!-- IRON_LAWS_JUDGE_START -->"
      local judge_end_marker="<!-- IRON_LAWS_JUDGE_END -->"

      if [[ ! -f "$judge_file" ]]; then
        log_error "File not found: $judge_file"
      elif ! grep -q "$judge_start_marker" "$judge_file"; then
        log_warn "Markers not found in $judge_file — skipping"
      else
        # Generate content using Ruby
        local judge_content
        judge_content=$(ruby "$RUBY_SCRIPT" judge)

        # Update file using Ruby
        ruby -e '
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

          new_file_content = content.sub(pattern, replacement)

          File.write(file, new_file_content)
          puts "Updated #{file}"
        ' "$judge_file" "$judge_start_marker" "$judge_end_marker" <<< "$judge_content"

        log_info "Updated $judge_file"
      fi
      ;;
  esac

  log_info "Generation complete!"
}

# Validate
if [[ ! -f "$YAML_SOURCE" ]]; then
  log_error "YAML source not found: $YAML_SOURCE"
  exit 1
fi

if [[ ! -f "$RUBY_SCRIPT" || -L "$RUBY_SCRIPT" ]]; then
  log_error "Ruby script not found: $RUBY_SCRIPT"
  exit 1
fi

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

generate_all "$TARGET"
