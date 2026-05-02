# Full Cycle Execution Steps

The canonical state machine lives in
`${CLAUDE_SKILL_DIR}/references/state-machine.md`. This file documents
only execution-time observations and patterns NOT covered there.

## Execution Notes

- `/rb:full` always derives `PLAN_DIR` and writes `progress.md` BEFORE
  invoking `/rb:plan`. The marker is set during INITIALIZING.
- After `/rb:work` clears the marker, the skill body uses LOCAL
  `PLAN_DIR` for State writes through COMPOUNDING and COMPLETED.
- Failure gates are HARD STOPS: blockers in `/rb:work`, failed
  `/rb:verify --full`, or Critical findings in `/rb:review` halt the
  cycle. State writes record the halt phase. No autonomous re-run.
- `/rb:compound ${PLAN_DIR}/plan.md` runs only when no Critical issues
  remain (this skill accepts a plan path arg).
- For an existing plan path argument, `/rb:full` skips `/rb:plan` and
  starts at WORKING with the inherited namespace.

For complete state transitions, slug pre-bind protocol, marker
concurrency notes, verification gate ordering, and progress.md
schema — see `state-machine.md`.
