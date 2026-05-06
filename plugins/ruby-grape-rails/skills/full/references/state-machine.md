# `/rb:full` State Machine

Implementation reference for `/rb:full` skill body. State names, phase
transitions, marker concurrency rules, progress.md schemas, verification
gating, and integration points. Skill bodies own fanout; agents are leaf
workers.

## State Machine

```text
                ┌─────────────┐
                │ INITIALIZING│
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │ DISCOVERING │  (optional /rb:brainstorm)
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │   PLANNING  │  (/rb:plan)
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │   WORKING   │  (/rb:work)
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │  VERIFYING  │  (/rb:verify --full)
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │  REVIEWING  │  (/rb:review)
                └──────┬──────┘
                       │
                 **Verdict**:
              ┌────────┼─────────────┐
       BLOCKED │       │ REQUIRES    │ PASS / PASS WITH WARNINGS
              │       │ CHANGES     │
              ▼       ▼             ▼
       ┌──────────┐ ┌────────────┐ ┌─────────────┐
       │ HALTED_  │ │ HALTED_    │ │ COMPOUNDING │  (/rb:compound ${PLAN_DIR}/plan.md)
       │ REVIEW_  │ │ REVIEW_    │ └──────┬──────┘
       │ BLOCKED  │ │ REQUIRES_  │        ▼
       │          │ │ CHANGES    │ ┌─────────────┐
       └──────────┘ └────────────┘ │  COMPLETED  │
                                   └─────────────┘
```

Missing artifact / verdict line absent / off-canonical wording →
`HALTED_REVIEW_UNKNOWN` (not shown above; see "Phase Transitions"
table below).

## Phase Details

| State | Driver | Inputs | Outputs |
|---|---|---|---|
| INITIALIZING | skill body | `$ARGUMENTS` | `PLAN_DIR/{research,scratchpad.md}`, initial `progress.md` |
| DISCOVERING | `/rb:brainstorm` (optional) | feature description | `PLAN_DIR/interview.md` |
| PLANNING | `/rb:plan` | `.claude/ACTIVE_PLAN` (pre-bound) | `PLAN_DIR/plan.md` |
| WORKING | `/rb:work` | `${PLAN_DIR}/plan.md` (explicit path) | updated checkboxes; marker cleared |
| VERIFYING | `/rb:verify --full` | current branch state | verification report |
| REVIEWING | `/rb:review` | git diff | `.claude/reviews/{review-slug}-{datesuffix}.md` |
| COMPOUNDING | `/rb:compound ${PLAN_DIR}/plan.md` | plan path | `.claude/solutions/{category}/{fix}.md` |
| COMPLETED | skill body | all phases passed | final `progress.md` State write |
| HALTED_VERIFY_FAILED | skill body | any `/rb:verify --full` gate failed | halt cycle; user fixes failing gate (test, lint, brakeman, zeitwerk, migration safety) and re-runs `/rb:full` or resumes manually |
| HALTED_REVIEW_BLOCKED | skill body | consolidated `**Verdict**: BLOCKED` parsed | halt cycle; user decides next |
| HALTED_REVIEW_REQUIRES_CHANGES | skill body | consolidated `**Verdict**: REQUIRES CHANGES` parsed | halt cycle; user invokes `/rb:triage {review-path}` (default; handles gaps + any warnings) OR `/rb:plan {review-path}` (gaps-only, no triage UI) |
| HALTED_REVIEW_UNKNOWN | skill body | review missing/unparseable / verdict line absent | halt cycle; user decides next |

## Phase Transitions

| From | To | Trigger | Skill body actions |
|---|---|---|---|
| INITIALIZING | DISCOVERING | brainstorm needed | write progress.md State; invoke `/rb:brainstorm` |
| INITIALIZING | PLANNING | brainstorm skipped | write progress.md State; invoke `/rb:plan` |
| DISCOVERING | PLANNING | interview complete | write progress.md State; invoke `/rb:plan` |
| PLANNING | WORKING | plan.md exists | write progress.md State; invoke `/rb:work ${PLAN_DIR}/plan.md` |
| WORKING | VERIFYING | all checkboxes done | write progress.md State; invoke `/rb:verify --full` |
| VERIFYING | REVIEWING | verify passed | write progress.md State; invoke `/rb:review` |
| VERIFYING | HALTED_VERIFY_FAILED | any verify gate failed | write progress.md State; stop (user fixes failing gate, re-runs `/rb:full` or resumes manually) |
| REVIEWING | COMPOUNDING | `**Verdict**: PASS` or `PASS WITH WARNINGS` | write progress.md State; invoke `/rb:compound ${PLAN_DIR}/plan.md` |
| REVIEWING | HALTED_REVIEW_BLOCKED | `**Verdict**: BLOCKED` | write progress.md State; stop |
| REVIEWING | HALTED_REVIEW_REQUIRES_CHANGES | `**Verdict**: REQUIRES CHANGES` | write progress.md State; stop (user runs `/rb:triage {review-path}` default, or `/rb:plan {review-path}` for gaps-only) |
| REVIEWING | HALTED_REVIEW_UNKNOWN | review missing/unparseable / verdict line absent | write progress.md State; stop |
| COMPOUNDING | COMPLETED | solution doc written | write progress.md final State |

