#!/usr/bin/env ruby
# frozen_string_literal: true

# Policy: advisory hook. Opt-in skill-discovery telemetry collector —
# fail-open. When RUBY_PLUGIN_DISCOVERY_LOG=1 is set, matches the hook
# input against patterns in references/discovery/triggers.yml and appends
# a JSONL row per match to ${CLAUDE_PLUGIN_DATA}/discovery.jsonl
# (file mode 0o600).
#
# When RUBY_PLUGIN_DISCOVERY_LOG_EXCERPTS=1 is also set, the row carries
# a 200-char redacted excerpt of the matched extractor field.
#
# Throttle simulation: each session+skill pair caps at PER_SESSION_CAP
# matches per session. State persists in
# ${CLAUDE_PLUGIN_DATA}/discovery-cache.json. The cap is a SIMULATION —
# the observer logs the would_throttle decision but writes every match
# regardless, so future analysis can tune the cap before any active
# injection layer ships.
#
# Default: env vars unset → exit 0 immediately, zero side effects.
# Any unexpected error → exit 0. Never alters hook chain.

require 'json'
require 'fileutils'

MAX_HOOK_INPUT_BYTES   = 8 * 1024 * 1024
EXCERPT_MAX_CHARS      = 200
LOG_ROTATE_BYTES       = 5 * 1024 * 1024
WOULD_INJECT_MAX_CHARS = 200
PER_SESSION_CAP        = 20
LOG_FILE_MODE          = 0o600
CACHE_FILE_MODE        = 0o600

exit 0 unless ENV['RUBY_PLUGIN_DISCOVERY_LOG'] == '1'

begin
  plugin_root = ENV['CLAUDE_PLUGIN_ROOT'].to_s
  exit 0 if plugin_root.empty?

  data_dir = ENV['CLAUDE_PLUGIN_DATA'].to_s
  exit 0 if data_dir.empty?

  # Spec: refuse a symlinked plugin-data directory before mkdir_p / writes.
  # Telemetry is local-only and writes to attacker-controlled symlink targets
  # would leak event payloads outside the data root.
  begin
    if File.exist?(data_dir)
      st = File.lstat(data_dir)
      exit 0 if st.symlink? || !st.directory?
    end
  rescue SystemCallError
    exit 0
  end

  require 'yaml'

  triggers_path = File.join(plugin_root, 'references/discovery/triggers.yml')
  triggers = YAML.load_file(triggers_path)
  exit 0 unless triggers.is_a?(Hash) && triggers['triggers'].is_a?(Array)

  $stdin.binmode
  input = $stdin.read(MAX_HOOK_INPUT_BYTES + 1)
  exit 0 if input.nil? || input.empty? || input.bytesize > MAX_HOOK_INPUT_BYTES

  begin
    data = JSON.parse(input)
  rescue JSON::ParserError
    exit 0
  end
  exit 0 unless data.is_a?(Hash)

  hook_event = data['hook_event_name'].to_s
  exit 0 if hook_event.empty?

  session_id = data['session_id'].to_s
  log_path   = File.join(data_dir, 'discovery.jsonl')
  cache_path = File.join(data_dir, 'discovery-cache.json')
  rotate_if_needed(log_path)
  cache = load_cache(cache_path)

  triggers['triggers'].each do |rule|
    next unless rule.is_a?(Hash)
    next unless Array(rule['event_kinds']).include?(hook_event)
    next unless rule_matches?(rule, data)

    suggest_list = Array(rule['suggest'] || rule['suggest_list'])
    suggest_list.each do |suggest|
      next if suggest.to_s.empty?

      throttle = update_cache_count!(cache, session_id, suggest.to_s)
      entry = build_entry(rule, data, hook_event, suggest.to_s, throttle)
      append_jsonl(log_path, entry)
    end
  end

  save_cache(cache_path, cache)
rescue StandardError, LoadError, SystemCallError
  # Fail-open. Any error → silent exit 0.
end
exit 0

