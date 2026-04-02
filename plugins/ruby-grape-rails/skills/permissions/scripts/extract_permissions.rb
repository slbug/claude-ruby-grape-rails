#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'optparse'
require 'open3'
require 'pathname'
require 'shellwords'
require 'time'
require 'digest'

options = {
  days: 14,
  json: false,
  limit: 30,
  include_global: false,
  dry_run: false
}

OptionParser.new do |parser|
  parser.banner = 'Usage: extract_permissions.rb [--days N] [--json] [--limit N] [--include-global] [--dry-run]'

  parser.on('--days N', Integer, 'Only scan sessions from the last N days') do |days|
    options[:days] = days
  end

  parser.on('--json', 'Emit machine-readable JSON') do
    options[:json] = true
  end

  parser.on('--limit N', Integer, 'Limit text output to the top N groups (default: 30)') do |limit|
    options[:limit] = limit
  end

  parser.on('--include-global', 'Also include ~/.claude/settings.json in addition to repo-local settings') do
    options[:include_global] = true
  end

  parser.on('--repo-only', 'Only use repo-local settings (default; kept for backward compatibility)') do
    # This is the default behavior, flag kept for backward compatibility
  end

  parser.on('--dry-run', 'Accepted for skill parity; extractor output is already read-only') do
    options[:dry_run] = true
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
    root, status = Open3.capture2e('git', '-C', path.to_s, 'rev-parse', '--show-toplevel')
    normalized_root = root.strip
    normalized_root unless !status.success? || normalized_root.empty?
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

    next if git_root && candidate.to_s != git_root && !candidate.to_s.start_with?("#{git_root}/")

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

def canonical_repo_root(repo_root)
  Pathname.new(repo_root).expand_path.realpath.to_s
rescue StandardError
  Pathname.new(repo_root).expand_path.to_s
end

def claude_project_slug(repo_root)
  canonical_root = canonical_repo_root(repo_root)
  base = canonical_root.tr('/:\\', '-')
  digest = Digest::SHA256.hexdigest(canonical_root)[0, 12]
  "#{base}-#{digest}"
end

def project_transcript_files(project_slug)
  project_dir = File.join(transcript_projects_root, project_slug)
  return [] unless File.directory?(project_dir)

  Dir.children(project_dir)
     .grep(/\.jsonl\z/)
     .map { |entry| File.join(project_dir, entry) }
     .select do |path|
       stat = File.lstat(path)
       stat.file? && !stat.symlink?
     rescue Errno::ENOENT, Errno::EACCES, Errno::EPERM
       false
     end
     .sort
rescue Errno::ENOENT
  []
end

def transcript_projects_root
  configured_root = ENV['RUBY_PLUGIN_PERMISSIONS_PROJECTS_DIR'].to_s.strip
  configured_root = ENV['CLAUDE_PROJECTS_DIR'].to_s.strip if configured_root.empty?
  configured_root = '~/.claude/projects' if configured_root.empty?

  File.expand_path(configured_root)
end

def mode_bit_readable_file?(path)
  stat = File.stat(path)
  return false if (stat.mode & 0o444).zero?

  true
rescue Errno::ENOENT
  nil
rescue Errno::EACCES, Errno::EPERM
  false
end

def regular_non_symlink_file?(path)
  stat = File.lstat(path)
  stat.file? && !stat.symlink?
rescue Errno::ENOENT
  nil
rescue Errno::EACCES, Errno::EPERM
  false
end

def load_permissions(settings_path)
  file_type = regular_non_symlink_file?(settings_path)
  return { allow: [], deny: [], invalid: false } if file_type.nil?
  return { allow: [], deny: [], invalid: true } unless file_type

  readability = mode_bit_readable_file?(settings_path)
  return { allow: [], deny: [], invalid: false } if readability.nil?
  return { allow: [], deny: [], invalid: true } unless readability

  data = JSON.parse(File.read(settings_path))
  return { allow: [], deny: [], invalid: true } unless data.is_a?(Hash)

  permissions = data.fetch('permissions', {})
  return { allow: [], deny: [], invalid: true } unless permissions.is_a?(Hash)

  {
    allow: Array(permissions['allow']).grep(String),
    deny: Array(permissions['deny']).grep(String),
    invalid: false
  }
rescue JSON::ParserError
  { allow: [], deny: [], invalid: true }
rescue Errno::ENOENT
  { allow: [], deny: [], invalid: false }
rescue Errno::EACCES, Errno::EPERM
  { allow: [], deny: [], invalid: true }
end

def permission_to_glob(permission)
  return '*' if ['Bash', 'Bash(*)'].include?(permission)
  return unless permission.start_with?('Bash(') && permission.end_with?(')')

  pattern = permission[5...-1]
  # Normalize the pattern the same way commands are normalized
  pattern = normalized_command_for_coverage(pattern)
  pattern.sub(/:\*\z/, ' *')
