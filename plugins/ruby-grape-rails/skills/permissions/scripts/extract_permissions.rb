#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'optparse'
require 'pathname'
require 'shellwords'
require 'time'

options = {
  days: 14,
  json: false,
  limit: 30,
  repo_only: false
}

OptionParser.new do |parser|
  parser.banner = 'Usage: extract_permissions.rb [--days N] [--json] [--limit N] [--repo-only]'

  parser.on('--days N', Integer, 'Only scan sessions from the last N days') do |days|
    options[:days] = days
  end

  parser.on('--json', 'Emit machine-readable JSON') do
    options[:json] = true
  end

  parser.on('--limit N', Integer, 'Limit text output to the top N groups (default: 30)') do |limit|
    options[:limit] = limit
  end

  parser.on('--repo-only', 'Ignore ~/.claude/settings.json and only use repo-local settings') do
    options[:repo_only] = true
  end
end.parse!

if options[:days].negative?
  warn '--days must be zero or greater'
  exit 1
end

if options[:limit] <= 0
  warn '--limit must be greater than zero'
  exit 1
end

def find_repo_root(start_dir)
  path = Pathname.new(start_dir).expand_path
  git_root = begin
    root = `git -C #{Shellwords.escape(path.to_s)} rev-parse --show-toplevel 2>/dev/null`.strip
    root unless root.empty?
  rescue StandardError
    nil
  end
  home_dir = Dir.home
  settings_candidate = nil
  gemfile_candidate = nil

  path.ascend do |candidate|
    claude_settings = (candidate + '.claude/settings.json').file? ||
                      (candidate + '.claude/settings.local.json').file?
    next if candidate.to_s == home_dir && claude_settings

    if git_root && candidate.to_s != git_root && !candidate.to_s.start_with?("#{git_root}/")
      next
    end

    return candidate.to_s if (candidate + '.git').exist?
    settings_candidate ||= candidate.to_s if claude_settings
    gemfile_candidate ||= candidate.to_s if (candidate + 'Gemfile').file?

    break if git_root && candidate.to_s == git_root
  end

  return settings_candidate if settings_candidate
  return git_root if git_root
  return gemfile_candidate if gemfile_candidate

  start_dir
end

def positive_env_int(name, default)
  raw = ENV[name]
  return default if raw.nil? || raw.empty?

  value = Integer(raw, exception: false)
  return default unless value && value.positive?

  value
end

def claude_project_slug(repo_root)
  repo_root.tr('/:\\', '-')
end

def load_permissions(settings_path)
  return { allow: [], deny: [] } unless File.file?(settings_path)

  data = JSON.parse(File.read(settings_path))
  permissions = data.fetch('permissions', {})

  {
    allow: Array(permissions['allow']).grep(String),
    deny: Array(permissions['deny']).grep(String)
  }
rescue JSON::ParserError, Errno::ENOENT
  { allow: [], deny: [] }
end

def permission_to_glob(permission)
  return '*' if ['Bash', 'Bash(*)'].include?(permission)
  return unless permission.start_with?('Bash(') && permission.end_with?(')')

  pattern = permission[5...-1]
  pattern.sub(/:\*\z/, ' *')
end

def covered_by_patterns?(command, patterns)
  patterns.any? { |pattern| File.fnmatch?(pattern, command) }
end

def normalized_command_for_coverage(command)
  first_line = command.lines.first.to_s.strip
  return first_line if first_line.empty?

  tokens =
    begin
      Shellwords.split(first_line)
    rescue ArgumentError
      first_line.split(/\s+/)
    end

  core_tokens = tokens.dup
  core_tokens.shift while core_tokens.first == 'env'
  core_tokens = core_tokens.drop_while { |token| token.match?(/\A[A-Za-z_][A-Za-z0-9_]*=.*/) }
  core_tokens = tokens if core_tokens.empty?
  core_tokens.join(' ')
end

