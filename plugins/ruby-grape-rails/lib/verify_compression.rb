# frozen_string_literal: true

# Deterministic verify-output compressor. Plugin-owned runtime.
#
# Loads rules from references/compression/rules.yml. Operates line-by-line;
# collapses stack frames beyond top-5, "Loaded gem" preamble, and repeated
# DEPRECATION WARNING blocks. Verifies preserve patterns survive compression.

require 'yaml'

module VerifyCompression
  RULES_PATH = File.expand_path('../references/compression/rules.yml', __dir__)
  STACK_FRAME_RE = /^\s*(from|at) .+:\d+/
  DEPRECATION_RE = /DEPRECATION WARNING/i
  GEM_LOADING_RE = /^\s*Loaded gem /i

  Result = Data.define(:text, :raw_bytes, :compressed_bytes, :preservation_violations) do
    def ratio
      return 0.0 if raw_bytes.zero?

      1.0 - (compressed_bytes.to_f / raw_bytes)
    end
  end

  module_function

  def compress(raw, rules_path: RULES_PATH)
    rules = load_rules(rules_path)
    lines = raw.split("\n", -1)
    lines = collapse_stack(lines)
    lines = collapse_gem_loading(lines)
    lines = collapse_deprecations(lines)
    compressed = lines.join("\n")
    violations = check_preservation(raw, compressed, rules)
    Result.new(
      text: compressed,
      raw_bytes: raw.bytesize,
      compressed_bytes: compressed.bytesize,
      preservation_violations: violations
    )
  end

  def load_rules(path)
    YAML.safe_load_file(path) || {}
  rescue Errno::ENOENT
    {}
  end

  def collapse_stack(lines)
    result = []
    buf = []
    flush = lambda do
      next if buf.empty?

      if buf.length <= 5
        result.concat(buf)
      else
        result.concat(buf.first(5))
        result << "  [... #{buf.length - 5} more frames elided ...]"
      end
      buf.clear
    end
    lines.each do |line|
      if STACK_FRAME_RE.match?(line)
        buf << line
      else
        flush.call
        result << line
      end
    end
    flush.call
    result
  end

  def collapse_gem_loading(lines)
    result = []
    buf = []
    flush = lambda do
      next if buf.empty?

      if buf.length <= 1
        result.concat(buf)
      else
        result << "Loaded #{buf.length} gems"
      end
      buf.clear
    end
    lines.each do |line|
      if GEM_LOADING_RE.match?(line)
        buf << line
      else
        flush.call
        result << line
      end
    end
    flush.call
    result
  end

  def collapse_deprecations(lines)
    result = []
    seen = false
    dupe = 0
    lines.each do |line|
      if DEPRECATION_RE.match?(line)
        if seen
          dupe += 1
        else
          result << line
          seen = true
        end
      else
        if dupe.positive?
          result << "  [+#{dupe} similar deprecations]"
          dupe = 0
        end
        result << line
      end
    end
    result << "  [+#{dupe} similar deprecations]" if dupe.positive?
    result
  end

  def check_preservation(raw, compressed, rules)
    # Ruby `^` matches each line by default; no flag needed (unlike Python's
    # re.MULTILINE).
    violations = []
    (rules['preserve'] || {}).each do |name, pattern|
      next unless pattern.is_a?(String)
      next if pattern.include?('verbatim')

      begin
        re = Regexp.new(pattern)
      rescue RegexpError
        next
      end
      raw.scan(re) do
        match = Regexp.last_match(0)
        violations << "#{name}: dropped #{match.inspect}" unless compressed.include?(match)
      end
    end
    violations
  end
end
