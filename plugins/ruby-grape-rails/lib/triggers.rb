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
      return false if Regexp.new(pat).match?(command)
    end
    TRIGGER_SECTIONS.each do |section|
      walk(data, section).each do |pat|
        return true if Regexp.new(pat).match?(command)
      end
    end
    false
  rescue Errno::ENOENT, Psych::SyntaxError
    false
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
