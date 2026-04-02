#!/usr/bin/env ruby
# frozen_string_literal: true

require 'pathname'
require 'shellwords'

# Detect stack dependencies and repository layout for /rb:init.
# Outputs simple "key=value" pairs for consumption by init skill.

def safe_manifest_file?(path)
  return false unless File.file?(path) && !File.symlink?(path)

  stat = File.stat(path)
  return false if (stat.mode & 0o444).zero?

  true
rescue SystemCallError
  false
end

def safe_read_file(path)
  return nil unless safe_manifest_file?(path)

  File.read(path)
rescue SystemCallError
  nil
end

def git_repo_root(start_dir)
  path = Pathname.new(start_dir).expand_path
  root = `git -C #{Shellwords.escape(path.to_s)} rev-parse --show-toplevel 2>/dev/null`.strip
  return nil if root.empty?

  Pathname.new(root).expand_path.to_s
rescue StandardError
  nil
end

def declared_ruby_version(gemfile_content)
  ruby_version_file = safe_read_file('.ruby-version')
  if ruby_version_file
    version = ruby_version_file.each_line.map(&:strip).find { |line| !line.empty? && !line.start_with?('#') }
    return version unless version.nil? || version.empty?
  end

  tool_versions = safe_read_file('.tool-versions')
  if tool_versions
    tool_versions.each_line do |line|
      next if line.strip.empty? || line.lstrip.start_with?('#')
      next unless line =~ /^\s*ruby\s+([^\s#]+)/

      return Regexp.last_match(1)
    end
  end

  if gemfile_content && !gemfile_content.empty? && gemfile_content =~ /^\s*ruby\s*(?:\(|\s)\s*['"]([^'"]+)['"]/
    return Regexp.last_match(1)
  end

  nil
end

def manifest_root(start_dir)
  git_root = git_repo_root(start_dir)

  Pathname.new(start_dir).expand_path.ascend do |candidate|
    gemfile = candidate.join('Gemfile')
    gemspecs = Dir.glob(candidate.join('*.gemspec').to_s)

    return candidate.to_s if safe_manifest_file?(gemfile.to_s) ||
                             gemspecs.any? { |path| safe_manifest_file?(path) }

    break if git_root && candidate.to_s == git_root
  end

  nil
end

repo_root = manifest_root(Dir.pwd)
unless repo_root
  puts '# No Gemfile or gemspec found'
  exit 0
end

Dir.chdir(repo_root) do
gemfile = safe_read_file('Gemfile') || ''
lockfile = safe_read_file('Gemfile.lock') || ''
gemspec_contents = Dir.glob('*.gemspec').sort.filter_map do |path|
  next unless safe_manifest_file?(path)

  safe_read_file(path)
end
gemfile_uses_gemspec = if gemfile.empty?
                         gemspec_contents.any?
                       else
                         gemfile.match?(/^\s*gemspec(?:\s*(?:\(|#|$)|$)/)
                       end
project_ruby_version = declared_ruby_version(gemfile)

# Detection helpers
def gem_declared_in_manifest?(content, name)
  content.match?(/^\s*gem\s*(?:\(|\s)\s*['"]#{Regexp.escape(name)}['"](?=\s*(?:,|\)|#|$))/)
end

def gemspec_declares_dependency?(content, name)
  content.match?(
    /^\s*(?:spec|s)?\.?add(?:_runtime|_development)?_dependency\s*(?:\(|\s)\s*['"]#{Regexp.escape(name)}['"](?=\s*(?:,|\)|#|$))/
  )
end

def lock_version(content, name)
  content[/^\s{4}#{Regexp.escape(name)} \(([^)]+)\)$/, 1]
end

def lock_dependency_declared?(content, name)
  in_dependencies = false

  content.each_line do |line|
    if line == "DEPENDENCIES\n"
      in_dependencies = true
      next
    end

    break if in_dependencies && line.match?(/^\S/)

    next unless in_dependencies
    return true if line.match?(/^\s{2}#{Regexp.escape(name)}(?:[[:space:]]|!|\(|$)/)
  end

  false
end

def repo_gem_present?(gemfile_content, lockfile_content, gemspecs, gemfile_uses_gemspec, name)
  return true if gem_declared_in_manifest?(gemfile_content, name)

  return false unless gemfile_uses_gemspec
  return true if gemspecs.any? { |content| gemspec_declares_dependency?(content, name) }

  lock_dependency_declared?(lockfile_content, name)
end

def directory_glob(*patterns)
  patterns.flat_map { |pattern| Dir.glob(pattern) }
          .select do |path|
            stat = File.lstat(path)
            stat.directory? && !stat.symlink?
  rescue SystemCallError
    false
          end
          .uniq
          .sort
end

def regular_file?(path)
  File.lstat(path).file?
rescue SystemCallError
  false
end

def safe_directory?(path)
  stat = File.lstat(path)
  stat.directory? && !stat.symlink?
rescue SystemCallError
  false
end

def package_root_patterns
  [
    'packs',
    'packages',
    'app/packs',
    'app/packages'
  ]
end

def package_content_markers
  %w[
    app
    config
    db
    lib
    spec
    test
    models
    controllers
    services
    workers
    jobs
    policies
    middleware
    public
    serializers
    presenters
    forms
    operations
    commands
    api
    graphql
    channels
    mailers
    views
  ]
end

def soft_package_content_markers
  %w[
    query
    queries
    handler
    handlers
    adapter
    adapters
    consumer
    consumers
    event
    events
    client
    clients
  ]
end

def package_manifests
  package_root_patterns.flat_map { |root| Dir.glob("#{root}/**/package.yml") }
                       .select do |path|
                         regular_file?(path) && safe_directory?(File.dirname(path))
                       end
                       .uniq
                       .sort
end

def package_dir_candidate?(path)
  return true if regular_file?(File.join(path, 'Gemfile'))

  return true if package_content_markers.any? do |entry|
    safe_directory?(File.join(path, entry))
  end

  return true if soft_package_content_markers.any? do |entry|
    safe_directory?(File.join(path, entry))
  end

  # Inside explicit package roots, be softer but still require code/package-ish
  # evidence, not just any arbitrary directory.
  entries = Dir.children(path).reject { |entry| entry.start_with?('.') }
  return false if entries.empty?

  ruby_file_present = entries.any? do |entry|
    child = File.join(path, entry)
    regular_file?(child) && entry.end_with?('.rb', '.rake', '.ru', '.gemspec')
  end
  return true if ruby_file_present

  false
rescue SystemCallError
  false
end

def modular_package_dirs
  dirs = package_manifests.map { |path| File.dirname(path) }

  dirs.concat(
    directory_glob(*package_root_patterns.map { |root| "#{root}/*" }).select do |path|
      package_dir_candidate?(path)
    end
  )

  dirs.uniq.sort
end

# Detect stack components
detected = []
versions = {}
orms = []

{
  'rails' => 'rails',
  'grape' => 'grape',
  'sidekiq' => 'sidekiq',
  'karafka' => 'karafka',
  'solid_queue' => 'solid_queue',
  'mysql' => 'mysql2',
  'postgres' => 'pg'
}.each do |component, gem_name|
  next unless repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, gem_name)

  detected << component
  version = lock_version(lockfile, gem_name)
  versions[component] = version if version
end

hotwire_gems = %w[hotwire-rails turbo-rails stimulus-rails]
hotwire_versions = hotwire_gems.filter_map do |gem_name|
  next unless repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, gem_name)

  [gem_name, lock_version(lockfile, gem_name)]
end
if hotwire_versions.any?
  detected << 'hotwire'
  versions['hotwire'] = hotwire_versions.find { |_name, version| version }&.last
end

if repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, 'redis') ||
   repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, 'redis-client')
  detected << 'redis'
  versions['redis'] = lock_version(lockfile, 'redis') || lock_version(lockfile, 'redis-client')
end

orms << 'active_record' if repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, 'rails') ||
                           repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, 'activerecord')
orms << 'sequel' if repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, 'sequel') ||
                    repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, 'sequel-rails')
orms.uniq!
versions['activerecord'] = lock_version(lockfile, 'activerecord') if repo_gem_present?(gemfile, lockfile,
                                                                                       gemspec_contents, gemfile_uses_gemspec, 'activerecord')
versions['sequel'] = lock_version(lockfile, 'sequel') if orms.include?('sequel')

rails_component_gems = %w[
  activesupport
  activemodel
  activerecord
  actionpack
  actionview
  actionmailer
  actioncable
  activejob
  railties
]

detected_rails_components = rails_component_gems.select do |gem_name|
  repo_gem_present?(gemfile, lockfile, gemspec_contents, gemfile_uses_gemspec, gem_name)
end
rails_components = detected_rails_components.any?
full_rails_app =
  (File.file?('bin/rails') && !File.symlink?('bin/rails')) ||
  (File.file?('script/rails') && !File.symlink?('script/rails')) ||
  (
    %w[config/application.rb config/environment.rb config/boot.rb].all? do |path|
      File.file?(path) && !File.symlink?(path)
    end &&
      Dir.exist?('app') && !File.symlink?('app') &&
      Dir.exist?('config/environments') && !File.symlink?('config/environments')
  )
detected.uniq!

rails_version = versions['rails']

package_dirs = modular_package_dirs
packwerk = safe_manifest_file?('packwerk.yml')
package_layout =
  if packwerk
    'packwerk'
  elsif package_dirs.any?
    'modular_monolith'
  else
    'single_app'
  end

package_query_needed = !packwerk && package_dirs.any?
primary_orm =
  if orms.length == 1
    orms.first
  elsif orms.length > 1
    'mixed'
  else
    'unknown'
  end

# Output for skill consumption
activerecord_version = versions['activerecord'] || rails_version

puts "RUBY_VERSION=#{project_ruby_version || RUBY_VERSION}"
puts "INTERPRETER_RUBY_VERSION=#{RUBY_VERSION}" if project_ruby_version && project_ruby_version != RUBY_VERSION
puts "RAILS_VERSION=#{rails_version}" if rails_version
if orms.include?('active_record')
  if activerecord_version && !activerecord_version.to_s.empty?
    puts "ACTIVERECORD_VERSION=#{activerecord_version}"
  else
    puts 'ACTIVERECORD_VERSION=detected'
  end
end
puts "SEQUEL_VERSION=#{versions['sequel']}" if versions['sequel']
puts "GRAPE_VERSION=#{versions['grape']}" if versions['grape']
puts "SIDEKIQ_VERSION=#{versions['sidekiq']}" if versions['sidekiq']
puts "KARAFKA_VERSION=#{versions['karafka']}" if versions['karafka']
puts "HOTWIRE_VERSION=#{versions['hotwire']}" if versions['hotwire']
puts "DETECTED_STACK=#{detected.join(',')}"
puts "DETECTED_ORMS=#{orms.join(',')}" if orms.any?
puts "RAILS_COMPONENTS=#{rails_components}"
puts "FULL_RAILS_APP=#{full_rails_app}"
puts "PRIMARY_ORM=#{primary_orm}"
puts "PACKAGE_LAYOUT=#{package_layout}"
puts "PACKAGE_LOCATIONS=#{package_dirs.join(',')}" if package_dirs.any?
puts "PACKAGE_QUERY_NEEDED=#{package_query_needed}"
puts "HAS_PACKWERK=#{packwerk}"

# Individual flags for easy conditional checks
detected.each do |component|
  puts "HAS_#{component.upcase}=true"
end

orms.each do |orm|
  puts "HAS_#{orm.upcase}=true"
end

end

exit 0
