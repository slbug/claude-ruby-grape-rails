#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'yaml'

DEFAULT_YAML_SOURCE = File.expand_path('../plugins/ruby-grape-rails/references/iron-laws.yml', __dir__)
YAML_SOURCE = ENV.fetch('RUBY_PLUGIN_IRON_LAWS_YAML', DEFAULT_YAML_SOURCE)

unless File.exist?(YAML_SOURCE)
  puts "Error: YAML source not found: #{YAML_SOURCE}"
  exit 1
end

yaml_raw = File.read(YAML_SOURCE)
yaml = YAML.safe_load(
  yaml_raw,
  permitted_classes: [],
  permitted_symbols: [],
  aliases: false
)

required_keys = %w[version last_updated total_laws categories laws]
missing_keys = required_keys.reject { |key| yaml.is_a?(Hash) && yaml.key?(key) }
unless missing_keys.empty?
  warn "Error: YAML source missing required keys: #{missing_keys.join(', ')}"
  exit 1
end

unless yaml['categories'].is_a?(Array) && yaml['laws'].is_a?(Array)
  warn "Error: Invalid Iron Laws YAML structure in #{YAML_SOURCE}"
  exit 1
end

def validate_entries!(yaml)
  category_required = %w[id name law_count]
  law_required = %w[id category title rule summary_text rationale subagent_text]
  category_ids = yaml['categories'].filter_map { |category| category['id'] if category.is_a?(Hash) }
  law_ids = yaml['laws'].filter_map { |law| law['id'] if law.is_a?(Hash) }
  category_totals = Hash.new(0)
  errors = []

  yaml['categories'].each_with_index do |category, index|
    unless category.is_a?(Hash)
      errors << "category[#{index}] must be a mapping, got #{category.class}"
      next
    end

    missing = category_required.reject { |key| category[key] }
    next if missing.empty?

    errors << "category[#{index}] missing: #{missing.join(', ')}"
  end

  yaml['laws'].each_with_index do |law, index|
    unless law.is_a?(Hash)
      errors << "law[#{index}] must be a mapping, got #{law.class}"
      next
    end

    missing = law_required.reject { |key| law[key] }
    errors << "law[#{index}] missing: #{missing.join(', ')}" unless missing.empty?
    next unless law.key?('category') && law['category']
    next if category_ids.include?(law['category'])

    errors << "law[#{index}] references unknown category: #{law['category'].inspect}"
  end

  duplicate_category_ids = category_ids.group_by(&:itself).select { |_id, entries| entries.length > 1 }.keys.sort
  duplicate_law_ids = law_ids.group_by(&:itself).select { |_id, entries| entries.length > 1 }.keys.sort
  errors << "duplicate category ids: #{duplicate_category_ids.join(', ')}" unless duplicate_category_ids.empty?
  errors << "duplicate law ids: #{duplicate_law_ids.join(', ')}" unless duplicate_law_ids.empty?

  if yaml['total_laws'].to_i != yaml['laws'].length
    errors << "total_laws=#{yaml['total_laws']} does not match actual laws count=#{yaml['laws'].length}"
  end

  yaml['laws'].each do |law|
    next unless law.is_a?(Hash) && law['category']

    category_totals[law['category']] += 1
  end

  yaml['categories'].each_with_index do |category, index|
    next unless category.is_a?(Hash) && category['id']

    declared_count = category['law_count'].to_i
    actual_count = category_totals[category['id']]
    next if declared_count == actual_count

    errors << "category[#{index}] #{category['id'].inspect} law_count=#{category['law_count']} does not match actual count=#{actual_count}"
  end

  return if errors.empty?

  warn "Error: Invalid Iron Laws YAML entries in #{YAML_SOURCE}"
  errors.each { |error| warn "  - #{error}" }
  exit 1
end

validate_entries!(yaml)

def law_count_label(count)
  "#{count} #{count == 1 ? 'law' : 'laws'}"
end

# Generate injectable template section
def generate_injectable_section(yaml)
  puts '## IRON LAWS — STOP if violated'
  puts ''
  puts 'If code would violate ANY of these, you MUST:'
  puts ''
  puts '1. STOP immediately'
  puts '2. Show the problematic code'
  puts '3. Show the correct pattern'
  puts '4. Ask permission to apply the fix'
  puts ''

  yaml['categories'].each do |cat|
    puts "**#{cat['name']}:**"
    puts ''
    yaml['laws'].select { |l| l['category'] == cat['id'] }.each_with_index do |law, idx|
      puts "#{idx + 1}. #{law['summary_text']}"
    end
    puts ''
  end
end

# Escape pipe characters for markdown tables
def escape_table_cell(text)
  text.to_s.gsub('|', '\|')
end

# Generate tutorial section
def generate_tutorial_section(yaml)
  puts "### Iron Laws (#{yaml['total_laws']} Rules, Always Enforced)"
  puts ''
  puts 'Iron Laws are non-negotiable rules that every agent enforces. If your code violates one, the plugin stops and explains before proceeding.'
  puts ''
  puts '**Key Laws:**'
  puts ''
  puts '| Law | Why |'
  puts '|-----|-----|'

  yaml['laws'].first(7).each do |law|
    puts "| #{escape_table_cell(law['title'])} | #{escape_table_cell(law['rationale'])} |"
  end
end

