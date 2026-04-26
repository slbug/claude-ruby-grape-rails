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
  rescue Errno::ENOENT, Errno::EACCES, Psych::Exception, IOError
    # `Psych::Exception` covers the full safe-load failure surface:
    # `Psych::SyntaxError` (malformed YAML) and `Psych::DisallowedClass`
    # (tagged objects rejected by `safe_load_file`). The hook contract
    # is fail-open; any of these → "no match" rather than an exception
    # propagating up through the matcher CLI.
    false
  end

  # Compile a YAML-supplied pattern. Returns nil for non-string values
  # (e.g. an accidentally-numeric or nil entry in triggers.yml) and on
  # RegexpError so a single invalid pattern does not crash the matcher;
  # the caller treats nil as "this pattern did not match" and continues
  # evaluating the next pattern (fail-open per the hook's contract).
  # `Regexp.new(nil)` and `Regexp.new(42)` raise `TypeError`, which an
  # explicit `is_a?(String)` guard avoids without paying the exception
  # cost on every invocation.
  def compile(pattern)
    return unless pattern.is_a?(String)

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
