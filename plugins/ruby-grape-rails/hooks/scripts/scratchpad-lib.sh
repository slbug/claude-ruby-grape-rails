#!/usr/bin/env bash
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
if [[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]]; then
  # shellcheck disable=SC1090,SC1091
  source "$ROOT_LIB"
fi
if ! declare -F library_safe_return >/dev/null 2>&1; then
  library_safe_return() {
    local status="${1:-0}"
    if [[ "${BASH_SOURCE[0]:-}" != "${0:-}" ]]; then
      return "$status"
    fi
    exit "$status"
  }
fi
if [[ -z "${REPO_ROOT:-}" ]]; then
  if declare -F resolve_workspace_root >/dev/null 2>&1; then
    if [[ -n "${INPUT:-}" ]]; then
      REPO_ROOT=$(resolve_workspace_root "$INPUT") || REPO_ROOT=""
    else
      REPO_ROOT=$(resolve_workspace_root) || REPO_ROOT=""
    fi
  else
    REPO_ROOT="${CLAUDE_PROJECT_DIR:-${PWD:-.}}"
  fi
fi
[[ -n "${REPO_ROOT:-}" ]] || library_safe_return 0

CLAUDE_DIR="${CLAUDE_DIR:-${REPO_ROOT}/.claude}"
PLANS_DIR="${PLANS_DIR:-${CLAUDE_DIR}/plans}"

scratchpad_branch_name() {
  local branch=""

  branch=$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || true)
  [[ -n "$branch" ]] || branch="unknown"
  printf '%s\n' "$branch"
}

scratchpad_plan_summary() {
  local plan_dir="$1"
  local requested_summary="${2:-}"
  local summary=""

  [[ -n "$plan_dir" ]] || return 1

  if [[ -n "$requested_summary" ]]; then
    summary="$requested_summary"
  elif declare -F get_plan_intent >/dev/null 2>&1; then
    summary=$(get_plan_intent "$plan_dir" 2>/dev/null || true)
  elif [[ -f "$plan_dir/plan.md" ]]; then
    summary=$(head -5 "$plan_dir/plan.md" 2>/dev/null | grep '^#' | head -1 | sed 's/^#* *//')
  fi

  if [[ -z "$summary" ]]; then
    if declare -F get_plan_slug >/dev/null 2>&1; then
      summary=$(get_plan_slug "$plan_dir" 2>/dev/null || true)
    else
      summary="${plan_dir##*/}"
    fi
  fi

  [[ -n "$summary" ]] || summary="(to be filled)"
  printf '%s\n' "$summary"
}

emit_scratchpad_template() {
  local plan_dir="$1"
  local requested_summary="${2:-}"
  local slug
  local summary
  local branch

  [[ -n "$plan_dir" ]] || return 1
  slug="${plan_dir##*/}"
  summary=$(scratchpad_plan_summary "$plan_dir" "$requested_summary") || return 1
  branch=$(scratchpad_branch_name)

  cat <<EOF
# Scratchpad: ${slug}

- Request: ${summary}
- Plan: .claude/plans/${slug}/plan.md

## Dead Ends

(none yet)

## Decisions

### Clarifications

(none yet)

### Research Cache Reuse

(none yet)

### Infrastructure

(none yet)

## Hypotheses

(none yet)

## Open Questions

(none yet)

## Handoff

- Branch: ${branch}
- Next: (to be filled)
EOF
}

ensure_scratchpad_file() {
  local input_plan_dir="$1"
  local requested_summary="${2:-}"
  local plan_dir="$input_plan_dir"
  local scratchpad_file
  local tmp_file

  [[ -n "$input_plan_dir" ]] || return 1

  if declare -F is_valid_plan_dir >/dev/null 2>&1; then
    is_valid_plan_dir "$input_plan_dir" || return 1
    if declare -F resolve_plan_dir >/dev/null 2>&1; then
      plan_dir=$(resolve_plan_dir "$input_plan_dir") || return 1
    fi
  else
    [[ "$plan_dir" == /* ]] || plan_dir="${REPO_ROOT}/${plan_dir#./}"
    [[ "$plan_dir" == "${PLANS_DIR}/"* ]] || return 1
    [[ -d "$plan_dir" ]] || return 1
    [[ ! -L "$plan_dir" ]] || return 1
  fi

  scratchpad_file="${plan_dir}/scratchpad.md"
  [[ ! -L "$scratchpad_file" ]] || return 1

  if [[ -f "$scratchpad_file" && -s "$scratchpad_file" ]]; then
    return 0
  fi

  tmp_file=$(mktemp "${plan_dir}/scratchpad.XXXXXX") || return 1
  if ! emit_scratchpad_template "$plan_dir" "$requested_summary" > "$tmp_file"; then
    rm -f -- "$tmp_file"
    return 1
  fi

  if ! mv -f -- "$tmp_file" "$scratchpad_file"; then
    rm -f -- "$tmp_file"
    return 1
  fi
}

extract_markdown_section() {
  local file="$1"
  local section="$2"
  local heading="## ${section}"

  [[ -f "$file" && ! -L "$file" ]] || return 1
  [[ -n "$section" ]] || return 1

  awk -v heading="$heading" '
    $0 == heading { in_section = 1; next }
    /^## / && in_section { exit }
    in_section { print }
  ' "$file"
}

count_markdown_bullets_in_section() {
  local file="$1"
  local section="$2"

  extract_markdown_section "$file" "$section" 2>/dev/null |
    grep -Ec '^[-*] ' 2>/dev/null || true
}

extract_dead_end_section() {
  local file="$1"

  extract_markdown_section "$file" "Dead Ends"
}

count_dead_end_entries() {
  local file="$1"

  count_markdown_bullets_in_section "$file" "Dead Ends"
}

append_handoff_note() {
  local file="$1"
  local note="$2"
  local tmp_file

  [[ -f "$file" && ! -L "$file" ]] || return 1
  [[ -n "$note" ]] || return 1

  tmp_file=$(mktemp "$(dirname "$file")/scratchpad-handoff.XXXXXX") || return 1
  if ! awk -v note="$note" '
    BEGIN { saw_handoff = 0; inserted = 0; in_handoff = 0 }
    $0 == "## Handoff" {
      saw_handoff = 1
      in_handoff = 1
      print
      next
    }
    /^## / && in_handoff {
      if (!inserted) {
        print ""
        print note
        inserted = 1
      }
      in_handoff = 0
      print
      next
    }
    in_handoff && !inserted && /^\(none yet\)[[:space:]]*$/ {
      print note
      inserted = 1
      next
    }
    { print }
    END {
      if (!saw_handoff) {
        print ""
        print "## Handoff"
        print ""
        print note
      } else if (!inserted) {
        print ""
        print note
      }
    }
  ' "$file" > "$tmp_file"; then
    rm -f -- "$tmp_file"
    return 1
  fi

  if ! mv -f -- "$tmp_file" "$file"; then
    rm -f -- "$tmp_file"
    return 1
  fi
}
