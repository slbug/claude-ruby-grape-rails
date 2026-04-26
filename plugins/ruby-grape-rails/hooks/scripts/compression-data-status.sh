#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory SessionStart hook. Read-only. Emits a single
# advisory per SessionStart invocation (no cross-session
# de-duplication; it fires every startup/resume while the thresholds
# are crossed) to stdout when accumulated verify-output compression
# telemetry crosses either threshold from
# `references/compression/rules.yml`
# (`advisory.size_threshold_bytes`, `advisory.sample_threshold`).
# SessionStart stdout IS added to Claude's context per Anthropic Claude
# Code hooks docs, so the message reaches both the model and the user.
# This hook NEVER writes or deletes any data. The plugin ships no
# destructive command at all — cleanup is the user's manual action via
# `rm`, with the exact paths surfaced in the advisory message below.
#
# Fail-open: missing ruby, missing files, unreadable rules, or any
# error path causes a clean exit 0 with no output.

[[ "${RUBY_PLUGIN_COMPRESSION_TELEMETRY:-0}" == "1" ]] || exit 0
[[ -n "${CLAUDE_PLUGIN_DATA:-}" ]] || exit 0
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
[[ -n "$PLUGIN_ROOT" ]] || exit 0
command -v ruby >/dev/null 2>&1 || exit 0

DATA_DIR="$CLAUDE_PLUGIN_DATA"
JSONL="${DATA_DIR}/compression.jsonl"
RAW_DIR="${DATA_DIR}/verify-raw"
RULES="${PLUGIN_ROOT}/references/compression/rules.yml"

[[ -r "$RULES" ]] || exit 0

# Single Ruby block: parses thresholds from rules.yml, sums telemetry
# size, counts jsonl samples, emits the nudge to stdout when either
# threshold crosses. Pure read-only.
# shellcheck disable=SC2016  # Ruby script body uses Ruby interpolation, not shell expansion
ruby -ryaml -rshellwords -e '
  rules_path, data_dir, jsonl_path, raw_dir = ARGV
  begin
    rules = YAML.safe_load_file(rules_path) || {}
  rescue StandardError
    exit 0
  end
  advisory = rules["advisory"] || {}
  size_threshold = Integer(advisory["size_threshold_bytes"] || 0) rescue 0
  sample_threshold = Integer(advisory["sample_threshold"] || 0) rescue 0
  exit 0 if size_threshold <= 0 && sample_threshold <= 0

  # Short-circuit as soon as either threshold is crossed: a SessionStart
  # hook should not stat or stream every byte under verify-raw/ when one
  # answer is already enough to fire the advisory.
  size_hit = false
  sample_hit = false
  total_bytes = 0
  sample_count = 0

  if File.file?(jsonl_path)
    total_bytes += File.size(jsonl_path)
    size_hit = true if size_threshold.positive? && total_bytes >= size_threshold
  end

  unless size_hit
    if File.directory?(raw_dir)
      raw_real = File.realpath(raw_dir) rescue nil
      data_real = File.realpath(data_dir) rescue nil
      if raw_real && data_real &&
         File.basename(raw_real) == "verify-raw" &&
         raw_real.start_with?(data_real + File::SEPARATOR)
        # `Dir.each_child` streams entries without materializing the
        # full filename array; keeps SessionStart memory bounded even
        # when `verify-raw/` accumulates thousands of files.
        Dir.each_child(raw_real) do |name|
          break if size_hit
          path = File.join(raw_real, name)
          next if File.symlink?(path)
          next unless File.file?(path)
          next unless name.end_with?(".log")
          begin
            total_bytes += File.size(path)
          rescue StandardError
            next
          end
          size_hit = true if size_threshold.positive? && total_bytes >= size_threshold
        end
      end
    end
  end

  if File.file?(jsonl_path) && sample_threshold.positive?
    File.foreach(jsonl_path) do |line|
      sample_count += 1 unless line.strip.empty?
      if sample_count >= sample_threshold
        sample_hit = true
        break
      end
    end
  end

  exit 0 unless size_hit || sample_hit

  mb = (total_bytes / (1024.0 * 1024.0)).round(1)
  reasons = []
  reasons << format("%.1f MB on disk", mb) if size_hit
  reasons << "#{sample_count} samples" if sample_hit

  # SessionStart stdout enters the model context. Surface only the
  # telemetry paths, never literal rm / rm -rf command strings; the
  # user composes the cleanup command from these paths.
  puts "[ruby-grape-rails] Verify-output compression telemetry has accumulated (#{reasons.join(", ")})."
  puts "[ruby-grape-rails] Run /rb:compression-report to draft a redacted report you can share."
  puts "[ruby-grape-rails] When you (the user) decide to clean up, the relevant paths on disk are:"
  puts "[ruby-grape-rails]   jsonl:     #{Shellwords.escape(jsonl_path)}"
  puts "[ruby-grape-rails]   raw logs:  #{Shellwords.escape(raw_dir)} (directory)"
' "$RULES" "$DATA_DIR" "$JSONL" "$RAW_DIR" 2>/dev/null || true

exit 0
