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

# Shared validation helpers used by both iron-laws and preferences validators.
def blank_string?(value)
  value.is_a?(String) && value.strip.empty?
end

def nonblank_string?(value)
  value.is_a?(String) && !value.strip.empty?
end

def integer_value(value)
  return value if value.is_a?(Integer)
  return nil unless value.is_a?(String)

  stripped = value.strip
  return nil unless stripped.match?(/\A\d+\z/)

  stripped.to_i
end

def integerish?(value)
  !integer_value(value).nil?
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

    missing = category_required.reject { |key| category.key?(key) && !category[key].nil? }
    errors << "category[#{index}] missing: #{missing.join(', ')}" unless missing.empty?
    next unless missing.empty?

    %w[id name].each do |key|
      value = category[key]
      next if nonblank_string?(value)

      if blank_string?(value)
        errors << "category[#{index}] #{key} must not be blank"
      else
        errors << "category[#{index}] #{key} must be a non-blank String"
      end
    end

    unless integerish?(category['law_count'])
      errors << "category[#{index}] law_count must be an integer"
    end
  end

  yaml['laws'].each_with_index do |law, index|
    unless law.is_a?(Hash)
      errors << "law[#{index}] must be a mapping, got #{law.class}"
      next
    end

    missing = law_required.reject { |key| law.key?(key) && !law[key].nil? }
    errors << "law[#{index}] missing: #{missing.join(', ')}" unless missing.empty?
    if missing.empty?
      unless law['id'].is_a?(Integer) || nonblank_string?(law['id'])
        if blank_string?(law['id'])
          errors << "law[#{index}] id must not be blank"
        else
          errors << "law[#{index}] id must be an Integer or non-blank String"
        end
      end

      %w[category title rule summary_text rationale subagent_text].each do |key|
        value = law[key]
        next if nonblank_string?(value)

        if blank_string?(value)
          errors << "law[#{index}] #{key} must not be blank"
        else
          errors << "law[#{index}] #{key} must be a non-blank String"
        end
      end
    end

    next unless law.key?('category') && law['category']
    next if category_ids.include?(law['category'])

    errors << "law[#{index}] references unknown category: #{law['category'].inspect}"
  end

  duplicate_category_ids = category_ids.group_by(&:itself).select { |_id, entries| entries.length > 1 }.keys.sort
  duplicate_law_ids = law_ids.group_by(&:itself).select { |_id, entries| entries.length > 1 }.keys.sort
  errors << "duplicate category ids: #{duplicate_category_ids.join(', ')}" unless duplicate_category_ids.empty?
  errors << "duplicate law ids: #{duplicate_law_ids.join(', ')}" unless duplicate_law_ids.empty?

  total_laws = integer_value(yaml['total_laws'])
  if total_laws.nil?
    errors << 'total_laws must be an integer'
  elsif total_laws != yaml['laws'].length
    errors << "total_laws=#{yaml['total_laws']} does not match actual laws count=#{yaml['laws'].length}"
  end

  yaml['laws'].each do |law|
    next unless law.is_a?(Hash) && law['category']

    category_totals[law['category']] += 1
  end

  yaml['categories'].each_with_index do |category, index|
    next unless category.is_a?(Hash) && category['id']

    declared_count = integer_value(category['law_count'])
    next if declared_count.nil?

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

DEFAULT_PREFERENCES_YAML = File.expand_path('../plugins/ruby-grape-rails/references/preferences.yml', __dir__)
PREFERENCES_YAML = ENV.fetch('RUBY_PLUGIN_PREFERENCES_YAML', DEFAULT_PREFERENCES_YAML)

PREFERENCE_SEVERITY_ALLOWED = %w[low medium].freeze