def command_group(command)
  first_line = command.lines.first.to_s.strip
  return first_line if first_line.empty?

  tokens =
    begin
      Shellwords.split(first_line)
    rescue ArgumentError
      first_line.split(/\s+/)
    end

  core_tokens = tokens.dup
  core_tokens.shift while core_tokens.first == 'env'
  core_tokens = core_tokens.drop_while { |token| token.match?(/\A[A-Za-z_][A-Za-z0-9_]*=.*/) }
  core_tokens = tokens if core_tokens.empty?
  return first_line if core_tokens.empty?

  if core_tokens[0] == 'bundle' && core_tokens[1] == 'exec'
    if core_tokens[2] == 'rails' && core_tokens[3]
      core_tokens[0, 4].join(' ')
    elsif core_tokens[2]
      core_tokens[0, 3].join(' ')
    else
      core_tokens.join(' ')
    end
  elsif %w[git rails bin/rails rake make just npm yarn pnpm lefthook].include?(core_tokens[0])
    core_tokens[1] ? core_tokens[0, 2].join(' ') : core_tokens[0]
  elsif %w[ruby python python3 node].include?(core_tokens[0])
    if core_tokens[1] && !core_tokens[1].start_with?('-')
      core_tokens[0, 2].join(' ')
    else
      core_tokens[0]
    end
  elsif core_tokens[0].start_with?('bin/') || core_tokens[0].start_with?('script/')
    core_tokens[1] ? core_tokens[0, 2].join(' ') : core_tokens[0]
  else
    core_tokens[0]
  end
end

def extract_bash_commands(entry)
  return [] unless entry['type'] == 'assistant'

  Array(entry.dig('message', 'content')).filter_map do |block|
    next unless block.is_a?(Hash)
    next unless block['type'] == 'tool_use' && block['name'] == 'Bash'

    command = block.dig('input', 'command').to_s.strip
    next if command.empty?

    command.lines.first.to_s.strip
  end
end

repo_root = find_repo_root(Dir.pwd)
project_slug = claude_project_slug(repo_root)
project_transcript_glob = File.expand_path("~/.claude/projects/#{project_slug}/*.jsonl")
settings_sources = [
  File.join(repo_root, '.claude/settings.json'),
  File.join(repo_root, '.claude/settings.local.json')
]
settings_sources.unshift(File.expand_path('~/.claude/settings.json')) unless options[:repo_only]

all_allow = []
all_deny = []
settings_sources.each do |path|
  permissions = load_permissions(path)
  all_allow.concat(permissions[:allow])
  all_deny.concat(permissions[:deny])
end

allow_globs = all_allow.filter_map { |permission| permission_to_glob(permission) }
deny_globs = all_deny.filter_map { |permission| permission_to_glob(permission) }

cutoff = Time.now - (options[:days] * 86_400)
session_files = Dir.glob(project_transcript_glob)
max_session_files = positive_env_int('RUBY_PLUGIN_PERMISSIONS_MAX_SESSION_FILES', 200)
max_lines_per_file = positive_env_int('RUBY_PLUGIN_PERMISSIONS_MAX_LINES_PER_FILE', 10_000)
recent_candidates = session_files.select { |path| File.file?(path) && File.mtime(path) > cutoff }
recent_files = recent_candidates.sort_by { |path| File.mtime(path) }.reverse.first(max_session_files)
truncated_session_files = [recent_candidates.length - recent_files.length, 0].max

group_counts = Hash.new(0)
examples = {}
total_bash_commands = 0
ignored_denied = 0
line_capped_files = 0

recent_files.each do |session_file|
  file_truncated = false

  File.foreach(session_file).with_index do |line, index|
    if index >= max_lines_per_file
      file_truncated = true
      break
    end

    begin
      entry = JSON.parse(line)
    rescue JSON::ParserError
      next
    end

    extract_bash_commands(entry).each do |command|
      total_bash_commands += 1
      normalized_command = normalized_command_for_coverage(command)

      if covered_by_patterns?(normalized_command, deny_globs)
        ignored_denied += 1
        next
      end

      next if covered_by_patterns?(normalized_command, allow_globs)

      group = command_group(normalized_command)
      group_counts[group] += 1
      examples[group] ||= normalized_command
    end
  end
  line_capped_files += 1 if file_truncated
