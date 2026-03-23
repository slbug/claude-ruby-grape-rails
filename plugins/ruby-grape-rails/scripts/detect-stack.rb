#!/usr/bin/env ruby
# frozen_string_literal: true

# Detect stack dependencies and repository layout for /rb:init.
# Outputs simple "key=value" pairs for consumption by init skill.

# Only run if Gemfile exists
unless File.exist?('Gemfile')
  puts '# No Gemfile found'
  exit 0
end

gemfile = File.read('Gemfile')
lockfile = File.exist?('Gemfile.lock') ? File.read('Gemfile.lock') : ''

# Detection helpers
def gem_present?(content, name)
  # Match exact Gemfile entries like:
  # gem "pg"
  # gem 'pg', '~> 1.5'
  # gem 'pg' # needed for postgres
  content.match?(/^\s*gem\s+['"]#{Regexp.escape(name)}['"](?=\s*(?:,|#|$))/)
end

def lock_version(content, name)
  content[/^\s{4}#{Regexp.escape(name)} \(([^)]+)\)$/, 1]
end

def directory_glob(*patterns)
  patterns.flat_map { |pattern| Dir.glob(pattern) }
          .select do |path|
            begin
              stat = File.lstat(path)
              stat.directory? && !stat.symlink?
            rescue SystemCallError
              false
            end
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
  package_root_patterns.flat_map { |root| Dir.glob("#{root}/*/package.yml") }
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
  'hotwire' => 'hotwire-rails',
  'solid_queue' => 'solid_queue',
  'mysql' => 'mysql2',
  'postgres' => 'pg'
}.each do |component, gem_name|
  next unless gem_present?(gemfile, gem_name)

  detected << component
  version = lock_version(lockfile, gem_name)
  versions[component] = version if version
end

if gem_present?(gemfile, 'redis') || gem_present?(gemfile, 'redis-client')
  detected << 'redis'
  versions['redis'] = lock_version(lockfile, 'redis') || lock_version(lockfile, 'redis-client')
end

orms << 'active_record' if gem_present?(gemfile, 'rails') || gem_present?(gemfile, 'activerecord')
orms << 'sequel' if gem_present?(gemfile, 'sequel') || gem_present?(gemfile, 'sequel-rails')
orms.uniq!
versions['activerecord'] = lock_version(lockfile, 'activerecord') if gem_present?(gemfile, 'activerecord')
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

detected_rails_components = rails_component_gems.select { |gem_name| gem_present?(gemfile, gem_name) }
rails_components = detected_rails_components.any?
full_rails_app = gem_present?(gemfile, 'rails')
detected.uniq!

# Determine Rails version
rails_version = if defined?(Rails::VERSION)
                  Rails::VERSION::STRING
                else
                  versions['rails']
                end

package_dirs = modular_package_dirs
packwerk = File.exist?('packwerk.yml')
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

puts "RUBY_VERSION=#{RUBY_VERSION}"
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

exit 0