end

def covered_by_patterns?(command, patterns)
  patterns.any? do |pattern|
    File.fnmatch?(pattern, command) ||
      (pattern.end_with?(' *') && command == pattern[0...-2])
  end
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
  core_tokens[0] = core_tokens[0].sub(%r{\A\./(?=(bin|script)/)}, '') unless core_tokens.empty?
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

  core_tokens[0] = core_tokens[0].sub(%r{\A\./(?=(bin|script)/)}, '')

  if core_tokens[0] == 'git'
    option_takes_value = lambda do |token|
      %w[
        -C
        -c
        --git-dir
        --work-tree
        --namespace
        --super-prefix
        --config-env
        --exec-path
      ].include?(token)
    end

    index = 1
    while index < core_tokens.length
      token = core_tokens[index]
      break unless token.start_with?('-')

      index += if option_takes_value.call(token)
                 2
               else
                 1
               end
    end

    return core_tokens[index] ? "git #{core_tokens[index]}" : 'git'
  end

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
    if core_tokens[1] == '-m' && core_tokens[2]
      core_tokens[0, 3].join(' ')
    elsif core_tokens[1] == '-e'
      core_tokens[0, 2].join(' ')
    elsif core_tokens[1] && !core_tokens[1].start_with?('-')
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

def split_shell_commands(command)
  normalized = command.gsub(/\\\n/, ' ')
  parser_segments = split_shell_commands_with_shfmt(normalized)
  return parser_segments if parser_segments.any?
  return [normalized.strip] if normalized.match?(/(^|[[:space:];(|&])<<-?\s*['"]?[A-Za-z_][A-Za-z0-9_]*['"]?/)

  commands = []
  current = +''
  in_single = false
  in_double = false
  escaped = false
  index = 0

  while index < normalized.length
    char = normalized[index]
    next_char = normalized[index + 1]

    if escaped
      current << char
      escaped = false
      index += 1
      next
    end

    if in_single
      current << char
      in_single = false if char == "'"
      index += 1
      next
    end

    if in_double
      current << char
      if char == '\\' && next_char
        current << next_char
        index += 2
        next
      end
      in_double = false if char == '"'
      index += 1
      next
    end

    case char
    when '\\'
      escaped = true
      current << char
      index += 1
    when '#'
      if current.empty? || current[-1].match?(/[[:space:];|&()]/)
        index += 1
        index += 1 while index < normalized.length && normalized[index] != "\n"
      else
        current << char
        index += 1
      end
    when "'"
      in_single = true
      current << char
      index += 1
    when '"'
      in_double = true
      current << char
      index += 1
    when ';', "\n"
      stripped = current.strip
      commands << stripped unless stripped.empty?
      current = +''
      index += 1
    when '&'
      prev_char = index.positive? ? normalized[index - 1] : nil
      if next_char == '&'
        stripped = current.strip
        commands << stripped unless stripped.empty?
        current = +''
        index += 2
      elsif ['>', '<'].include?(prev_char) || next_char == '>'
        current << char
        index += 1
      else
        stripped = current.strip
        commands << stripped unless stripped.empty?
        current = +''
        index += 1
      end
    when '|'
      if next_char == '|'
        stripped = current.strip
        commands << stripped unless stripped.empty?
        current = +''
        index += 2
      else
        stripped = current.strip
        commands << stripped unless stripped.empty?
        current = +''
        index += (next_char == '&' ? 2 : 1)
      end
    else
      current << char
      index += 1
    end
  end

  stripped = current.strip
  commands << stripped unless stripped.empty?
  commands
end

def split_shell_commands_with_shfmt(command)
  stdout, status = Open3.capture2e('shfmt', '--to-json', '-filename', 'hook-input.sh', stdin_data: command)
  return [] unless status.success?

  ast = JSON.parse(stdout)
  Array(ast['Stmts']).filter_map do |stmt|
    start = stmt.dig('Pos', 'Offset')
    stop = stmt.dig('Cmd', 'End', 'Offset') || stmt.dig('End', 'Offset')
    next unless start.is_a?(Integer) && stop.is_a?(Integer) && stop >= start

    segment = command[start...stop].to_s.strip
    next if segment.empty?

    segment
  end
rescue Errno::ENOENT, JSON::ParserError
  []
end

def extract_bash_commands(entry)
  return [] unless entry.is_a?(Hash)
  return [] unless entry['type'] == 'assistant'

  Array(entry.dig('message', 'content')).flat_map do |block|
    next [] unless block.is_a?(Hash)
    next [] unless block['type'] == 'tool_use' && block['name'] == 'Bash'

    command = block.dig('input', 'command').to_s.strip
    next [] if command.empty?

    split_shell_commands(command)
  end
end

repo_root = find_repo_root(Dir.pwd)
project_slug = claude_project_slug(repo_root)
settings_sources = [
  File.join(repo_root, '.claude/settings.json'),
  File.join(repo_root, '.claude/settings.local.json')
]
settings_sources.unshift(File.expand_path('~/.claude/settings.json')) if options[:include_global]

all_allow = []
all_deny = []
invalid_settings_files = []
settings_sources.each do |path|
  permissions = load_permissions(path)
  invalid_settings_files << path if permissions[:invalid]
  all_allow.concat(permissions[:allow])
  all_deny.concat(permissions[:deny])
end

allow_globs = all_allow.filter_map { |permission| permission_to_glob(permission) }
deny_globs = all_deny.filter_map { |permission| permission_to_glob(permission) }

cutoff = Time.now - (options[:days] * 86_400)
session_files = project_transcript_files(project_slug)
max_session_files = positive_env_int('RUBY_PLUGIN_PERMISSIONS_MAX_SESSION_FILES', 200)
max_lines_per_file = positive_env_int('RUBY_PLUGIN_PERMISSIONS_MAX_LINES_PER_FILE', 10_000)
missing_session_files = []
recent_candidates = session_files.filter_map do |path|
  next unless File.file?(path)

  mtime = File.mtime(path)
  next unless mtime > cutoff

  { path: path, mtime: mtime }
rescue Errno::ENOENT
  missing_session_files << path unless missing_session_files.include?(path)
  next
end
recent_files = recent_candidates.sort_by do |entry|
  entry[:mtime]
end.reverse.first(max_session_files).map { |entry| entry[:path] }
truncated_session_files = [recent_candidates.length - recent_files.length, 0].max

group_counts = Hash.new(0)
examples = {}
total_bash_commands = 0
ignored_denied = 0
line_capped_files = 0
malformed_lines = 0

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
      malformed_lines += 1
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
  missing_session_files << session_file unless missing_session_files.include?(session_file)
  next
end

all_patterns = all_allow + all_deny

deprecated_patterns = all_patterns.select do |permission|
  permission.start_with?('Bash(') && permission.include?(':*)')
end.uniq.sort
garbage_patterns = all_patterns.select do |permission|
  permission.match?(/\ABash\((done|fi|then|do|EOF|EOT|RUBY|BASH)\)\z/) ||
    permission.include?('__NEW_LINE_')
end.uniq.sort

duplicate_patterns = all_patterns
                     .group_by { |permission| permission }
                     .select { |_permission, entries| entries.length > 1 }
                     .keys
                     .sort

report = {
  repo_root: repo_root,
  project_slug: project_slug,
  transcript_projects_root: transcript_projects_root,
  days: options[:days],
  settings_sources: settings_sources,
  scanned_sessions: recent_files.length,
  available_sessions_in_window: recent_candidates.length,
  truncated_session_files: truncated_session_files,
  line_capped_files: line_capped_files,
  max_lines_per_file: max_lines_per_file,
  malformed_lines: malformed_lines,
  invalid_settings_files: invalid_settings_files,
  missing_session_files: missing_session_files,
  settings_scope: options[:include_global] ? 'repo+global' : 'repo-only',
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
puts "Transcript projects root: #{transcript_projects_root}"
puts "Settings scope: #{options[:include_global] ? 'repo + ~/.claude/settings.json' : 'repo-only'}"
puts "Settings sources considered: #{settings_sources.join(', ')}"
if options[:include_global]
  puts 'WARNING: including ~/.claude/settings.json can pull unrelated personal permissions into this repo audit.'
end
puts 'Dry-run: extractor is read-only; no settings changes were written.' if options[:dry_run]
puts "Sessions scanned: #{recent_files.length} (last #{options[:days]} days)"
puts "Additional recent sessions skipped by cap: #{truncated_session_files}" if truncated_session_files.positive?
puts "Files capped at #{max_lines_per_file} lines: #{line_capped_files}" if line_capped_files.positive?
puts "Malformed transcript lines skipped: #{malformed_lines}" if malformed_lines.positive?
puts "Invalid or unreadable settings files ignored: #{invalid_settings_files.length}" if invalid_settings_files.any?
puts "Transcript files skipped after disappearing: #{missing_session_files.length}" if missing_session_files.any?
if truncated_session_files.positive? || line_capped_files.positive?
  puts 'WARNING: transcript scan was truncated by caps; recommendations are partial.'
end
puts 'WARNING: malformed transcript lines were skipped; recommendations may be incomplete.' if malformed_lines.positive?
if invalid_settings_files.any?
  puts 'WARNING: invalid or unreadable settings files were ignored; permission coverage may be incomplete.'
end
if missing_session_files.any?
  puts 'WARNING: some transcript files disappeared during scanning; recommendations may be incomplete.'
end
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
