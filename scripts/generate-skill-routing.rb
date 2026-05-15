#!/usr/bin/env ruby
# frozen_string_literal: true

# Regenerate routing-table + hub-body footers + tutorial-content inventory
# inventory from references/skill-registry.yml.
#
# Marker format inside target files:
#   <!-- BEGIN-GENERATED <block-name> -->
#   ...generator-controlled content...
#   <!-- END-GENERATED <block-name> -->
#
# Block names + targets:
#   routing-table     → plugins/ruby-grape-rails/skills/intent-detection/SKILL.md
#   related-footer    → any hub-body SKILL.md that hosts the marker (registry advertise_in drives content per file)
#   inventory         → plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md
#
# Modes:
#   default → write generated content into matching marker blocks
#   --check → report 0 if all marker blocks match generator output, non-zero otherwise

require 'yaml'
require 'pathname'

REPO_ROOT  = Pathname.new(__dir__).join('..').expand_path
REGISTRY   = REPO_ROOT.join('plugins/ruby-grape-rails/references/skill-registry.yml')
SKILLS_DIR = REPO_ROOT.join('plugins/ruby-grape-rails/skills')

BEGIN_RE = /<!-- BEGIN-GENERATED ([a-z0-9-]+) -->/
END_RE   = /<!-- END-GENERATED ([a-z0-9-]+) -->/

# --- Routing-table rows pulled from existing intent-detection body when we
# regenerate, so the visible-skill rows stay intact and the registry-driven
# hidden-skill rows are appended. The existing rows live verbatim above the
# marker; the marker block carries only the DMI roster routing rows.

def load_registry
  YAML.safe_load_file(REGISTRY, permitted_classes: [Symbol])
end

# --- Block generators -------------------------------------------------------

def routing_table_rows(reg)
  rows = []
  reg.fetch('hidden_skills').each do |entry|
    next if entry['aliases'].to_a.empty?
    signal = entry['aliases'].map { |a| %("#{a}") }.join(', ')
    rows << "| #{signal} | #{entry['rationale']} | `/#{entry['name']}` |"
  end
  ["| Signal | Detected Intent | Suggest |", "|---|---|---|", *rows].join("\n")
end

def related_footer_for_hub(reg, hub_name)
  hits = reg.fetch('hidden_skills').select { |e| Array(e['advertise_in']).include?(hub_name) }
  return nil if hits.empty?
  bullets = hits.map { |e| "- #{e.fetch('symptom', e['rationale'])} → `/#{e['name']}` (#{e['rationale']})" }
  bullets.join("\n")
end

def inventory_section(reg)
  visible = reg.fetch('visible_skills').map { |e| "- `/#{e['name']}` — #{e['rationale']}" }
  hidden  = reg.fetch('hidden_skills').map  { |e| "- `/#{e['name']}` — #{e['rationale']}" }
  [
    "**Visible (in routing budget):**",
    "",
    *visible,
    "",
    "**Hidden (DMI, slash-invocable):**",
    "",
    *hidden,
  ].join("\n")
end

# --- File-walking + splicing -----------------------------------------------

# Targets the script scans for marker blocks. Each is (path, hub-name-or-nil).
# hub-name is only meaningful for `related-footer` blocks; other block types
# look up content by block name alone.
def scan_targets
  targets = []
  targets << [SKILLS_DIR.join('intent-detection/SKILL.md'), nil]
  targets << [SKILLS_DIR.join('intro/references/tutorial-content.md'), nil]
  SKILLS_DIR.glob('*/SKILL.md').sort.each do |skill_md|
    folder = skill_md.parent.basename.to_s
    next if folder == 'intent-detection'
    targets << [skill_md, folder]
  end
  targets
end

def expected_content(block_name, hub_folder, reg)
  case block_name
  when 'routing-table'  then routing_table_rows(reg)
  when 'inventory'      then inventory_section(reg)
  when 'related-footer' then related_footer_for_hub(reg, hub_folder)
  else nil
  end
end

def splice(text, block_name, content)
  marker_re = /(<!-- BEGIN-GENERATED #{Regexp.escape(block_name)} -->)(.*?)(<!-- END-GENERATED #{Regexp.escape(block_name)} -->)/m
  return text unless text.match?(marker_re)
  text.sub(marker_re) { "#{Regexp.last_match(1)}\n#{content}\n#{Regexp.last_match(3)}" }
end

def each_block(text)
  scanner = StringScanner.new(text)
  while scanner.scan_until(BEGIN_RE)
    block_name = scanner.captures.first
    yield block_name
  end
end

require 'strscan'

# --- Main ------------------------------------------------------------------

FOOTER_HEADING = "\n## Related — invoke manually if needed\n\n<!-- BEGIN-GENERATED related-footer -->\n<!-- END-GENERATED related-footer -->\n"

def ensure_related_footer_marker(text, hub_folder, reg)
  return text if text.include?('<!-- BEGIN-GENERATED related-footer -->')
  return text unless hub_folder
  return text if related_footer_for_hub(reg, hub_folder).nil?
  trimmed = text.sub(/\s*\z/, "\n")
  trimmed + FOOTER_HEADING
end

def run(mode:)
  reg = load_registry
  drift = []
  scan_targets.each do |path, hub_folder|
    next unless path.file?
    text = path.read
    text_with_markers = ensure_related_footer_marker(text, hub_folder, reg)
    next unless text_with_markers.include?('<!-- BEGIN-GENERATED ')
    if text_with_markers != text && mode == :check
      drift << "#{path.relative_path_from(REPO_ROOT)} :: missing related-footer marker"
    end
    updated = text_with_markers.dup
    each_block(text_with_markers) do |block_name|
      content = expected_content(block_name, hub_folder, reg)
      next if content.nil?
      after = splice(updated, block_name, content)
      drift << "#{path.relative_path_from(REPO_ROOT)} :: #{block_name}" if after != updated && mode == :check && after != text_with_markers
      updated = after
    end
    next if updated == text
    if mode == :write
      path.write(updated)
      puts "wrote #{path.relative_path_from(REPO_ROOT)}"
    end
  end
  if mode == :check && !drift.empty?
    warn "registry vs generated drift:"
    drift.each { |row| warn "  #{row}" }
    exit 1
  end
end

mode = ARGV.include?('--check') ? :check : :write
run(mode: mode)
