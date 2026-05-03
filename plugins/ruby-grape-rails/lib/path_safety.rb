# frozen_string_literal: true

require 'pathname'

# Path-safety helpers for plugin Ruby bin/ scripts that write into
# user-controlled paths under .claude/. Mirrors the bash helpers in
# hooks/scripts/workspace-root-lib.sh (canonicalize_existing_path,
# is_path_within_root) and the per-script `[[ ! -L "$dir" ]]` ancestor
# checks. Stdlib only.
#
# Threat model: a path that is lexically inside the repo (e.g.
# repo/.claude/reviews/slug/RUN-CURRENT.json) can still resolve outside
# the repo if any ancestor is a symlink. mkdir_p / rename / open(W)
# follow symlinks during traversal, so writes can land in
# attacker-chosen locations even when the input path looks contained.
#
# Two complementary guards:
#
#   reject_symlink_ancestors!  Fail-closed lexical walk from path's
#                              parent up to stop_at, raising on the
#                              first symlinked ancestor. Use BEFORE
#                              mkdir_p / open / rename.
#
#   path_within_root?          Canonical containment check using
#                              canonical_existing_or_deepest on both
#                              args. Tolerates macOS /tmp → /private/tmp
#                              and similar OS-level symlink prefixes.
module RubyGrapeRails
  module PathSafety
    module_function

    MAX_LINK_DEPTH = 40

    class SymlinkAncestorError < StandardError
    end

    # Walk from File.dirname(path) upward toward stop_at; raise if any
    # ancestor is a symlink. Operates lexically (no symlink resolution),
    # so it catches symlinks on the path that mkdir_p would otherwise
    # follow. Requires path to be lexically within stop_at.
    def reject_symlink_ancestors!(path, stop_at:)
      abs = File.expand_path(path)
      stop = File.expand_path(stop_at)
      unless abs == stop || abs.start_with?("#{stop}/")
        raise SymlinkAncestorError, "path not lexically within stop_at: #{abs} ⊄ #{stop}"
      end

      cur = File.dirname(abs)
      depth = 0
      while cur != stop
        depth += 1
        if depth > MAX_LINK_DEPTH
          raise SymlinkAncestorError,
                "ancestor walk exceeded MAX_LINK_DEPTH (#{MAX_LINK_DEPTH}) for #{abs}"
        end
        raise SymlinkAncestorError, "symlinked ancestor: #{cur} (in path #{abs})" if File.symlink?(cur)

        parent = File.dirname(cur)
        raise SymlinkAncestorError, "walked past stop_at without finding it: #{abs}" if parent == cur

        cur = parent
      end
    end

    # Realpath if path exists; else realpath the deepest existing
    # ancestor and re-append the missing tail. Returns the lexical
    # input on resolution failure (caller should pair with
    # reject_symlink_ancestors! for fail-closed semantics).
    def canonical_existing_or_deepest(path)
      abs = File.expand_path(path)
      return File.realpath(abs) if File.exist?(abs)

      cur = abs
      tail = []
      depth = 0
      loop do
        depth += 1
        return abs if depth > MAX_LINK_DEPTH

        tail.unshift(File.basename(cur))
        parent = File.dirname(cur)
        return abs if parent == cur

        cur = parent
        return File.join(File.realpath(cur), *tail) if File.exist?(cur)
      end
    rescue StandardError
      File.expand_path(path)
    end

    # Containment check resilient to existing symlinked ancestors
    # (e.g. macOS /tmp → /private/tmp). Use AFTER reject_symlink_ancestors!
    # so any symlink on the path has already been refused.
    def path_within_root?(path, root)
      resolved_path = canonical_existing_or_deepest(path)
      resolved_root = canonical_existing_or_deepest(root)
      return true if resolved_path == resolved_root

      resolved_path.start_with?("#{resolved_root}/")
    end
  end
end
