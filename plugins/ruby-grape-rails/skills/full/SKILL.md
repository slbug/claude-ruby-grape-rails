---
name: rb:full
description: "Use when running the hands-off end-to-end lifecycle: autonomously runs plan, work, verify, review, and compound in one command with no user intervention needed."
when_to_use: "Triggers: \"do everything\", \"full lifecycle\", \"hands-off\", \"plan and implement\", \"end to end\"."
argument-hint: "<feature description OR plan path>"
effort: xhigh
---
# Full Workflow

`/rb:full` runs the full plan-work-verify-review-compound cycle autonomously.
Skill body owns the complete cycle from main session.

## Cycle

0. `/rb:brainstorm` (optional) → if requirements vague
1. `/rb:plan` → reuses pre-bound namespace; produces plan.md via main-session research fanout
2. `/rb:work` → executes plan tasks; clears active-plan marker on completion
3. `/rb:verify` → runs full verification stack (no plan-path arg; resolves from current branch)
4. `/rb:review` → main-session review fanout (no plan-path arg; resolves from diff)
5. `/rb:compound` → captures learnings; accepts plan path arg

Use `/rb:full` for well-scoped work where the user wants the full cycle.
Skip for vague requirements or trivial fixes.

## State Machine (summary)

```text
INITIALIZING → DISCOVERING → PLANNING → WORKING → VERIFYING → REVIEWING → COMPOUNDING → COMPLETED
```

`/rb:full` skill body writes `**State**:` to `progress.md` at every
transition. The `plan-stop-reminder.sh` hook checks for this field to
skip the manual plan-presentation reminder during autonomous runs.

## PLAN_DIR Tracking

- Derive `PLAN_DIR` once at INITIALIZING; track as local variable through
  the cycle.
- Use PLAN_DIR for skill-body's own progress.md State writes only.
- Do NOT pass PLAN_DIR as CLI arg to `/rb:verify` or `/rb:review`.
- Do pass `${PLAN_DIR}/plan.md` to `/rb:compound`.
- After `/rb:work` clears the active-plan marker, continue using local
  PLAN_DIR. Do NOT re-read the marker mid-cycle.

## Slug Pre-Bind Protocol (summary)

`/rb:full` creates the plan namespace and writes initial `progress.md`
BEFORE invoking `/rb:plan`. `/rb:plan` reads `.claude/ACTIVE_PLAN`
directly with strict guards (NOT via `active-plan-marker.sh get`,
which has disk-glob fallbacks) and reuses the pre-bound slug.

## Completion Criteria

A workflow is COMPLETED when:

- [ ] All planned tasks completed or explicitly deferred
- [ ] Verification suite passes
- [ ] Reviews complete with no critical issues
- [ ] Learnings captured in compound docs
- [ ] `progress.md` final write: `**State**: COMPLETED`
- [ ] User acknowledged completion

## Laws

- **Never skip verification** — Always run full verification suite
- **Never hide blockers** — Log them in progress.md and scratchpad.md
- **Re-read plan.md after compaction** — Checkboxes remain source of truth
- **Prefer small steps** — Checkpoint frequently
- **Maintain state externally** — Files, not memory
- **Delegate appropriately** — Don't do specialist work in main session
- **Ask when uncertain** — Better to clarify than assume

## Detail References

For implementation detail (state machine table, transition rules, slug
pre-bind protocol with example bash, marker concurrency notes,
Verification Gate ordering, Initial Progress Schema, Integration Points),
see:

- `${CLAUDE_SKILL_DIR}/references/state-machine.md`
- `${CLAUDE_SKILL_DIR}/references/cycle-patterns.md`
- `${CLAUDE_SKILL_DIR}/references/execution-steps.md`
- `${CLAUDE_SKILL_DIR}/references/safety-recovery.md`
- `${CLAUDE_SKILL_DIR}/references/example-run.md`
