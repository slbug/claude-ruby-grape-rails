# frozen_string_literal: true

require 'open3'
require 'pathname'

# Shared repo-root resolution for plugin Ruby bin/ scripts.
#
# Mirrors the canonical bash precedence (workspace-root-lib.sh
# resolve_workspace_root) but as a stdlib-only Ruby module. Each
# caller passes its own start_dir (typically Dir.pwd) so multi-repo
# workspaces resolve to the repo enclosing the call site.
#
# Resolution precedence (matches existing bin/extract-permissions):
#   1. nearest ascended dir containing `.git/`
#   2. nearest ascended dir containing `.claude/settings(.local)?.json`
#   3. `git -C <start_dir> rev-parse --show-toplevel` output
#   4. nearest ascended dir containing `Gemfile`
#   5. start_dir itself (last resort)
module RubyGrapeRails
  module RepoRoot
    module_function

    def find(start_dir)
      path = Pathname.new(start_dir).expand_path
      git_root = git_toplevel(path)
      home_dir = Dir.home
      settings_candidate = nil
      gemfile_candidate = nil

      path.ascend do |candidate|
        claude_settings = (candidate / '.claude/settings.json').file? ||
                          (candidate / '.claude/settings.local.json').file?
        next if candidate.to_s == home_dir && claude_settings
        next if git_root && candidate.to_s != git_root && !candidate.to_s.start_with?("#{git_root}/")

        return candidate.to_s if (candidate / '.git').exist?

        settings_candidate ||= candidate.to_s if claude_settings
        gemfile_candidate ||= candidate.to_s if (candidate / 'Gemfile').file?

        break if git_root && candidate.to_s == git_root
      end

      return settings_candidate if settings_candidate
      return git_root if git_root
      return gemfile_candidate if gemfile_candidate

      start_dir.to_s
    end

    def canonical(repo_root)
      Pathname.new(repo_root).expand_path.realpath.to_s
    rescue StandardError
      Pathname.new(repo_root).expand_path.to_s
    end

    def git_toplevel(path)
      root, status = Open3.capture2e('git', '-C', path.to_s, 'rev-parse', '--show-toplevel')
      normalized = root.strip
      return nil if !status.success? || normalized.empty?

      normalized
    rescue StandardError
      nil
    end
  end
end