def validate_preferences!(prefs, source_path)
  errors = []
  category_required = %w[id name]
  pref_text_required = %w[category title rule summary_text rationale subagent_text]

  # Top-level metadata — these feed generated output, so require them.
  %w[version last_updated].each do |key|
    next if nonblank_string?(prefs[key])

    if blank_string?(prefs[key])
      errors << "top-level #{key} must not be blank"
    else
      errors << "top-level #{key} must be a non-blank String"
    end
  end
  unless integerish?(prefs['total_preferences'])
    errors << 'total_preferences must be an integer'
  end

  category_ids = prefs['categories'].filter_map { |c| c['id'] if c.is_a?(Hash) }
  pref_ids = prefs['preferences'].filter_map { |p| p['id'] if p.is_a?(Hash) }
  category_totals = Hash.new(0)

  prefs['categories'].each_with_index do |cat, index|
    unless cat.is_a?(Hash)
      errors << "category[#{index}] must be a mapping, got #{cat.class}"
      next
    end

    missing = category_required.reject { |key| cat.key?(key) && !cat[key].nil? }
    errors << "category[#{index}] missing: #{missing.join(', ')}" unless missing.empty?
    next unless missing.empty?

    category_required.each do |key|
      value = cat[key]
      next if nonblank_string?(value)

      if blank_string?(value)
        errors << "category[#{index}] #{key} must not be blank"
      else
        errors << "category[#{index}] #{key} must be a non-blank String"
      end
    end

    next unless cat.key?('preference_count')
    next if integerish?(cat['preference_count'])

    errors << "category[#{index}] preference_count must be an integer"
  end

  prefs['preferences'].each_with_index do |pref, index|
    unless pref.is_a?(Hash)
      errors << "preference[#{index}] must be a mapping, got #{pref.class}"
      next
    end

    unless pref['id'].is_a?(Integer) || nonblank_string?(pref['id'])
      if blank_string?(pref['id'])
        errors << "preference[#{index}] id must not be blank"
      else
        errors << "preference[#{index}] id must be an Integer or non-blank String"
      end
    end

    pref_text_required.each do |key|
      value = pref[key]
      next if nonblank_string?(value)

      if blank_string?(value)
        errors << "preference[#{index}] #{key} must not be blank"
      else
        errors << "preference[#{index}] #{key} must be a non-blank String"
      end
    end

    if pref.key?('severity') && !pref['severity'].nil?
      sev = pref['severity']
      unless sev.is_a?(String) && PREFERENCE_SEVERITY_ALLOWED.include?(sev)
        errors << "preference[#{index}] severity=#{sev.inspect} not in #{PREFERENCE_SEVERITY_ALLOWED.inspect}"
      end
    end

    next unless pref.key?('category') && pref['category']
    next if category_ids.include?(pref['category'])

    errors << "preference[#{index}] references unknown category: #{pref['category'].inspect}"
  end

  duplicate_category_ids = category_ids.group_by(&:itself).select { |_id, e| e.length > 1 }.keys.sort
  duplicate_pref_ids = pref_ids.group_by(&:itself).select { |_id, e| e.length > 1 }.keys.sort
  errors << "duplicate category ids: #{duplicate_category_ids.join(', ')}" unless duplicate_category_ids.empty?
  errors << "duplicate preference ids: #{duplicate_pref_ids.join(', ')}" unless duplicate_pref_ids.empty?

  total_prefs = integer_value(prefs['total_preferences'])
  if total_prefs && total_prefs != prefs['preferences'].length
    errors << "total_preferences=#{prefs['total_preferences']} does not match actual preferences count=#{prefs['preferences'].length}"
  end

  prefs['preferences'].each do |pref|
    next unless pref.is_a?(Hash) && pref['category']

    category_totals[pref['category']] += 1
  end

  prefs['categories'].each_with_index do |cat, index|
    next unless cat.is_a?(Hash) && cat['id']

    declared_count = integer_value(cat['preference_count'])
    next if declared_count.nil?

    actual_count = category_totals[cat['id']]
    next if declared_count == actual_count

    errors << "category[#{index}] #{cat['id'].inspect} preference_count=#{cat['preference_count']} does not match actual count=#{actual_count}"
  end

  return if errors.empty?

  warn "Error: Invalid preferences.yml entries in #{source_path}"
  errors.each { |error| warn "  - #{error}" }
  exit 1
end

def warn_missing_preferences_recommended(prefs)
  return unless prefs

  recommended = %w[severity applies_to init_text reference_files]
  prefs['preferences'].each_with_index do |pref, index|
    next unless pref.is_a?(Hash)

    present = ->(v) { !v.nil? && !(v.is_a?(String) && v.strip.empty?) && !(v.is_a?(Array) && v.empty?) }
    missing = recommended.reject { |key| pref.key?(key) && present.call(pref[key]) }
    missing.each do |key|
      warn "  WARNING: preference[#{index}] (#{pref['id']}) missing recommended field: #{key}"
    end
  end
end

prefs = nil
if File.exist?(PREFERENCES_YAML)
  prefs_raw = File.read(PREFERENCES_YAML)
  prefs = YAML.safe_load(
    prefs_raw,
    permitted_classes: [],
    permitted_symbols: [],
    aliases: false
  )
  unless prefs.is_a?(Hash) && prefs['preferences'].is_a?(Array) && prefs['categories'].is_a?(Array)
    warn "Error: Invalid preferences.yml structure in #{PREFERENCES_YAML}"
    exit 1
  end
  validate_preferences!(prefs, PREFERENCES_YAML)
end

