#!/usr/bin/env bash
# Check that iron-laws SKILL.md rule text matches the canonical YAML source.
# Exits 0 if aligned, 1 if drift detected.
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
YAML_FILE="${REPO_ROOT}/plugins/ruby-grape-rails/references/iron-laws.yml"
SKILL_FILE="${REPO_ROOT}/plugins/ruby-grape-rails/skills/iron-laws/SKILL.md"

command -v ruby >/dev/null 2>&1 || { echo "ERROR: ruby required for iron-law drift check" >&2; exit 1; }

# Extract rules from YAML (source of truth)
YAML_RULES=$(ruby -ryaml -e '
yaml = YAML.safe_load(File.read(ARGV[0]))
yaml["laws"].each do |law|
  # Normalize: collapse whitespace, strip trailing periods
  rule = law["rule"].gsub(/\s+/, " ").strip.sub(/\.\z/, "")
  puts "#{law["id"]}|#{law["title"]}|#{rule}"
end
' "$YAML_FILE" 2>/dev/null) || { echo "ERROR: failed to parse $YAML_FILE" >&2; exit 1; }

# Extract rules from SKILL.md (may drift)
# shellcheck disable=SC2016 # $1/$2/$3 are Ruby regex captures, not shell vars
SKILL_RULES=$(ruby -e '
in_laws = false
File.readlines(ARGV[0]).each do |line|
  line = line.strip
  # Match numbered law lines: "1. **Title** — rule text"
  if line =~ /\A(\d+)\.\s+\*\*(.+?)\*\*\s+—\s+(.+)\z/
    id = $1
    title = $2
    rule = $3.gsub(/\s+/, " ").strip.sub(/\.\z/, "")
    puts "#{id}|#{title}|#{rule}"
  end
end
' "$SKILL_FILE" 2>/dev/null) || { echo "ERROR: failed to parse $SKILL_FILE" >&2; exit 1; }

DRIFT=0

# Compare each YAML rule against SKILL.md
while IFS='|' read -r id title rule; do
  skill_line=$(echo "$SKILL_RULES" | grep "^${id}|" || true)
  if [[ -z "$skill_line" ]]; then
    echo "DRIFT: Law $id ($title) missing from SKILL.md"
    DRIFT=1
    continue
  fi
  skill_rule=$(echo "$skill_line" | cut -d'|' -f3-)
  if [[ "$rule" != "$skill_rule" ]]; then
    echo "DRIFT: Law $id ($title)"
    echo "  YAML:     $rule"
    echo "  SKILL.md: $skill_rule"
    DRIFT=1
  fi
done <<< "$YAML_RULES"

# Check for extra laws in SKILL.md not in YAML
while IFS='|' read -r id title rule; do
  yaml_line=$(echo "$YAML_RULES" | grep "^${id}|" || true)
  if [[ -z "$yaml_line" ]]; then
    echo "DRIFT: Law $id ($title) in SKILL.md but not in YAML"
    DRIFT=1
  fi
done <<< "$SKILL_RULES"

if [[ "$DRIFT" -eq 0 ]]; then
  echo "Iron Laws SKILL.md is aligned with YAML source."
fi
exit "$DRIFT"
