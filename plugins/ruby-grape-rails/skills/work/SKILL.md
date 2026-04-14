---
name: rb:work
description: Use after /rb:plan to implement an existing checklist, resume active code changes, and verify each step in Active Record or Sequel work. Can resume the newest active plan automatically.
argument-hint: <path to plan file>
effort: high
---
# Work

Execute the unchecked tasks from a plan file.

## Usage

- `/rb:work .claude/plans/user-auth/plan.md`
- `/rb:work .claude/plans/user-auth/plan.md --from P2-T3`
- `/rb:work` (resumes the active plan)

## Iron Laws

1. Never auto-start `/rb:review`.
2. Plan checkboxes are the state - check them off as you complete.
3. Read `scratchpad.md` before implementing.
4. Verify after every task with the project's actual toolchain.
5. After three failed attempts, create a blocker instead of thrashing.
6. Ask when a task is ambiguous rather than guessing.
7. Prefer small, verifiable commits over large changes.
8. Keep Iron Laws visible - review them before each task batch.

## Execution State Machine

```
START ──▶ READ PLAN ──▶ ANALYZE CONTEXT ──▶ PICK TASK
                              │                   │
                              ▼                   ▼
                        CHECK SCRATCHPAD ◀──────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │   IMPLEMENT TASK      │
                  │   - Read files        │
                  │   - Make changes      │
                  │   - Verify            │
                  └───────────┬───────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              [SUCCESS]            [FAILURE]
                    │                   │
                    ▼                   ▼
           CHECK OFF TASK ◀─── CREATE BLOCKER
                    │         (after 3 tries)
                    ▼
              MORE TASKS?
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       [YES]              [NO]
          │                   │
          ▼                   ▼
    PICK NEXT TASK      UPDATE PLAN
                              │
                              ▼
                        SUMMARIZE & OFFER
                        /rb:review
```

## Startup Sequence

When starting work:

1. **Locate the plan**
   - Check explicit marker: `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/active-plan-marker.sh get`
   - If no marker or invalid, find newest plan with unchecked tasks
   - Use argument if provided (overrides marker)

2. **Validate marker** - ensure plan exists and has unchecked tasks

3. **Read plan.md** - understand scope, phases, risks

4. **Read scratchpad.md** - understand context, decisions

5. **Check current status** - which tasks are complete?

6. **Identify next task** - first unchecked item

7. **Identify package + ORM context** - in modular or mixed repos, determine which package owns the task and whether it uses Active Record or Sequel

8. **Load relevant context** - files, dependencies, tests

## Routing Hints

Task hints indicate which domain expertise to apply:

- `[rails]` controller/view/service wiring, routing, helpers
- `[grape]` API params, versioning, endpoint behavior, serializers
- `[ar]` schema, query, migration, locking, transaction work
- `[sequel]` datasets, Sequel models, Sequel migrations, DB.transaction work
- `[sidekiq]` jobs, queueing, retries, enqueue-after-commit
- `[security]` authn/authz, parameter shaping, unsafe rendering, secrets
- `[perf]` query plans, caching, Redis, hot paths, N+1 prevention
- `[ruby]` plain Ruby refactors, library code, gems
- `[hotwire]` Turbo Streams, Stimulus controllers, frames
- `[test]` specs, factories, test data, coverage

## Task Execution Protocol

### Before Starting a Task

1. **Understand the scope**
   - What files need to change?
   - What's the expected outcome?
   - Are there dependencies on other tasks?

2. **Check Iron Laws**
   - Review relevant Iron Laws for this domain
   - Keep them visible while working

3. **Load context**
   - Read existing files
   - Check related code
   - Identify package boundary if repo is modular
   - Look at existing patterns

### During Implementation

1. **Make incremental changes**
   - One logical change at a time
   - Run verification between changes
   - Don't batch unrelated changes

2. **Follow existing patterns**
   - Match code style
   - Use existing abstractions
   - Don't introduce new patterns without reason

3. **Keep verification running**
   - Save and test frequently
   - Fix errors immediately
   - Don't let errors accumulate

For domain-specific implementation patterns and deeper checklists, see
`${CLAUDE_SKILL_DIR}/references/execution-guide.md`.

