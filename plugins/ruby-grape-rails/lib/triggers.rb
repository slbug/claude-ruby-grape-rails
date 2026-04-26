# frozen_string_literal: true

# Verify-command trigger matcher. Plugin-owned. No lab/ dependency.

require 'yaml'

module Triggers
  TRIGGER_SECTIONS = [
    %w[verify_commands direct],
    %w[verify_commands migrations],
    %w[verify_commands rake_verify_only]
  ].freeze
  EXCLUDE_SECTION = ['rake_excluded'].freeze

  module_function

  def matches?(triggers_path, command)
    data = YAML.safe_load_file(triggers_path) || {}
    walk(data, EXCLUDE_SECTION).each do |pat|
      return false if compile(pat)&.match?(command)
    end
    TRIGGER_SECTIONS.each do |section|
      walk(data, section).each do |pat|
        return true if compile(pat)&.match?(command)
      end
    end
    false
  rescue Errno::ENOENT, Errno::EACCES, Psych::SyntaxError, IOError
    false
  end

  # Compile a YAML-supplied pattern. Returns nil on RegexpError so a
  # single invalid pattern in triggers.yml does not crash the matcher;
  # the caller treats nil as "this pattern did not match" and continues
  # evaluating the next pattern (fail-open per the hook's contract).
  def compile(pattern)
    Regexp.new(pattern)
  rescue RegexpError
    nil
  end

  def walk(data, keys)
    cur = data
    keys.each do |key|
      return [] unless cur.is_a?(Hash) && cur.key?(key)

      cur = cur[key]
    end
    cur.is_a?(Array) ? cur : []
  end
end