rescue Errno::ENOENT
  next
end

deprecated_patterns = all_allow.select do |permission|
  permission.start_with?('Bash(') && permission.include?(':*)')
end.uniq.sort
garbage_patterns = all_allow.select do |permission|
  permission.match?(/\ABash\((done|fi|then|do|EOF|EOT|RUBY|BASH)\)\z/) ||
    permission.include?('__NEW_LINE_')
end.uniq.sort

duplicate_patterns = all_allow
                     .group_by { |permission| permission }
                     .select { |_permission, entries| entries.length > 1 }
                     .keys
                     .sort

report = {
  repo_root: repo_root,
  project_slug: project_slug,
  days: options[:days],
  scanned_sessions: recent_files.length,
  available_sessions_in_window: recent_candidates.length,
  truncated_session_files: truncated_session_files,
  line_capped_files: line_capped_files,
  max_lines_per_file: max_lines_per_file,
  settings_scope: options[:repo_only] ? 'repo-only' : 'repo+global',
  scanned_files: recent_files,
  total_bash_commands: total_bash_commands,
  ignored_denied_commands: ignored_denied,
  uncovered_command_groups: group_counts.length,
  total_avoidable_prompts: group_counts.values.sum,
  uncovered_groups: group_counts.sort_by { |_group, count| -count }.map do |group, count|
    {
      group: group,
      count: count,
      example: examples[group].to_s[0, 300]
    }
  end,
  deprecated_patterns: deprecated_patterns,
  garbage_patterns: garbage_patterns,
  duplicate_patterns: duplicate_patterns
}

if options[:json]
  puts JSON.pretty_generate(report)
  exit 0
end

puts "Repo root: #{repo_root}"
puts "Project transcript scope: #{project_slug}"
puts "Settings scope: #{options[:repo_only] ? 'repo-only' : 'repo + ~/.claude/settings.json'}"
puts "Sessions scanned: #{recent_files.length} (last #{options[:days]} days)"
puts "Additional recent sessions skipped by cap: #{truncated_session_files}" if truncated_session_files.positive?
puts "Files capped at #{max_lines_per_file} lines: #{line_capped_files}" if line_capped_files.positive?
puts 'WARNING: transcript scan was truncated by caps; recommendations are partial.' if truncated_session_files.positive? || line_capped_files.positive?
puts "Total Bash tool calls seen: #{total_bash_commands}"
puts "Uncovered command groups: #{group_counts.length}"
puts "Total avoidable prompts: #{group_counts.values.sum}"
puts "Commands ignored due to existing deny rules: #{ignored_denied}" if ignored_denied.positive?
puts "Deprecated :* patterns to fix: #{deprecated_patterns.length}" if deprecated_patterns.any?
puts "Garbage entries to review: #{garbage_patterns.length}" if garbage_patterns.any?
puts "Duplicate entries to review: #{duplicate_patterns.length}" if duplicate_patterns.any?
puts

report[:uncovered_groups].first(options[:limit]).each do |entry|
  puts format('%4<count>dx  %<group>s', count: entry[:count], group: entry[:group])
  puts "       e.g.: #{entry[:example][0, 140]}" if entry[:example] && entry[:example] != entry[:group]
end

if deprecated_patterns.any?
  puts
  puts '=== DEPRECATED :* PATTERNS ==='
  deprecated_patterns.each do |permission|
    puts "  #{permission} -> #{permission.sub(':*)', ' *)')}"
  end
end

if garbage_patterns.any?
  puts
  puts '=== GARBAGE ENTRIES ==='
  garbage_patterns.each do |permission|
    puts "  #{permission}"
  end
end

if duplicate_patterns.any?
  puts
  puts '=== DUPLICATE ENTRIES ==='
  duplicate_patterns.each do |permission|
    puts "  #{permission}"
  end
end