## Verification Tiers

### Per Task (Immediate)

- Syntax check: `ruby -c file.rb`
- Formatter: direct `bundle exec standardrb --fix file.rb` or `bundle exec rubocop -a`; Lefthook is only acceptable when its config covers lint + security/static-analysis checks
- Type check if available: `bundle exec srb tc`

### Per Phase (Checkpoint)

- Zeitwerk check: `bundle exec rails zeitwerk:check` only for full Rails apps
- Targeted tests: `bundle exec rspec spec/models/user_spec.rb`
- Linter full pass: whichever configured direct linter is available (`standardrb` first, otherwise `rubocop`)

### Final Gate (Completion)

- Full test suite: `bundle exec rspec` or `bin/rails test`
- Security scan: `bundle exec brakeman` (if available)
- Optional final diff-scoped review: `eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref)"` then `bundle exec pronto run -c "$BASE_REF"`
- Static analysis: `bundle exec rails_best_practices`

## Error Handling & Recovery

### When a Task Fails

1. **First failure**: Diagnose, fix, retry
2. **Second failure**: Step back, check assumptions
3. **Third failure**: Create blocker, move on

### Blocker Format

```markdown
## Blocker: {Task ID}

**Task**: {description}

**Problem**: {what went wrong}

**Attempts**:
1. {what you tried}
2. {what you tried}
3. {what you tried}

**Blocking on**: {what's needed}

**Options**:
- A: {option}
- B: {option}
```

### Recovery Patterns

| Situation | Action |
|-----------|--------|
| Test fails | Read error carefully, check test setup |
| Syntax error | Check line number, look for missing `end` |
| Zeitwerk fail | Check file naming, module nesting |
| Migration error | Check version, roll back if needed |
| Merge conflict | Pause, ask user for resolution |

## Progress Tracking

Update plan.md after each task:

```markdown
- [x] {completed task} ✓ {timestamp}
- [ ] {current task} ▶ {timestamp}
- [ ] {next task}
```

Use emoji markers:

- ✓ Completed
- ▶ In progress
- 🚧 Blocked
- ⏸️ Paused

## Resumption Pattern

When resuming work:

1. Read `plan.md` to see current state
2. Read `scratchpad.md` for context
3. Identify the next unchecked task
4. Pick up where you left off
5. Update timestamps

## Scratchpad Integration

Update `scratchpad.md` with:

- `## Dead Ends`
  - failed approaches and why they failed
- `## Decisions`
  - implementation choices, trade-offs, and discovered infrastructure
- `## Hypotheses`
  - ideas worth testing later
- `## Open Questions`
  - unresolved concerns to revisit
- `## Handoff`
  - branch state, API failures, or next-step notes

Follow the canonical structure in
`${CLAUDE_SKILL_DIR}/../plan/references/scratchpad-template.md`. Prefer appending to the
existing sections rather than inventing new top-level headings.

## Completion Protocol

When all tasks are checked:

1. **Update plan.md**
   - Mark all tasks complete
   - Add completion timestamp
   - Update status to "done"

2. **Final verification**
   - Run full test suite
   - Run security scan
   - Check formatter

3. **Summarize changes**
   - Files modified
   - Features added
   - Tests added

4. **Offer next steps**
   - `/rb:review` - for code review
   - `/rb:brief` - for documentation
   - Manual continuation - for more work

## Stop Conditions

Stop and ask the user when:

- Requirements are unclear
- A decision needs user input
- Security implications are significant
- Breaking changes are introduced
- Performance impact is unknown
- Third attempt at a task fails

## Completion

When all tasks complete or user explicitly stops:

1. **Clear the active plan marker** (prevents auto-resume on next `/rb:work`):

   Run `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/active-plan-marker.sh clear`.

2. **Summarize progress** - what was accomplished

3. **Offer next step**:
   - `/rb:review` if all tasks done
   - `/rb:compound` to capture solution
   - New planning if scope changed

## Success Metrics

Good work sessions have:

- [ ] All tasks completed or blocked with clear reason
- [ ] No uncommitted changes
- [ ] Tests passing
- [ ] Plan updated
- [ ] Scratchpad current
- [ ] Clear next steps identified
