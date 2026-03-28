#!/usr/bin/env bash
# Run deterministic contributor evals for the Ruby plugin.
#
# Usage:
#   ./lab/eval/run_eval.sh              # Lint + injection check + changed surfaces
#   ./lab/eval/run_eval.sh --changed    # Same as default
#   ./lab/eval/run_eval.sh --all        # Lint + injection check + core skills + all agents + triggers
#   ./lab/eval/run_eval.sh --skills     # Core skills only
#   ./lab/eval/run_eval.sh --agents     # All agents only
#   ./lab/eval/run_eval.sh --triggers   # Trigger corpora only
#   ./lab/eval/run_eval.sh --ci         # CI gate for all tracked eval surfaces

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLUGIN_ROOT="plugins/ruby-grape-rails"
LAST_EVAL_FILE="${SCRIPT_DIR}/.last-eval-commit"
MODE="${1:---changed}"
FAIL_UNDER="${RUBY_PLUGIN_EVAL_FAIL_UNDER:-0.90}"
AGENT_FAIL_UNDER="${RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER:-0.85}"
TRIGGER_FAIL_UNDER="${RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER:-0.90}"
FAILURES=0
CORE_SKILLS_REGEX='^(plan|work|review|verify|permissions|research)$'

cd "$PROJECT_ROOT" || exit 1

have_head() {
  git rev-parse --verify HEAD >/dev/null 2>&1
}

collect_changed_paths() {
  local prefix="$1"
  local lines=""

  if have_head; then
    lines=$(git diff --name-only HEAD -- "$prefix" 2>/dev/null || true)

    local staged=""
    staged=$(git diff --cached --name-only -- "$prefix" 2>/dev/null || true)
    if [[ -n "$staged" ]]; then
      lines=$(printf '%s\n%s\n' "$lines" "$staged")
    fi

    if [[ -f "$LAST_EVAL_FILE" ]]; then
      local last_commit=""
      last_commit="$(cat "$LAST_EVAL_FILE")"
      if git rev-parse --verify "$last_commit" >/dev/null 2>&1; then
        local since_last=""
        since_last=$(git diff --name-only "$last_commit" HEAD -- "$prefix" 2>/dev/null || true)
        if [[ -n "$since_last" ]]; then
          lines=$(printf '%s\n%s\n' "$lines" "$since_last")
        fi
      fi
    fi
  else
    lines=$(git ls-files -- "$prefix" 2>/dev/null || true)
  fi

  local untracked=""
  untracked=$(git ls-files --others --exclude-standard -- "$prefix" 2>/dev/null || true)
  if [[ -n "$untracked" ]]; then
    lines=$(printf '%s\n%s\n' "$lines" "$untracked")
  fi

  printf '%s\n' "$lines" | awk 'NF' | sort -u
}

collect_changed_skill_names() {
  collect_changed_paths "${PLUGIN_ROOT}/skills/" \
    | sed -n "s|^${PLUGIN_ROOT}/skills/\\([^/]*\\)/.*|\\1|p" \
    | awk 'NF' \
    | sort -u
}

collect_changed_agent_paths() {
  collect_changed_paths "${PLUGIN_ROOT}/agents/" \
    | grep -E '^plugins/ruby-grape-rails/agents/.+\.md$' \
    | sort -u || true
}

should_run_changed_triggers() {
  if [[ -n "$(collect_changed_paths 'lab/eval/triggers/')" ]]; then
    return 0
  fi

  local core_changed=""
  core_changed=$(
    collect_changed_paths "${PLUGIN_ROOT}/skills/" \
      | sed -n "s|^${PLUGIN_ROOT}/skills/\\([^/]*\\)/SKILL\\.md$|\\1|p" \
      | grep -E "$CORE_SKILLS_REGEX" || true
  )
  [[ -n "$core_changed" ]]
}

summarize_subject_scores() {
  local label="$1"
  local threshold="$2"
  local payload_file
  payload_file="$(mktemp "${TMPDIR:-/tmp}/rb-eval-scores.XXXXXX")"
  cat > "$payload_file"
  local status=0
  python3 - "$label" "$threshold" "$payload_file" <<'PY' || status=$?
import json
from pathlib import Path
import sys

label = sys.argv[1]
threshold = float(sys.argv[2])
data = json.loads(Path(sys.argv[3]).read_text())

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
  payload_file="$(mktemp "${TMPDIR:-/tmp}/rb-eval-triggers.XXXXXX")"
  cat > "$payload_file"
  local status=0
  python3 - "$threshold" "$payload_file" <<'PY' || status=$?
import json
from pathlib import Path
import sys

threshold = float(sys.argv[1])
payload = json.loads(Path(sys.argv[2]).read_text())
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
  npm run lint --silent
}

run_injection_check() {
  bash scripts/check-dynamic-injection.sh
}

run_changed_skills() {
  mapfile -t skills_to_check < <(collect_changed_skill_names)

  if [[ ${#skills_to_check[@]} -eq 0 ]]; then
    echo "  No skill changes detected."
    return 0
  fi

  echo "  Scoring ${#skills_to_check[@]} changed skills: ${skills_to_check[*]}"

  local result="{"
  local first=true
  local skill=""
  for skill in "${skills_to_check[@]}"; do
    local path="${PLUGIN_ROOT}/skills/${skill}/SKILL.md"
    [[ -f "$path" ]] || continue

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

  printf '%s\n' "$result" | summarize_subject_scores "skills" "$FAIL_UNDER"
}

run_all_skills() {
  echo "  Scoring core skills: plan work review verify permissions research"
  python3 -m lab.eval.scorer --core | summarize_subject_scores "skills" "$FAIL_UNDER"
}

run_changed_agents() {
  mapfile -t agent_paths < <(collect_changed_agent_paths)

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
  for path in "${agent_paths[@]}"; do
    local agent_name
    agent_name="$(basename "$path" .md)"
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

persist_last_eval_marker() {
  if have_head; then
    git rev-parse HEAD > "$LAST_EVAL_FILE"
  fi
}

echo "=== Ruby Plugin Eval ==="
echo

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
    echo "--- CI Gate: lint + injection check + core skills + all agents + triggers ---"
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
    echo "Usage: $0 [--changed|--all|--skills|--agents|--triggers|--ci]"
    exit 1
    ;;
esac

persist_last_eval_marker

if [[ $FAILURES -gt 0 ]]; then
  echo
  echo "Eval finished with ${FAILURES} failing section(s)."
  exit 1
fi

echo
echo "Eval passed."