# Generate injector script
def generate_injector_script(yaml)
  output = "Ruby/Rails/Grape Iron Laws (NON-NEGOTIABLE) — #{yaml['total_laws']} Total:\n\n"

  yaml['categories'].each do |cat|
    output += "#{cat['name']} (#{cat['law_count']}):\n"
  end

  output += "\n"

  yaml['laws'].each do |law|
    output += "#{law['subagent_text']}\n"
  end

  payload = JSON.generate(
    'hookSpecificOutput' => {
      'hookEventName' => 'SubagentStart',
      'additionalContext' => output
    }
  )

  puts '#!/usr/bin/env bash'
  puts 'set -o nounset'
  puts 'set -o pipefail'
  puts ''
  puts '# GENERATED FROM iron-laws.yml — DO NOT EDIT'
  puts "# Source version: #{yaml['version']} (updated #{yaml['last_updated']})"
  puts ''
  puts "cat <<'EOF'"
  puts payload
  puts 'EOF'
end

# Generate canonical registry
def generate_canonical_registry(yaml)
  puts '# Iron Laws Canonical Registry'
  puts ''
  puts "**Version**: #{yaml['version']}"
  puts "**Last Updated**: #{yaml['last_updated']}"
  puts "**Total Laws**: #{yaml['total_laws']}"
  puts ''
  puts '<!-- This file is a generated projection of iron-laws.yml — DO NOT EDIT DIRECTLY -->'
  puts ''
  puts 'This file is the human-readable registry of all Iron Laws across the plugin.'
  puts 'For programmatic use, see [iron-laws.yml](../../../references/iron-laws.yml).'
  puts ''
  puts "## The #{yaml['total_laws']} Iron Laws"
  puts ''

  yaml['categories'].each do |cat|
    puts "### #{cat['name']} (#{law_count_label(cat['law_count'])})"
    puts ''
    yaml['laws'].select { |l| l['category'] == cat['id'] }.each do |law|
      puts "#{law['id']}. **#{law['title']}** — #{law['rule']}"
      puts "   *#{law['rationale']}*"
      puts ''
    end
  end

  puts '## Enforcement Tiers'
  puts ''
  puts '### Tier 1: Programmatic (Hook-Level)'
  puts ''
  puts 'Enforced automatically by iron-law-verifier.sh on every .rb file edit:'
  puts ''

  yaml['laws'].select { |l| l['detector_id'] }.each do |law|
    puts "- Law #{law['id']} (#{law['title']}) — detector: #{law['detector_id']}"
  end

  puts ''
  puts '### Tier 2: Behavioral (Agent/Context)'
  puts ''
  puts "Enforced by loading skills and agent instructions (all #{yaml['total_laws']} laws)."
  puts ''
  puts '### Tier 3: Review-Time (On-Demand)'
  puts ''
  puts 'Checked during /rb:review by specialist agents.'
  puts ''
  puts '## Update Procedure'
  puts ''
  puts 'Do not edit this file directly. Instead:'
  puts ''
  puts '1. Update plugins/ruby-grape-rails/references/iron-laws.yml'
  puts '2. Run: ./scripts/generate-iron-law-outputs.sh'
  puts '3. All projections will regenerate automatically'
end

# Generate README section
def generate_readme(yaml)
  puts "The plugin enforces **#{yaml['total_laws']} Iron Laws** that prevent common, costly mistakes:"
  puts ''
  puts '| Category | Count | Laws |'
  puts '|----------|-------|------|'

  yaml['categories'].each do |cat|
    law_names = yaml['laws']
                .select { |l| l['category'] == cat['id'] }
                .map { |l| l['summary_text'] }
                .join('; ')
    puts "| #{escape_table_cell(cat['name'])} | #{cat['law_count']} | #{escape_table_cell(law_names)} |"
  end

  puts ''
  puts '### Enforcement'
  puts ''
  programmatic_count = yaml['laws'].filter_map { |law| law['detector_id'] }.uniq.count
  puts "- **Programmatic**: #{programmatic_count} programmatic detectors checked automatically on targeted Ruby-ish edits"
  puts "- **Behavioral**: All #{yaml['total_laws']} laws injected into subagent context"
  puts '- **Review-time**: Full audit during `/rb:review`'
  puts ''
  puts 'See [full registry](plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md) for details.'
end

# Generate iron-law-judge.md Iron Laws Overview section
def generate_judge_section(yaml)
  puts "These are the #{yaml['total_laws']} non-negotiable Iron Laws. Any violation must be flagged."
  puts ''

  yaml['categories'].each do |cat|
    puts "### #{cat['name']} (#{law_count_label(cat['law_count'])})"
    puts ''
    yaml['laws'].select { |l| l['category'] == cat['id'] }.each do |law|
      puts "#{law['id']}. **#{law['title']}** — #{law['rule']}"
    end
    puts ''
  end
end

# Main
case ARGV[0]
when 'injectable'
  generate_injectable_section(yaml)
when 'tutorial'
  generate_tutorial_section(yaml)
when 'injector'
  generate_injector_script(yaml)
when 'canonical'
  generate_canonical_registry(yaml)
when 'readme'
  generate_readme(yaml)
when 'judge'
  generate_judge_section(yaml)
else
  puts "Usage: #{$PROGRAM_NAME} [injectable|tutorial|injector|canonical|readme|judge]"
  exit 1
end
