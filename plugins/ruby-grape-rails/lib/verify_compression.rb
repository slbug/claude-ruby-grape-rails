# frozen_string_literal: true

# Deterministic verify-output compressor. Plugin-owned runtime.
#
# Loads rules from references/compression/rules.yml. Operates line-by-line;
# collapses stack frames beyond top-5, "Loaded gem" preamble, and repeated
# DEPRECATION WARNING blocks. Verifies preserve patterns survive compression.

require 'yaml'
require 'json'
require 'fileutils'

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

  # Default templates used when rules.yml omits a `collapse:` key.
  # rules.yml is hot-reloadable; the file's templates win when present.
  DEFAULT_COLLAPSE = {
    'stack_beyond_5' => '  [... {count} more frames elided ...]',
    'deprecation_warnings' => '  [+{count} similar deprecations]',
    'gem_loading' => 'Loaded {count} gems'
  }.freeze

  module_function

  def compress(raw, rules_path: RULES_PATH)
    rules = load_rules(rules_path)
    collapse = build_collapse(rules)
    lines = raw.split("\n", -1)
    lines = collapse_stack(lines, collapse['stack_beyond_5'])
    lines = collapse_gem_loading(lines, collapse['gem_loading'])
    lines = collapse_deprecations(lines, collapse['deprecation_warnings'])
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
  rescue Errno::ENOENT, Errno::EACCES, Psych::Exception, IOError
    # Missing / unreadable / malformed rules.yml falls back to an empty
    # ruleset. `Psych::Exception` covers the full safe-load failure
    # surface (SyntaxError, DisallowedClass, BadAlias, …). The
    # compressor still runs (collapse uses DEFAULT_COLLAPSE, preserve
    # check has no patterns to verify) and the hook's documented
    # fail-open contract is preserved — a misconfigured rules file
    # MUST NOT crash the caller.
    {}
  end

  def build_collapse(rules)
    file_collapse = rules['collapse']
    return DEFAULT_COLLAPSE.dup unless file_collapse.is_a?(Hash)

    DEFAULT_COLLAPSE.each_with_object({}) do |(key, default), out|
      val = file_collapse[key]
      out[key] = val.is_a?(String) ? val : default
    end
  end

  def render_collapse(template, count)
    template.gsub('{count}', count.to_s)
  end

  def collapse_stack(lines, template)
    result = []
    buf = []
    flush = lambda do
      next if buf.empty?

      if buf.length <= 5
        result.concat(buf)
      else
        result.concat(buf.first(5))
        result << render_collapse(template, buf.length - 5)
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

  def collapse_gem_loading(lines, template)
    result = []
    buf = []
    flush = lambda do
      next if buf.empty?

      if buf.length <= 1
        result.concat(buf)
      else
        result << render_collapse(template, buf.length)
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

  def collapse_deprecations(lines, template)
    # Collapse a run of CONSECUTIVE IDENTICAL deprecation lines into the
    # first occurrence + a `[+N similar deprecations]` suffix. A
    # different deprecation message, or any non-deprecation line, ends
    # the run and is emitted in full. The previous implementation kept
    # a global `seen` flag and treated every later DEPRECATION line as
    # a duplicate regardless of content, which silently dropped
    # distinct deprecation messages later in the same output.
    result = []
    last_dep = nil
    dupe = 0
    flush_dupe = lambda do
      if dupe.positive?
        result << render_collapse(template, dupe)
        dupe = 0
      end
    end
    lines.each do |line|
      if DEPRECATION_RE.match?(line)
        if line == last_dep
          dupe += 1
        else
          flush_dupe.call
          result << line
          last_dep = line
        end
      else
        flush_dupe.call
        last_dep = nil
        result << line
      end
    end
    flush_dupe.call
    result
  end

  def check_preservation(raw, compressed, rules)
    # Every value under `preserve:` is treated as a regex; non-string
    # values are a config bug and surface as a violation. Ruby `^` matches
    # each line by default — no flag needed (unlike Python's re.MULTILINE).
    # Prose / explanatory text belongs in YAML comments, never in a
    # `preserve:` value, because a misconfigured pattern silently
    # disabling preservation is exactly the failure mode this check is
    # meant to catch.
    violations = []
    preserve = rules['preserve']
    case preserve
    when nil
      # No preserve rules configured → nothing to check.
      return violations
    when Hash
      # Expected shape; fall through to the per-rule loop below.
    else
      # Misconfiguration (scalar, array, …): emit a single violation
      # describing the schema problem rather than crashing on `.each`.
      # This preserves the documented "config errors surface as
      # violations" contract from the comment block above.
      violations << "preserve: top-level value must be a Hash, got #{preserve.class}"
      return violations
    end

    preserve.each do |name, pattern|
      unless pattern.is_a?(String)
        violations << "#{name}: preserve rule is not a string regex (#{pattern.class})"
        next
      end

      begin
        re = Regexp.new(pattern)
      rescue RegexpError => e
        violations << "#{name}: invalid preserve regex (#{e.message})"
        next
      end
      # Multiplicity check: every occurrence of a preserve pattern in
      # raw output must appear at least the same number of times in
      # the compressed output. `compressed.include?(match)` alone would
      # incorrectly accept a compressed copy that dropped 4 of 5
      # duplicate matches — passing the contract "each occurrence
      # survives" only by coincidence on the first hit.
      raw_counts = scan_counts(raw, re)
      next if raw_counts.empty?

      compressed_counts = scan_counts(compressed, re)
      raw_counts.each do |match, raw_n|
        kept = compressed_counts.fetch(match, 0)
        next if kept >= raw_n

        violations << "#{name}: #{match.inspect} preserved #{kept}/#{raw_n} occurrences"
      end
    end
    violations
  end

  # Append a JSONL stats entry to log_path. Symlink-safe (lstat + NOFOLLOW)
  # and concurrency-safe (LOCK_EX). Returns true on success, false on any
  # bail condition. Caller is responsible for input validation.
  def append_jsonl(log_path, entry)
    FileUtils.mkdir_p(File.dirname(log_path))
    begin
      st = File.lstat(log_path)
      return false if st.symlink? || !st.file?
    rescue Errno::ENOENT
      # path will be created below
    rescue SystemCallError
      return false
    end

    File.open(log_path, File::WRONLY | File::CREAT | File::APPEND | File::NOFOLLOW, 0o644) do |fh|
      fh.flock(File::LOCK_EX)
      fh.puts(JSON.generate(entry))
      fh.flush
    end
    true
  rescue Errno::ELOOP, Errno::EMLINK
    false
  end

  # Returns a Hash mapping the full-match string of each occurrence to
  # its count. Streams counts directly into the Hash via `String#scan`'s
  # block form so verify outputs in the multi-MB range never materialize
  # a full Array of every match before tallying. The block-form scan
  # also makes `Regexp.last_match(0)` (the full match) available even
  # for patterns with capture groups — needed for preserve regexes like
  # `file_colon_line` that capture path and line number.
  def scan_counts(text, re)
    counts = Hash.new(0)
    text.scan(re) { counts[Regexp.last_match(0)] += 1 }
    counts
  end
end