## Local PLAN_DIR Pattern

PLAN_DIR is local to the /rb:full skill body. It is used ONLY for
the skill's own progress.md State writes between phases. It is NOT
passed as a CLI argument to /rb:verify, /rb:review, or other subskills.
Their interfaces do not accept a plan path:

  /rb:verify argument-hint:  [--quick|--full]
  /rb:review argument-hint:  [test|security|sidekiq|deploy|iron-laws|all]
  /rb:compound argument-hint: [path to fix|review|plan]    (this one accepts a path)

So /rb:full invokes:
  /rb:work    ${PLAN_DIR}/plan.md         # explicit path (avoids marker fallback ambiguity)
  /rb:verify  --full                      # NO PLAN_DIR
  /rb:review                              # NO PLAN_DIR; resolves from diff
  /rb:compound ${PLAN_DIR}/plan.md        # path arg permitted

Bash example:

Steps: derive `${SLUG}` from feature description, create plan
namespace, write initial `progress.md` (schema below), pre-bind the
active-plan marker BEFORE invoking `/rb:plan`.

```bash
SLUG=$(printf '%s' "$FEATURE_DESCRIPTION" | tr '[:upper:] ' '[:lower:]-' | tr -cd '[:alnum:]-' | tr -s '-')
PLAN_DIR=".claude/plans/${SLUG}"

mkdir -p "${PLAN_DIR}/research"
: > "${PLAN_DIR}/scratchpad.md"

cat > "${PLAN_DIR}/progress.md" <<EOF
# Progress: ${SLUG}

- **State**: INITIALIZING
- **Started**: $(date -Iseconds)

## Phase History
EOF

"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/active-plan-marker.sh" set "${PLAN_DIR}"
```

## Review Verdict Gate

After /rb:review writes .claude/reviews/{review-slug}-{datesuffix}.md,
/rb:full parses the consolidated `**Verdict**:` line (canonical 4-set
per `${CLAUDE_PLUGIN_ROOT}/skills/review/references/review-playbook.md`
§ "Verdict Decision Rules"). The verdict line sits immediately after
the `## Summary` table:

```text
## Summary

| Severity | Count |
|----------|-------|
| Blockers | {n} |
| Warnings | {n} |
| Suggestions | {n} |

**Verdict**: PASS | PASS WITH WARNINGS | REQUIRES CHANGES | BLOCKED
```

| Verdict | Transition |
|---|---|
| `PASS` / `PASS WITH WARNINGS` | continue to COMPOUNDING |
| `BLOCKED` | write `**State**: HALTED_REVIEW_BLOCKED`; stop cycle |
| `REQUIRES CHANGES` | write `**State**: HALTED_REVIEW_REQUIRES_CHANGES`; stop (user runs `/rb:triage {review-path}` default, or `/rb:plan {review-path}` for gaps-only) |
| missing artifact / verdict line absent / off-canonical wording | write `**State**: HALTED_REVIEW_UNKNOWN`; stop cycle |

Summary `Blockers` count is informational here — `**Verdict**:` is
the load-bearing gate. No autonomous re-run regardless of verdict.
User decides next step.

## Marker Lifecycle Constraints

Marker lifecycle constraints:

- Concurrent `/rb:full` invocations in the same repo race on
  `.claude/ACTIVE_PLAN`; last writer wins. Cross-session collision is
  user responsibility.
- `/rb:full` skill body tracks PLAN_DIR as a local variable through the
  entire state machine. Subsequent phases use local PLAN_DIR; do NOT
  re-read the marker mid-cycle.
- `/rb:plan` standalone (no marker pre-bind) reads `.claude/ACTIVE_PLAN`
  directly with strict guards (file exists, content resolves to valid
  namespace, progress.md State INITIALIZING|DISCOVERING, plan.md absent).
  Do NOT use `active-plan-marker.sh get` — that has disk-glob fallbacks.

## Marker Concurrency Notes

`active-plan-lib.sh::set_active_plan()` uses `mktemp` + atomic `mv`
(POSIX-safe against torn writes). NO `flock` / mutex. Race window: two
parallel `set_active_plan` calls land sequentially via `mv`; last writer
wins; first marker silently overwritten.

`get_active_plan()` has TWO disk-glob fallbacks if marker missing/invalid:
newest plan with unchecked tasks, then newest planning-phase dir. So a
missing marker still resolves to *something* — could be the wrong plan.
Skill bodies that need exact namespace identity MUST read
`.claude/ACTIVE_PLAN` directly with strict guards, not via `get`.

