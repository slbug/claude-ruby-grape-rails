#!/usr/bin/env bash

# Shared workspace-root resolution for plugin hook scripts.
# Resolution order:
# 1. CLAUDE_PROJECT_DIR environment variable
# 2. Hook payload .cwd (when hook input JSON is available)
# 3. Current working directory
#
# Candidate directories are promoted to the actual project root:
# - nearest ancestor containing Gemfile or .claude
# - otherwise git/worktree root when available
# - otherwise the canonicalized candidate directory itself

read_hook_input() {
  if [[ -t 0 ]]; then
    printf '%s' ""
  else
    cat
  fi
}

library_safe_return() {
  local status="${1:-0}"
  if [[ "${BASH_SOURCE[0]:-}" != "${0:-}" ]]; then
    return "$status"
  fi
  exit "$status"
}

normalize_workspace_dir() {
  local dir="$1"
  [[ -n "$dir" ]] || return 1

  [[ -d "$dir" ]] || return 1
  (cd "$dir" >/dev/null 2>&1 && pwd -P) || return 1
}

ensure_safe_workspace_root() {
  local root="$1"
  [[ -n "$root" ]] || return 1

  if [[ "$root" == "/" ]]; then
    echo "Warning: refusing to use filesystem root as workspace root" >&2
    return 1
  fi

  printf '%s\n' "$root"
}

resolve_project_root_from_dir() {
  local dir="$1"
  local normalized_dir
  local current
  local git_root

  normalized_dir=$(normalize_workspace_dir "$dir") || return 1

  current="$normalized_dir"
  while [[ -n "$current" ]]; do
    if [[ -f "${current}/Gemfile" || -d "${current}/.claude" ]]; then
      ensure_safe_workspace_root "$current"
      return 0
    fi

    [[ "$current" != "/" ]] || break
    current=$(dirname "$current") || break
  done

  if command -v git >/dev/null 2>&1; then
    git_root=$(git -C "$normalized_dir" rev-parse --show-toplevel 2>/dev/null) || git_root=""
    if [[ -n "$git_root" ]]; then
      normalize_workspace_dir "$git_root" | {
        IFS= read -r resolved_git_root || exit 1
        ensure_safe_workspace_root "$resolved_git_root"
      }
      return 0
    fi
  fi

  ensure_safe_workspace_root "$normalized_dir"
}

canonicalize_existing_path() {
  local path="$1"
  local dir
  local base
  local resolved_dir

  [[ -n "$path" ]] || return 1
  [[ -e "$path" ]] || return 1

  dir=$(dirname "$path") || return 1
  base=$(basename "$path") || return 1
  [[ -d "$dir" ]] || return 1

  resolved_dir=$(cd "$dir" >/dev/null 2>&1 && pwd -P) || return 1
  printf '%s/%s\n' "$resolved_dir" "$base"
}

resolve_workspace_file_path() {
  local root="$1"
  local input_path="$2"
  local candidate

  [[ -n "$root" && -n "$input_path" ]] || return 1
  if [[ "$input_path" == /* ]]; then
    candidate="$input_path"
  else
    candidate="${root}/${input_path#./}"
  fi

  canonicalize_existing_path "$candidate"
}

is_path_within_root() {
  local root="$1"
  local path="$2"
  local normalized_root
  local normalized_path

  normalized_root=$(normalize_workspace_dir "$root") || return 1
  normalized_path=$(canonicalize_existing_path "$path") || return 1

  [[ "$normalized_path" == "$normalized_root" || "$normalized_path" == "${normalized_root}/"* ]]
}

resolve_workspace_root() {
  local input="${1:-${CLAUDE_HOOK_INPUT:-}}"
  local root="${CLAUDE_PROJECT_DIR:-}"

  if [[ -n "$root" ]]; then
    if resolve_project_root_from_dir "$root"; then
      return 0
    fi
  fi

  if [[ -n "$input" ]] && command -v jq >/dev/null 2>&1; then
    root=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null) || root=""
    if [[ -n "$root" ]]; then
      if resolve_project_root_from_dir "$root"; then
        return 0
      fi
    fi
  fi

  resolve_project_root_from_dir "${PWD:-.}"
}

normalize_hook_mode() {
  case "${1:-}" in
    strict|STRICT|Strict) printf '%s\n' "strict" ;;
    *) printf '%s\n' "default" ;;
  esac
}

resolve_hook_mode() {
  local root="${1:-$(resolve_workspace_root)}"
  local mode="${RUBY_PLUGIN_HOOK_MODE:-}"
  local claude_dir
  local mode_file

  if [[ -n "$mode" ]]; then
    normalize_hook_mode "$mode"
    return 0
  fi

  claude_dir="${root}/.claude"
  [[ ! -L "$claude_dir" ]] || {
    printf '%s\n' "default"
    return 0
  }

  mode_file="${claude_dir}/ruby-plugin-hook-mode"
  if [[ -f "$mode_file" && ! -L "$mode_file" ]]; then
    if IFS= read -r mode < "$mode_file"; then
      normalize_hook_mode "$mode"
      return 0
    fi
  fi

  printf '%s\n' "default"
}
