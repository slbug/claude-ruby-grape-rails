#!/usr/bin/env ruby
# frozen_string_literal: true

# Telemetry collector for verify-output compression. Opt-in via
# RUBY_PLUGIN_COMPRESSION_TELEMETRY=1. When enabled, appends compression
# stats to ${CLAUDE_PLUGIN_DATA}/compression.jsonl and preserves the raw
# captured Bash output under ${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log.
# When disabled (default), exits 0 immediately with zero side effects.
# Fail-open: any unreadable config / write error → clean exit 0,
# raw Bash output reaching Claude is never altered.

require 'json'
require 'securerandom'
require 'fileutils'

exit 0 unless ENV['RUBY_PLUGIN_COMPRESSION_TELEMETRY'] == '1'

plugin_root = ENV['CLAUDE_PLUGIN_ROOT'].to_s
exit 0 if plugin_root.empty?

require_relative File.join(plugin_root, 'lib/triggers')
require_relative File.join(plugin_root, 'lib/verify_compression')

$stdin.binmode
input = $stdin.read
exit 0 if input.nil? || input.empty?

data = begin
  JSON.parse(input)
rescue JSON::ParserError
  exit 0
end
exit 0 unless data.is_a?(Hash)

tool_name  = data['tool_name'].to_s
command    = data.dig('tool_input', 'command').to_s
event_name = data['hook_event_name'].to_s

# PostToolUse Bash `tool_response`: {stdout, stderr, interrupted, ...}.
# PostToolUseFailure: top-level `error` carries the full output blob.
# Skip on user-interrupt — partial output is not representative.
def extract_post_tool_use_text(tr)
  return '' unless tr.is_a?(Hash)
  return '' if tr['interrupted'] == true

  out = tr['stdout'].to_s
  err = tr['stderr'].to_s
  return out if err.empty?
  return err if out.empty?

  "#{out}\n--- stderr ---\n#{err}"
end

output = case event_name
         when 'PostToolUseFailure'
           data['is_interrupt'] == true ? '' : data['error'].to_s
         else
           extract_post_tool_use_text(data['tool_response'])
         end

exit 0 unless tool_name == 'Bash'
exit 0 if command.empty?

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
exit 0