BEGIN {
  def rotate_if_needed(path)
    return unless File.exist?(path)
    return if File.size(path) < LOG_ROTATE_BYTES

    n = 1
    n += 1 while File.exist?("#{path}.#{n}")
    File.rename(path, "#{path}.#{n}")
  rescue SystemCallError
    # Best-effort. Failure to rotate is non-fatal.
  end

  def rule_matches?(rule, data)
    clauses = Array(rule['match'])
    return false if clauses.empty?

    threshold = rule['confidence_min'].to_i.clamp(1, 10)
    hits = clauses.count { |clause| clause_matches?(clause, data) }
    hits >= threshold
  end

  def clause_matches?(clause, data)
    return false unless clause.is_a?(Hash)

    case clause['type']
    when 'regex'      then regex_match?(clause, data)
    when 'structured' then structured_match?(clause, data)
    else false
    end
  end

  def regex_match?(clause, data)
    text = extract_field(clause['extractor'], data).to_s
    return false if text.empty?

    Regexp.new(clause['pattern']).match?(text)
  rescue RegexpError
    false
  end

  def structured_match?(clause, data)
    value = extract_field(clause['extractor'], data)
    case clause['operator']
    when 'equals' then value == clause['value']
    when 'glob'
      value.is_a?(String) && File.fnmatch?(clause['value'].to_s, value, File::FNM_PATHNAME)
    else false
    end
  end

  def extract_field(path, data)
    return nil if path.nil?

    path.to_s.split('.').reduce(data) { |acc, key| acc.is_a?(Hash) ? acc[key] : nil }
  end

  # Returns { count:, would_throttle:, throttle_reason: } for the
  # session+skill pair AFTER incrementing the count.
  def update_cache_count!(cache, session_id, skill)
    key = "#{session_id}::#{skill}"
    cache[key] = (cache[key] || 0) + 1
    count = cache[key]
    if count > PER_SESSION_CAP
      { count: count, would_throttle: true, throttle_reason: "per-session cap #{PER_SESSION_CAP} exceeded" }
    else
      { count: count, would_throttle: false, throttle_reason: nil }
    end
  end

  def build_entry(rule, data, hook_event, suggest, throttle)
    reason = rule['reason'].to_s
    would_chars = (reason.length + suggest.length + 80).clamp(0, WOULD_INJECT_MAX_CHARS)
    entry = {
      'ts' => Time.now.utc.iso8601,
      'session_id' => data['session_id'].to_s,
      'hook_event' => hook_event,
      'matched_rule' => rule['id'],
      'suggest' => suggest,
      'reason' => reason,
      'would_inject' => true,
      'would_inject_chars' => would_chars,
      'would_throttle' => throttle[:would_throttle],
      'throttle_reason' => throttle[:throttle_reason],
      'session_skill_count' => throttle[:count]
    }
    if ENV['RUBY_PLUGIN_DISCOVERY_LOG_EXCERPTS'] == '1'
      raw = (data.dig('prompt') || data.dig('tool_input', 'command') || data.dig('tool_input', 'file_path')).to_s
      entry['excerpt'] = redact(raw[0, EXCERPT_MAX_CHARS])
    end
    entry
  end

  def redact(text)
    text
      .gsub(%r{/Users/[^/\s]+}, '/Users/<redacted>')
      .gsub(%r{/home/[^/\s]+}, '/home/<redacted>')
      .gsub(/[A-Z][A-Z0-9_]+\s*=\s*\S+/, '<env=redacted>')
  end

  def load_cache(path)
    return {} unless File.exist?(path)
    return {} unless File.lstat(path).file?

    text = File.read(path)
    data = JSON.parse(text)
    data.is_a?(Hash) ? data : {}
  rescue JSON::ParserError, SystemCallError, IOError
    {}
  end

  def save_cache(path, cache)
    FileUtils.mkdir_p(File.dirname(path))
    tmp = "#{path}.tmp"
    File.open(tmp, File::WRONLY | File::CREAT | File::TRUNC | File::NOFOLLOW, CACHE_FILE_MODE) do |fh|
      fh.write(JSON.generate(cache))
    end
    File.rename(tmp, path)
  rescue SystemCallError, IOError
    # Best-effort.
  end

  def append_jsonl(path, entry)
    FileUtils.mkdir_p(File.dirname(path))
    begin
      st = File.lstat(path)
      return if st.symlink? || !st.file?
    rescue Errno::ENOENT
      # path will be created below
    rescue SystemCallError
      return
    end
    File.open(path, File::WRONLY | File::CREAT | File::APPEND | File::NOFOLLOW, LOG_FILE_MODE) do |fh|
      fh.flock(File::LOCK_EX)
      fh.write(JSON.generate(entry) + "\n")
      fh.flush
    end
  rescue SystemCallError, IOError
    # Fail-open.
  end
}
