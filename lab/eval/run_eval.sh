#!/usr/bin/env bash
# Run contributor evals for the Ruby plugin.
# Default and CI modes score tracked surfaces; --include-untracked is
# intentionally local-only and non-comparable.
#
# Usage:
#   ./lab/eval/run_eval.sh              # Lint + injection check + tracked changed surfaces
#   ./lab/eval/run_eval.sh --changed    # Same as default
#   ./lab/eval/run_eval.sh --changed --against origin/main  # branch-style diff vs merge-base
#   ./lab/eval/run_eval.sh --changed --include-untracked  # local-only expansion
#   ./lab/eval/run_eval.sh --all        # Lint + injection check + core skills + all agents + triggers
#   ./lab/eval/run_eval.sh --skills     # Core skills only
#   ./lab/eval/run_eval.sh --agents     # All agents only
#   ./lab/eval/run_eval.sh --triggers   # Trigger corpora only
#   ./lab/eval/run_eval.sh --ci         # tracked scoring gate (runtime tests run separately)

set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
case "$SCRIPT_PATH" in
  */*) SCRIPT_BASE_DIR="${SCRIPT_PATH%/*}" ;;
  *) SCRIPT_BASE_DIR="." ;;
esac
SCRIPT_DIR="$(cd "${SCRIPT_BASE_DIR}" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLUGIN_ROOT="plugins/ruby-grape-rails"
MODE="--changed"
INCLUDE_UNTRACKED=false
AGAINST_REF=""
AGAINST_MERGE_BASE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --changed|--all|--skills|--agents|--triggers|--ci)
      MODE="$1"
      ;;
    --include-untracked)
      INCLUDE_UNTRACKED=true
      ;;
    --against)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Usage: $0 [--changed|--all|--skills|--agents|--triggers|--ci] [--include-untracked] [--against REF]" >&2
        exit 1
      fi
      AGAINST_REF="$1"
      ;;
    *)
      echo "Usage: $0 [--changed|--all|--skills|--agents|--triggers|--ci] [--include-untracked] [--against REF]" >&2
      exit 1
      ;;
  esac
  shift
done
FAIL_UNDER="${RUBY_PLUGIN_EVAL_FAIL_UNDER:-0.90}"
AGENT_FAIL_UNDER="${RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER:-0.85}"
TRIGGER_FAIL_UNDER="${RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER:-0.90}"
FAILURES=0
CORE_TRIGGER_SKILLS_REGEX='plan|work|review|verify|permissions|research'

cd "$PROJECT_ROOT" || exit 1

require_python_310() {
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    echo "ERROR: lab/eval requires python3 3.10+." >&2
    echo "Current python3: $(python3 --version 2>/dev/null || echo unavailable)" >&2
    exit 1
  fi
}

require_python_310

require_command() {
  local command_name="$1"
  local reason="$2"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: ${command_name} is required for ${reason}." >&2
    exit 1
  fi
}

require_git_for_mode() {
  case "$MODE" in
    --changed|--all|--ci)
      require_command git "git-aware eval path selection in ${MODE} mode"
      ;;
  esac

  if [[ -n "$AGAINST_REF" ]] || [[ "$INCLUDE_UNTRACKED" == "true" ]]; then
    require_command git "git-aware changed-surface selection"
  fi
}

require_git_for_mode

validate_threshold() {
  local env_name="$1"
  local value="$2"

  if ! python3 - "$value" <<'PY' >/dev/null 2>&1
import math
import sys

try:
    value = float(sys.argv[1])
except ValueError:
    raise SystemExit(1)

raise SystemExit(0 if math.isfinite(value) and 0.0 <= value <= 1.0 else 1)
PY
  then
    echo "ERROR: ${env_name} must be a finite numeric threshold between 0 and 1, got: ${value}" >&2
    exit 1
  fi
}

validate_threshold "RUBY_PLUGIN_EVAL_FAIL_UNDER" "$FAIL_UNDER"
validate_threshold "RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER" "$AGENT_FAIL_UNDER"
validate_threshold "RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER" "$TRIGGER_FAIL_UNDER"

have_head() {
  git rev-parse --verify HEAD >/dev/null 2>&1
}

resolve_against_merge_base() {
  [[ -n "$AGAINST_REF" ]] || return 0
  have_head || return 0

  AGAINST_MERGE_BASE=$(git merge-base HEAD "$AGAINST_REF" 2>/dev/null || true)
  if [[ -z "$AGAINST_MERGE_BASE" ]]; then
    echo "ERROR: could not resolve merge-base with ${AGAINST_REF}; changed-surface scoring would be incomplete." >&2
    echo "Use a valid branch/ref for --against or rerun without it." >&2
    exit 1
  fi
}

resolve_against_merge_base

collect_changed_paths() {
  local prefix="$1"
  local lines=""

  collect_diff_paths() {
    local status=""
    local path=""
    local old_path=""

    while IFS= read -r -d '' status; do
      [[ -n "$status" ]] || continue
      case "$status" in
        R*|C*)
          # The old path is intentionally ignored; changed-mode scoring only uses
          # the current tree path for renamed/copied files.
          # shellcheck disable=SC2034
          IFS= read -r -d '' old_path || break
          IFS= read -r -d '' path || break
          printf '%s\n' "$path"
          ;;
        D*)
          IFS= read -r -d '' path || break
          printf '__DELETED__:%s\n' "$path"
          ;;
        *)
          IFS= read -r -d '' path || break
          printf '%s\n' "$path"
          ;;
      esac
    done
  }

  if have_head; then
    if [[ -n "$AGAINST_REF" ]]; then
      lines=$(git diff --name-status -z -M "${AGAINST_MERGE_BASE}..HEAD" -- "$prefix" 2>/dev/null | collect_diff_paths || true)
    else
      lines=$(git diff --name-status -z -M HEAD -- "$prefix" 2>/dev/null | collect_diff_paths || true)
    fi

    local staged=""
    staged=$(git diff --cached --name-status -z -M -- "$prefix" 2>/dev/null | collect_diff_paths || true)
    if [[ -n "$staged" ]]; then
      lines=$(printf '%s\n%s\n' "$lines" "$staged")
    fi
  else
    lines=$(git ls-files -- "$prefix" 2>/dev/null || true)
  fi

  if [[ "$INCLUDE_UNTRACKED" == "true" ]]; then
    local untracked=""
    untracked=$(git ls-files --others --exclude-standard -- "$prefix" 2>/dev/null || true)
    if [[ -n "$untracked" ]]; then
      lines=$(printf '%s\n%s\n' "$lines" "$untracked")
    fi
  fi

  printf '%s\n' "$lines" | awk 'NF' | sort -u
}

collect_changed_skill_names() {
  collect_changed_paths "${PLUGIN_ROOT}/skills/" \
    | grep -Ev '^__DELETED__:' \
    | sed -n "s|^${PLUGIN_ROOT}/skills/\\([^/]*\\)/.*|\\1|p" \
    | awk 'NF' \
    | sort -u
}

collect_deleted_skill_names() {
  collect_changed_paths "${PLUGIN_ROOT}/skills/" \
    | sed -n "s|^__DELETED__:${PLUGIN_ROOT}/skills/\\([^/]*\\)/.*|\\1|p" \
    | awk 'NF' \
    | sort -u
}

collect_changed_agent_paths() {
  collect_changed_paths "${PLUGIN_ROOT}/agents/" \
    | grep -Ev '^__DELETED__:' \
    | grep -E "^${PLUGIN_ROOT}/agents/.+\.md$" \
    | sort -u || true
}

collect_deleted_agent_names() {
  collect_changed_paths "${PLUGIN_ROOT}/agents/" \
    | sed -n "s|^__DELETED__:${PLUGIN_ROOT}/agents/\\([^/]*\\)\\.md$|\\1|p" \
    | awk 'NF' \
    | sort -u
}

should_run_changed_triggers() {
  if [[ -n "$(collect_changed_paths 'lab/eval/triggers/')" ]]; then
    return 0
  fi

  if [[ -n "$(collect_changed_paths 'lab/eval/evals/')" ]]; then
    return 0
  fi

  local entrypoint_changed=""
  entrypoint_changed=$(
    collect_changed_paths "${PLUGIN_ROOT}/skills/" \
      | grep -E "^${PLUGIN_ROOT}/skills/(${CORE_TRIGGER_SKILLS_REGEX})/SKILL\\.md$" || true
  )
  [[ -n "$entrypoint_changed" ]]
}

summarize_subject_scores() {
  local label="$1"
  local threshold="$2"
  local payload_file
  payload_file="$(mktemp "${TMPDIR:-/tmp}/rb-eval-scores.XXXXXX")" || {
    echo "ERROR: could not create a temporary score payload file." >&2
    return 1
  }
  cat > "$payload_file"
  local status=0
  python3 - "$label" "$threshold" "$payload_file" <<'PY' || status=$?
import json
from pathlib import Path
import sys

label = sys.argv[1]
threshold = float(sys.argv[2])
data = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

if not data:
    print(f"  No {label} scored.")
    raise SystemExit(0)

avg = sum(item["composite"] for item in data.values()) / len(data)
perfect = sum(1 for item in data.values() if item["composite"] >= 0.999)
below = {name: round(item["composite"], 3) for name, item in data.items() if item["composite"] < threshold}

print(f"  {len(data)} {label} scored | {perfect} perfect | avg {avg:.3f} | threshold {threshold:.2f}")
if below:
    print(f"  BELOW {threshold:.2f}: {below}")
    raise SystemExit(1)

print("  All scores meet threshold.")
PY
  rm -f -- "$payload_file"
  return "$status"
}

summarize_triggers() {
  local threshold="$1"
  local payload_file
  payload_file="$(mktemp "${TMPDIR:-/tmp}/rb-eval-triggers.XXXXXX")" || {
    echo "ERROR: could not create a temporary trigger payload file." >&2
    return 1
  }
  cat > "$payload_file"
  local status=0
  python3 - "$threshold" "$payload_file" <<'PY' || status=$?
import json
from pathlib import Path
import sys

threshold = float(sys.argv[1])
payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
skills = payload.get("skills", {})
pairs = payload.get("confusable_pairs", [])

if not skills:
    print("  No trigger corpora scored.")
    raise SystemExit(0)

avg = sum(item["score"] for item in skills.values()) / len(skills)
below = {name: round(item["score"], 3) for name, item in skills.items() if item["score"] < threshold}

print(f"  {len(skills)} trigger sets scored | avg {avg:.3f} | threshold {threshold:.2f}")
if below:
    print(f"  BELOW {threshold:.2f}: {below}")
else:
    print("  All trigger sets meet threshold.")

if pairs:
    print("  Top confusable pairs:")
    for pair in pairs[:3]:
        print(f"    - {pair['left']} vs {pair['right']} ({pair['overlap']:.4f})")

if below:
    raise SystemExit(1)
PY
  rm -f -- "$payload_file"
  return "$status"
}

run_lint() {
  require_command npm "linting in ${MODE} mode"
  npm run lint --silent
}

run_injection_check() {
  bash scripts/check-dynamic-injection.sh
}

run_changed_skills() {
  local skills_to_check=()
  local skill_name=""

  while IFS= read -r skill_name; do
    [[ -n "$skill_name" ]] || continue
    skills_to_check+=("$skill_name")
  done < <(collect_changed_skill_names)

  if [[ ${#skills_to_check[@]} -eq 0 ]]; then
    echo "  No skill changes detected."
    return 0
  fi

  echo "  Scoring ${#skills_to_check[@]} changed skills: ${skills_to_check[*]}"

  local result="{"
  local first=true
  local skill=""
  local missing_skills=()
  local deleted_skills=()
  while IFS= read -r skill; do
    [[ -n "$skill" ]] || continue
    deleted_skills+=("$skill")
  done < <(collect_deleted_skill_names)
  for skill in "${skills_to_check[@]}"; do
    local path="${PLUGIN_ROOT}/skills/${skill}/SKILL.md"
    if [[ ! -f "$path" ]]; then
      missing_skills+=("$skill")
      continue
    fi

    local score=""
    score="$(python3 -m lab.eval.scorer "$path")"
    if [[ "$first" == true ]]; then
      first=false
    else
      result+=","
    fi
    result+="\"${skill}\":${score}"
  done
  result+="}"

  if [[ ${#missing_skills[@]} -gt 0 ]]; then
    echo "  WARNING: skipping deleted or moved changed skills: ${missing_skills[*]}" >&2
  fi
  if [[ ${#deleted_skills[@]} -gt 0 ]]; then
    echo "  NOTE: deleted changed skills are not scorable on the current tree: ${deleted_skills[*]}" >&2
  fi

  if [[ "$first" == true ]]; then
    echo "  No scorable changed skills remain after skipping deleted or moved paths."
    return 0
  fi

  printf '%s\n' "$result" | summarize_subject_scores "skills" "$FAIL_UNDER"
}

run_all_skills() {
  echo "  Scoring core skills: plan work review verify permissions research"
  python3 -m lab.eval.scorer --core | summarize_subject_scores "skills" "$FAIL_UNDER"
}

run_changed_agents() {
  local agent_paths=()
  local agent_path=""

  while IFS= read -r agent_path; do
    [[ -n "$agent_path" ]] || continue
    agent_paths+=("$agent_path")
  done < <(collect_changed_agent_paths)

  if [[ ${#agent_paths[@]} -eq 0 ]]; then
    echo "  No agent changes detected."
    return 0
  fi

  local agent_names=()
  local path=""
  for path in "${agent_paths[@]}"; do
    agent_names+=("$(basename "$path" .md)")
  done
  echo "  Scoring ${#agent_paths[@]} changed agents: ${agent_names[*]}"

  local result="{"
  local first=true
  local missing_agents=()
  local deleted_agents=()
  while IFS= read -r agent_name; do
    [[ -n "$agent_name" ]] || continue
    deleted_agents+=("$agent_name")
  done < <(collect_deleted_agent_names)
  for path in "${agent_paths[@]}"; do
    local agent_name
    agent_name="$(basename "$path" .md)"
    if [[ ! -f "$path" ]]; then
      missing_agents+=("$agent_name")
      continue
    fi
    local score=""
    score="$(python3 -m lab.eval.agent_scorer "$path")"
    if [[ "$first" == true ]]; then
      first=false
    else
      result+=","
    fi
    result+="\"${agent_name}\":${score}"
  done
  result+="}"

  if [[ ${#missing_agents[@]} -gt 0 ]]; then
    echo "  WARNING: skipping deleted or moved changed agents: ${missing_agents[*]}" >&2
  fi
  if [[ ${#deleted_agents[@]} -gt 0 ]]; then
    echo "  NOTE: deleted changed agents are not scorable on the current tree: ${deleted_agents[*]}" >&2
  fi

  if [[ "$first" == true ]]; then
    echo "  No scorable changed agents remain after skipping deleted or moved paths."
    return 0
  fi

  printf '%s\n' "$result" | summarize_subject_scores "agents" "$AGENT_FAIL_UNDER"
}

run_all_agents() {
  echo "  Scoring all shipped agents"
  python3 -m lab.eval.agent_scorer --all | summarize_subject_scores "agents" "$AGENT_FAIL_UNDER"
}

run_all_triggers() {
  echo "  Scoring trigger corpora and overlap analysis"
  python3 -m lab.eval.trigger_scorer --all | summarize_triggers "$TRIGGER_FAIL_UNDER"
}

echo "=== Ruby Plugin Eval ==="
echo

if [[ "$MODE" != "--changed" && "$INCLUDE_UNTRACKED" == "true" ]]; then
  echo "WARNING: --include-untracked only affects --changed mode and will be ignored for ${MODE}."
  echo
fi

if [[ "$MODE" == "--changed" && "$INCLUDE_UNTRACKED" == "true" ]]; then
  echo "WARNING: --include-untracked makes changed-mode results local-only and non-comparable."
  echo "WARNING: CI and review comparisons should use tracked surfaces only."
  echo
fi

if [[ "$MODE" == "--changed" && -n "$AGAINST_REF" ]]; then
  echo "NOTE: --against ${AGAINST_REF} compares changed surfaces from merge-base to HEAD plus staged changes."
  echo
fi

case "$MODE" in
  --changed)
    echo "--- Lint ---"
    run_lint || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Injection Guard ---"
    run_injection_check || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Skills (changed) ---"
    run_changed_skills || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Agents (changed) ---"
    run_changed_agents || FAILURES=$((FAILURES + 1))
    if should_run_changed_triggers; then
      echo
      echo "--- Triggers (changed context) ---"
      run_all_triggers || FAILURES=$((FAILURES + 1))
    fi
    ;;
  --all)
    echo "--- Lint ---"
    run_lint || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Injection Guard ---"
    run_injection_check || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Skills (core) ---"
    run_all_skills || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Agents (all) ---"
    run_all_agents || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Triggers ---"
    run_all_triggers || FAILURES=$((FAILURES + 1))
    ;;
  --skills)
    echo "--- Skills (core) ---"
    run_all_skills || FAILURES=$((FAILURES + 1))
    ;;
  --agents)
    echo "--- Agents (all) ---"
    run_all_agents || FAILURES=$((FAILURES + 1))
    ;;
  --triggers)
    echo "--- Triggers ---"
    run_all_triggers || FAILURES=$((FAILURES + 1))
    ;;
  --ci)
    echo "--- CI Scoring Gate: lint + injection check + core skills + all agents + triggers ---"
    echo "NOTE: runtime tests run separately via npm run eval:test or npm run ci."
    echo
    echo "--- Lint ---"
    run_lint || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Injection Guard ---"
    run_injection_check || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Skills (core) ---"
    run_all_skills || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Agents (all) ---"
    run_all_agents || FAILURES=$((FAILURES + 1))
    echo
    echo "--- Triggers ---"
    run_all_triggers || FAILURES=$((FAILURES + 1))
    ;;
  *)
    echo "Usage: $0 [--changed|--all|--skills|--agents|--triggers|--ci] [--include-untracked] [--against REF]"
    exit 1
    ;;
esac

if [[ $FAILURES -gt 0 ]]; then
  echo
  echo "Eval finished with ${FAILURES} failing section(s)."
  exit 1
fi

echo
echo "Eval passed."
