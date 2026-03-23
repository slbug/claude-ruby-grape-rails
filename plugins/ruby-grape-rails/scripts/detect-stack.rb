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

# Detection helpers
def gem_present?(content, name)
  # Match exact Gemfile entries like:
  # gem "pg"
  # gem 'pg', '~> 1.5'
  content.match?(/^\s*gem\s+['"]#{Regexp.escape(name)}['"](?=\s*(?:,|$))/)
end

# Detect stack components
detected = []

detected << 'sidekiq' if gem_present?(gemfile, 'sidekiq')
detected << 'hotwire' if gem_present?(gemfile, 'hotwire-rails')
detected << 'karafka' if gem_present?(gemfile, 'karafka')
detected << 'grape' if gem_present?(gemfile, 'grape')
detected << 'mysql' if gem_present?(gemfile, 'mysql2')
detected << 'postgres' if gem_present?(gemfile, 'pg')

# Determine Rails version
rails_version = if defined?(Rails::VERSION)
                  Rails::VERSION::STRING
                elsif File.exist?('Gemfile.lock')
                  # Parse Gemfile.lock as fallback
                  lock_content = File.read('Gemfile.lock')
                  lock_content[/^    rails \((\d+\.\d+\.?\d*)\)/, 1]
                end

# Output for skill consumption
puts "RUBY_VERSION=#{RUBY_VERSION}"
puts "RAILS_VERSION=#{rails_version}" if rails_version
puts "DETECTED_STACK=#{detected.join(',')}"

# Individual flags for easy conditional checks
detected.each do |component|
  puts "HAS_#{component.upcase}=true"
end

exit 0
