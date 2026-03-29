#!/usr/bin/env bash

ruby_plugin_escape_ere() {
  printf '%s' "$1" | sed 's/[][(){}.^$?+*|\\/]/\\&/g'
}

ruby_plugin_lock_version() {
  local lockfile="$1"
  local gem_name="$2"
  local escaped_name

  [[ -f "$lockfile" && ! -L "$lockfile" ]] || return 1
  escaped_name=$(ruby_plugin_escape_ere "$gem_name")

  grep -m 1 -E "^[[:space:]]{4}${escaped_name} \([^)]+\)$" "$lockfile" |
    sed -E 's/.*\(([^)]+)\).*/\1/'
}

ruby_plugin_lock_declares_gem() {
  local lockfile="$1"
  local gem_name="$2"
  local escaped_name

  [[ -f "$lockfile" && ! -L "$lockfile" ]] || return 1
  escaped_name=$(ruby_plugin_escape_ere "$gem_name")

  sed -n '/^DEPENDENCIES$/,/^[^[:space:]]/p' "$lockfile" |
    grep -Eq "^[[:space:]]{2}${escaped_name}([[:space:]]|!|\\(|$)"
}

ruby_plugin_lock_has_gem() {
  ruby_plugin_lock_declares_gem "$1" "$2"
}

ruby_plugin_gemfile_uses_gemspec() {
  local gemfile="$1"

  [[ -f "$gemfile" && ! -L "$gemfile" ]] || return 1
  grep -Eq "^[[:space:]]*gemspec([[:space:]]*(\\(|#|$)|$)" "$gemfile"
}

ruby_plugin_gemfile_declares_gem() {
  local gemfile="$1"
  local gem_name="$2"
  local escaped_name

  [[ -f "$gemfile" && ! -L "$gemfile" ]] || return 1
  escaped_name=$(ruby_plugin_escape_ere "$gem_name")
  grep -Eq "^[[:space:]]*gem[[:space:]]*(\\(|[[:space:]])[[:space:]]*['\"]${escaped_name}['\"]([[:space:]]*(,|\\)|#|$))" "$gemfile"
}

ruby_plugin_gemfile_declares_gem_prefix() {
  local gemfile="$1"
  local prefix="$2"
  local escaped_prefix

  [[ -f "$gemfile" && ! -L "$gemfile" ]] || return 1
  escaped_prefix=$(ruby_plugin_escape_ere "$prefix")
  grep -Eq "^[[:space:]]*gem[[:space:]]*(\\(|[[:space:]])[[:space:]]*['\"]${escaped_prefix}[A-Za-z0-9_-]+['\"]([[:space:]]*(,|\\)|#|$))" "$gemfile"
}

ruby_plugin_gemspec_declares_gem() {
  local gemspec="$1"
  local gem_name="$2"
  local escaped_name

  [[ -f "$gemspec" && ! -L "$gemspec" ]] || return 1
  escaped_name=$(ruby_plugin_escape_ere "$gem_name")
  grep -Eq "^[[:space:]]*(spec|s)?\\.?add(_runtime|_development)?_dependency[[:space:]]*(\\(|[[:space:]])[[:space:]]*['\"]${escaped_name}['\"]([[:space:]]*(,|\\)|#|$))" "$gemspec"
}

ruby_plugin_gemspec_declares_gem_prefix() {
  local gemspec="$1"
  local prefix="$2"
  local escaped_prefix

  [[ -f "$gemspec" && ! -L "$gemspec" ]] || return 1
  escaped_prefix=$(ruby_plugin_escape_ere "$prefix")
  grep -Eq "^[[:space:]]*(spec|s)?\\.?add(_runtime|_development)?_dependency[[:space:]]*(\\(|[[:space:]])[[:space:]]*['\"]${escaped_prefix}[A-Za-z0-9_-]+['\"]([[:space:]]*(,|\\)|#|$))" "$gemspec"
}

ruby_plugin_each_root_gemspec() {
  local repo_root="$1"
  local gemspec

  for gemspec in "$repo_root"/*.gemspec; do
    [[ -f "$gemspec" && ! -L "$gemspec" ]] || continue
    printf '%s\n' "$gemspec"
  done
}

ruby_plugin_repo_declares_gem() {
  local repo_root="$1"
  local gemfile="$2"
  local gem_name="$3"
  local gemspec

  if ruby_plugin_gemfile_declares_gem "$gemfile" "$gem_name"; then
    return 0
  fi

  ruby_plugin_gemfile_uses_gemspec "$gemfile" || return 1

  while IFS= read -r gemspec; do
    if ruby_plugin_gemspec_declares_gem "$gemspec" "$gem_name"; then
      return 0
    fi
  done < <(ruby_plugin_each_root_gemspec "$repo_root")

  return 1
}

ruby_plugin_repo_declares_gem_prefix() {
  local repo_root="$1"
  local gemfile="$2"
  local prefix="$3"
  local gemspec

  if ruby_plugin_gemfile_declares_gem_prefix "$gemfile" "$prefix"; then
    return 0
  fi

  ruby_plugin_gemfile_uses_gemspec "$gemfile" || return 1

  while IFS= read -r gemspec; do
    if ruby_plugin_gemspec_declares_gem_prefix "$gemspec" "$prefix"; then
      return 0
    fi
  done < <(ruby_plugin_each_root_gemspec "$repo_root")

  return 1
}