True mutual exclusion would require adding `flock` to `set_active_plan`
— out of scope.

## Slug Pre-Bind Protocol

```bash
# /rb:full skill body executes BEFORE invoking /rb:plan:

# 1. Derive slug from feature description (or accept plan path)
if [[ "$ARGUMENTS" == */plan.md ]]; then
  PLAN_DIR="$(dirname "$ARGUMENTS")"
else
  SLUG=$(printf '%s' "$ARGUMENTS" | tr '[:upper:] ' '[:lower:]-' | tr -cd '[:alnum:]-' | tr -s '-')
  PLAN_DIR=".claude/plans/${SLUG}"
fi

# 2. Create namespace
mkdir -p "${PLAN_DIR}/research"
: > "${PLAN_DIR}/scratchpad.md"

# 3. Write initial progress.md (see Initial Progress Schema)
# 4. Pre-bind marker
"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/active-plan-marker.sh" set "${PLAN_DIR}"

# 5. Invoke /rb:plan — it reads .claude/ACTIVE_PLAN directly with strict
#    guards (file exists, target dir exists, progress.md State is
#    INITIALIZING|DISCOVERING, plan.md absent) and reuses the pre-bound
#    slug.
```

## Initial Progress Schema

Skill body writes `progress.md` at INITIALIZING:

```markdown
# Progress: {slug}

- **State**: INITIALIZING
- **Started**: {ISO 8601 timestamp}
- **PLAN_DIR**: .claude/plans/{slug}

## Phase History

(transitions appended below as the cycle progresses)
```

Each phase transition appends to `## Phase History`:

```markdown
- {timestamp}: {FROM_STATE} → {TO_STATE} ({brief note})
```

## State Writer

Main-session only. `/rb:full` skill body owns every State write.

- Use Edit tool. Match `- **State**: <OLD_STATE>`. Replace with
  `- **State**: <NEW_STATE>`.
- Use Edit tool again to append transition entry at end:
  `- <ISO-8601-timestamp>: <OLD_STATE> → <NEW_STATE> (<note>)`.
- NEVER use raw shell (`sed -i`, `rm`, `>>`, `>`).

## Verification Gate

VERIFYING phase ordering (each gate must pass before the next):

1. Zeitwerk autoload check (`bundle exec rails zeitwerk:check`) — when Rails present
2. Lint / formatter (project-native preferred: `lefthook run pre-commit`,
   else `standardrb --no-fix` / `rubocop`)
3. Unit + request specs (`bundle exec rspec` or `bundle exec rake test`)
4. Brakeman (`bundle exec brakeman --quiet --no-progress`) — when present
5. Migration safety scan (`strong_migrations` / `pg_lock_visualizer`) — when migrations changed

Failure on any gate halts the cycle. Skill body writes
`**State**: HALTED_VERIFY_FAILED`. User decides next step.

## Active Plan Marker Lifecycle

Marker file: `.claude/ACTIVE_PLAN` (single line; absolute or repo-relative path).

| Phase | Marker action |
|---|---|
| INITIALIZING (`/rb:full`) | written to PLAN_DIR (pre-bind) |
| PLANNING (`/rb:plan`) | conditionally written; skipped if pre-bound to current slug |
| WORKING (`/rb:work` finishes all tasks) | cleared |
| VERIFYING / REVIEWING / COMPOUNDING / COMPLETED | NOT consulted; skill body uses local PLAN_DIR |

Note: standalone `/rb:plan` (no `/rb:full` pre-bind) writes the marker
unconditionally via `active-plan-marker.sh set` after `plan.md` write.

## Completion Criteria

Read `${CLAUDE_PLUGIN_ROOT}/skills/full/SKILL.md` § "Completion
Criteria". Do NOT duplicate the list here.

## Integration Points

| File / hook | Role |
|---|---|
| `.claude/ACTIVE_PLAN` | marker file; written by skill body at INITIALIZING |
| `${PLAN_DIR}/progress.md` | State machine ledger; updated every transition |
| `${PLAN_DIR}/scratchpad.md` | Decisions / hypotheses / blockers (durable workflow memory) |
| `${PLAN_DIR}/plan.md` | source of truth for WORKING phase |
| `${PLAN_DIR}/research/{topic}.md` | per-agent research artifacts (PLANNING phase) |
| `.claude/reviews/{review-slug}-{datesuffix}.md` | REVIEWING-phase consolidated artifact |
| `.claude/solutions/{category}/{fix}.md` | COMPOUNDING-phase capture |
| `plan-stop-reminder.sh` hook | reads `**State**:` line; skips reminder during autonomous run |
| `precompact-rules.sh` hook | reads marker for compaction context |
| `check-scratchpad.sh` hook | reads marker via `get_active_plan` (line 39) |
| `log-progress.sh` hook | reads marker for progress logging |
| `postcompact-verify.sh` hook | reads marker after compaction |
| `stop-failure-log.sh` hook | reads marker for failure context |
