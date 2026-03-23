#!/usr/bin/env ruby
# frozen_string_literal: true

# Detect optional stack dependencies for /rb:init
# Outputs simple "key=value" pairs for consumption by init skill

require 'fileutils'

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

# Detect stack components
detected = []
versions = {}

{
  'rails' => 'rails',
  'grape' => 'grape',
  'sidekiq' => 'sidekiq',
  'karafka' => 'karafka',
  'hotwire' => 'hotwire-rails',
  'mysql' => 'mysql2',
  'postgres' => 'pg'
}.each do |component, gem_name|
  next unless gem_present?(gemfile, gem_name)

  detected << component
  version = lock_version(lockfile, gem_name)
  versions[component] = version if version
end

# Determine Rails version
rails_version = if defined?(Rails::VERSION)
                  Rails::VERSION::STRING
                else
                  versions['rails']
                end

# Output for skill consumption
puts "RUBY_VERSION=#{RUBY_VERSION}"
puts "RAILS_VERSION=#{rails_version}" if rails_version
puts "GRAPE_VERSION=#{versions['grape']}" if versions['grape']
puts "SIDEKIQ_VERSION=#{versions['sidekiq']}" if versions['sidekiq']
puts "KARAFKA_VERSION=#{versions['karafka']}" if versions['karafka']
puts "HOTWIRE_VERSION=#{versions['hotwire']}" if versions['hotwire']
puts "DETECTED_STACK=#{detected.join(',')}"

# Individual flags for easy conditional checks
detected.each do |component|
  puts "HAS_#{component.upcase}=true"
end

exit 0