def warn_missing_recommended(yaml)
  recommended = %w[severity applies_to init_text reference_files]
  nullable = %w[detector_id]
  yaml['laws'].each_with_index do |law, index|
    next unless law.is_a?(Hash)

    present = ->(v) { !v.nil? && !(v.is_a?(String) && v.strip.empty?) && !(v.is_a?(Array) && v.empty?) }
    missing = recommended.reject { |key| law.key?(key) && present.call(law[key]) }
    missing += nullable.reject { |key| law.key?(key) }
    missing.each do |key|
      warn "  WARNING: law[#{index}] (#{law['id']}) missing recommended field: #{key}"
    end
  end
end

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
      init = law['init_text']
      text = (init.is_a?(String) && !init.strip.empty?) ? init : law['summary_text']
      puts "#{idx + 1}. #{text}"
    end
    puts ''
  end
end

# Generate preferences injectable section (rendered between PREFERENCES_START/END markers)
def generate_preferences_injectable(prefs)
  unless prefs && prefs['preferences'].is_a?(Array) && !prefs['preferences'].empty?
    # No preferences defined — emit a sentinel comment so the block stays
    # present but inert.
    puts '<!-- no preferences defined -->'
    return
  end

  puts '## Advisory Preferences'
  puts ''
  puts 'Apply when possible; fall back gracefully when tools are unavailable.'
  puts ''

  known_category_ids = prefs['categories'].map { |c| c['id'] }

  prefs['categories'].each do |cat|
    prefs_in_cat = prefs['preferences'].select { |p| p['category'] == cat['id'] }
    next if prefs_in_cat.empty?

    puts "**#{cat['name']}:**"
    puts ''
    prefs_in_cat.each_with_index do |pref, idx|
      init = pref['init_text']
      text = (init.is_a?(String) && !init.strip.empty?) ? init : pref['summary_text']
      puts "#{idx + 1}. #{text}"
    end
    puts ''
  end

  # Safety net: preferences whose category is not declared in `categories`
  # should be loud, not silently dropped. Validator normally catches this;
  # this renders them under an Uncategorized bucket as belt-and-suspenders.
  orphans = prefs['preferences'].reject { |p| known_category_ids.include?(p['category']) }
  return if orphans.empty?

  puts '**Uncategorized:**'
  puts ''
  orphans.each_with_index do |pref, idx|
    init = pref['init_text']
    text = (init.is_a?(String) && !init.strip.empty?) ? init : pref['summary_text']
    puts "#{idx + 1}. #{text}"
  end
  puts ''
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
def generate_injector_script(yaml, prefs)
  output = "Ruby/Rails/Grape Iron Laws (NON-NEGOTIABLE) — #{yaml['total_laws']} Total:\n\n"

  yaml['categories'].each do |cat|
    output += "#{cat['name']} (#{cat['law_count']}):\n"
  end

  output += "\n"

  yaml['laws'].each do |law|
    output += "#{law['subagent_text']}\n"
  end

  if prefs && prefs['preferences'].is_a?(Array) && !prefs['preferences'].empty?
    total_prefs = prefs['total_preferences'] || prefs['preferences'].length
    output += "\nAdvisory Preferences — #{total_prefs} Total:\n"
    prefs['preferences'].each do |pref|
      output += "#{pref['subagent_text']}\n"
    end
  end

  payload = JSON.generate(
    'hookSpecificOutput' => {
      'hookEventName' => 'SubagentStart',
      'additionalContext' => output
    }
  )

  has_prefs = prefs && prefs['preferences'].is_a?(Array) && !prefs['preferences'].empty?
  puts '#!/usr/bin/env bash'
  puts 'set -o nounset'
  puts 'set -o pipefail'
  puts ''
  puts '# SubagentStart hook: inject Iron Laws (+ Advisory Preferences when present)'
  puts '# Policy: advisory injection via additionalContext; emit-then-exit. A'
  puts '# HEREDOC failure drops the payload, leaving the subagent without the'
  puts '# injected context — fail-open by design, no guardrail semantics.'
  if has_prefs
    puts '# GENERATED FROM iron-laws.yml + preferences.yml — DO NOT EDIT'
    puts "# Source versions: iron-laws=#{yaml['version']} preferences=#{prefs['version']}"
  else
    puts '# GENERATED FROM iron-laws.yml — DO NOT EDIT'
    puts "# Source version: iron-laws=#{yaml['version']} (preferences.yml absent)"
  end
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
when 'preferences_injectable'
  generate_preferences_injectable(prefs)
when 'tutorial'
  generate_tutorial_section(yaml)
when 'injector'
  generate_injector_script(yaml, prefs)
when 'canonical'
  generate_canonical_registry(yaml)
when 'readme'
  generate_readme(yaml)
when 'judge'
  generate_judge_section(yaml)
when 'validate'
  warn_missing_recommended(yaml)
  warn_missing_preferences_recommended(prefs)
  warn "Validation complete."
else
  puts "Usage: #{$PROGRAM_NAME} [injectable|preferences_injectable|tutorial|injector|canonical|readme|judge|validate]"
  exit 1
end
