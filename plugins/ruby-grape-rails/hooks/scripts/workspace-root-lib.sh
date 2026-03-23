#!/usr/bin/env bash

# Shared workspace-root resolution for plugin hook scripts.
# Resolution order:
# 1. CLAUDE_PROJECT_DIR environment variable
# 2. Hook payload .cwd (when hook input JSON is available)
# 3. Current working directory

normalize_workspace_dir() {
  local dir="$1"
  [[ -n "$dir" ]] || return 1

  if [[ -d "$dir" ]]; then
    (cd "$dir" >/dev/null 2>&1 && pwd -P) || printf '%s\n' "$dir"
    return 0
  fi

  printf '%s\n' "$dir"
}

resolve_workspace_root() {
  local input="${1:-${CLAUDE_HOOK_INPUT:-}}"
  local root="${CLAUDE_PROJECT_DIR:-}"

  if [[ -n "$root" ]]; then
    normalize_workspace_dir "$root"
    return 0
  fi

  if [[ -n "$input" ]] && command -v jq >/dev/null 2>&1; then
    root=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null) || root=""
    if [[ -n "$root" ]]; then
      normalize_workspace_dir "$root"
      return 0
    fi
  fi

  normalize_workspace_dir "${PWD:-.}"
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
  local mode_file

  if [[ -n "$mode" ]]; then
    normalize_hook_mode "$mode"
    return 0
  fi

  mode_file="${root}/.claude/ruby-plugin-hook-mode"
  if [[ -f "$mode_file" && ! -L "$mode_file" ]]; then
    if IFS= read -r mode < "$mode_file"; then
      normalize_hook_mode "$mode"
      return 0
    fi
  fi

  printf '%s\n' "default"
}
