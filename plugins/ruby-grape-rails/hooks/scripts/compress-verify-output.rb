#!/usr/bin/env ruby
# frozen_string_literal: true

# Policy: advisory PostToolUse / PostToolUseFailure hook. Opt-in
# telemetry collector — fail-open. When
# RUBY_PLUGIN_COMPRESSION_TELEMETRY=1 is set, appends compression
# stats to ${CLAUDE_PLUGIN_DATA}/compression.jsonl and preserves the
# captured Bash output under ${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log.
# When unset (default), exits 0 immediately with zero side effects.
# Any unexpected error (require failure, JSON parse, library raise,
# SystemCallError on write) is swallowed by the top-level rescue and
# becomes a clean exit 0 — raw Bash output reaching Claude is never
# altered, hook is never a gating step.

require 'json'
require 'securerandom'
require 'fileutils'

# Defense-in-depth cap on hook-input size. CC bounds Bash output upstream
# (background tasks killed at 5 GiB per CC changelog), but a runaway
# foreground payload could still pin RSS during JSON.parse. 8 MiB covers
# ~150K-line rspec output; anything bigger is dropped from telemetry.
MAX_HOOK_INPUT_BYTES = 8 * 1024 * 1024

exit 0 unless ENV['RUBY_PLUGIN_COMPRESSION_TELEMETRY'] == '1'

begin
  plugin_root = ENV['CLAUDE_PLUGIN_ROOT'].to_s
  exit 0 if plugin_root.empty?

  require_relative File.join(plugin_root, 'lib/triggers')
  require_relative File.join(plugin_root, 'lib/verify_compression')

  $stdin.binmode
  # Read MAX+1 to detect overflow without slurping the full payload.
  input = $stdin.read(MAX_HOOK_INPUT_BYTES + 1)
  exit 0 if input.nil? || input.empty?
  exit 0 if input.bytesize > MAX_HOOK_INPUT_BYTES

  data = begin
    JSON.parse(input)
  rescue JSON::ParserError
    exit 0
  end
  exit 0 unless data.is_a?(Hash)

  tool_name = data['tool_name'].to_s
  command   = data.dig('tool_input', 'command').to_s
  exit 0 unless tool_name == 'Bash'
  exit 0 if command.empty?

  # Skip on user-interrupt (partial output not representative).
  exit 0 if data.dig('tool_response', 'interrupted') == true
  exit 0 if data['is_interrupt'] == true

  # Three output channels across PostToolUse + PostToolUseFailure:
  #   - tool_response.stdout — captured stdout (PostToolUse)
  #   - tool_response.stderr — captured stderr (PostToolUse)
  #   - top-level `error`    — failure blob (PostToolUseFailure)
  # Treat `error` as another stderr stream. Combine stderr + error
  # into one stream so the `--- stderr ---` marker is consistent
  # whether the source was a successful run with stderr or a failure
  # event with an `error` blob.
  out = data.dig('tool_response', 'stdout').to_s
  stderr_stream = [data.dig('tool_response', 'stderr').to_s, data['error'].to_s]
                  .reject(&:empty?)
                  .join("\n")

  parts = []
  parts << out unless out.empty?
  parts << "--- stderr ---\n#{stderr_stream}" unless stderr_stream.empty?
  output = parts.join("\n")

  triggers_path = File.join(plugin_root, 'references/compression/triggers.yml')
  rules_path    = File.join(plugin_root, 'references/compression/rules.yml')
  exit 0 unless File.readable?(triggers_path)
  exit 0 unless File.readable?(rules_path)

  exit 0 unless Triggers.matches?(triggers_path, command)

  data_dir = ENV['CLAUDE_PLUGIN_DATA'].to_s
  exit 0 if data_dir.empty?
  # Refuse to write through a symlinked plugin-data dir.
  exit 0 unless File.directory?(data_dir) && !File.symlink?(data_dir)

  raw_dir = File.join(data_dir, 'verify-raw')
  FileUtils.mkdir_p(raw_dir)
  exit 0 unless File.directory?(raw_dir) && !File.symlink?(raw_dir)

  # Skip BEFORE creating raw_log so an empty extracted output never
  # materializes a 0-byte orphan. The plugin never `rm`s telemetry.
  exit 0 if output.empty?

  raw_log = File.join(raw_dir, "#{SecureRandom.uuid}.log")
  flags = File::WRONLY | File::CREAT | File::EXCL | File::NOFOLLOW
  begin
    File.open(raw_log, flags, 0o600) { |f| f.write(output) }
  rescue Errno::EEXIST, Errno::ELOOP, Errno::EMLINK, SystemCallError
    exit 0
  end
  exit 0 unless (File.size?(raw_log) || 0).positive?

  result = VerifyCompression.compress(output)
  entry = {
    'ts' => Time.now.to_f,
    'cmd' => command,
    'raw_bytes' => result.raw_bytes,
    'compressed_bytes' => result.compressed_bytes,
    'ratio' => result.ratio,
    'violations' => result.preservation_violations,
    'raw_log' => raw_log
  }
  VerifyCompression.append_jsonl(File.join(data_dir, 'compression.jsonl'), entry)
rescue StandardError, LoadError, SystemCallError
  # Fail-open. PostToolUse stderr feeds the debug log only (per Anthropic
  # docs), but any non-zero exit could surface in unexpected ways. Swallow
  # all non-SystemExit errors and exit cleanly. SystemExit (raised by
  # `exit 0` above) propagates normally.
end
exit 0
