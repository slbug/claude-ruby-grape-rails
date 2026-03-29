# Execution Guide

Step-by-step execution details for `/rb:work`.

## Contents

- [Loading a Plan](#loading-a-plan)
- [Task Routing](#task-routing)
- [Parallel Task Execution](#parallel-task-execution)
- [Verification](#verification)
- [Proactive Patterns](#proactive-patterns)
- [Checkpoint Pattern](#checkpoint-pattern)
- [Phase Transitions](#phase-transitions)
- [Git Integration](#git-integration)
- [Error Recovery](#error-recovery)

## Loading a Plan

Read the plan file and count progress:

```markdown
## Phase 1: Schema Design [COMPLETED]
- [x] [P1-T1][active record] Create users migration
- [x] [P1-T2][active record] Add indexes

## Phase 2: Model Implementation [IN_PROGRESS]
- [x] [P2-T1][direct] Generate model with rails g model
- [ ] [P2-T2][active record] Add validations    <-- NEXT TASK
- [ ] [P2-T3][direct] Implement User.register
```

**Task ID format**: `[Pn-Tm]` where n=phase, m=task number.

With `--from P2-T3`: Skip directly to that task.

## Task Routing

### Primary: Parse Agent Annotation

Task format: `- [ ] [Pn-Tm][agent] Description`

```markdown
- [ ] [P2-T2][active record] Add validations to user model
                 ^^^^            
            Parse this annotation -> spawn active-record-schema-designer
```

### Routing Table

| Annotation | Agent | Verification |
|------------|-------|--------------|
| `[active record]` | active-record-schema-designer | migrate + test |
| `[hotwire]` | rails-architect | test + browser |
| `[sidekiq]` | sidekiq-specialist | test + manual |
| `[concurrency]` | ruby-runtime-advisor | test |
| `[security]` | security-analyzer | test + audit |
| `[test]` | testing-reviewer | test only |
| `[direct]` | (none) | syntax + format |

### Fallback: Keyword Matching (Legacy Plans)

If no `[agent]` annotation, fall back to keywords:

| Keywords (priority order) | Agent |
|---------------------------|-------|
| auth, login, password, token, permission | security-analyzer |
| migration, schema, validation, model | active-record-schema-designer |
| job, worker, queue, sidekiq | sidekiq-specialist |
| thread, async, concurrent | ruby-runtime-advisor |
| turbo, stimulus, stream | rails-architect |
| test, spec, mock | testing-reviewer |
| (no match) | (direct execution) |

**Security priority**: Security keywords ALWAYS win, even if other
patterns match.

### `[direct]` Task Guidance

Tasks annotated `[direct]` are simple and don't need a specialist:

- **Config changes**: Adding env vars, updating `config/application.rb`
- **Dependencies**: Adding gems to `Gemfile`, running `bundle install`
- **Scaffolding**: Creating directory structure, empty modules
- **Simple wiring**: Adding routes, requires, includes
- **File operations**: Moving, renaming, or deleting files

Implement these directly without spawning a Task agent. Run
verification (syntax check + format) after each one.

## Parallel Task Execution

Tasks under `### Parallel:` header execute via subagents:

### Detection

```markdown
## Phase 2: Forms [IN_PROGRESS]

### Parallel: Deal Forms
- [ ] [P2-T1][direct] Add selectors to occupier deal form
- [ ] [P2-T2][direct] Add selectors to landlord deal form
- [ ] [P2-T3][direct] Add selectors to seller deal form

### Sequential
- [ ] [P2-T4][direct] Update shared form helpers
```

Tasks are parallelizable if they:

- Are under a `### Parallel:` header
- Modify different files (check Locations in task description)
- Don't share mutable state (models, helpers)

### Spawning Pattern

Spawn ALL parallel tasks in ONE message using the Agent tool:

```
Agent(
  subagent_type: "general-purpose",
  description: "Implement P2-T1",
  prompt: "Implement P2-T1: Add currency/area unit selectors to
    occupier deal form at app/.../occupier_deal/.../details_form.rb.
    [full task context here]"
)
Agent(
  subagent_type: "general-purpose",
  description: "Implement P2-T2",
  prompt: "Implement P2-T2: Add selectors to landlord deal form..."
)
// ... one per parallel task
```

### Waiting and Checkpoint

After spawning, wait for ALL agents to complete, then run phase checkpoint:

```bash
bundle exec rubocop -A app/**/*.rb
bundle exec rails zeitwerk:check
bundle exec rspec <affected_test_files>
```

Mark all completed task checkboxes in the plan.

### When NOT to Parallelize

- Tasks that edit the same file
- Tasks that depend on each other's output
- Schema/migration tasks (database lock)
- Tasks with `[security]` annotation (need careful review)

## Verification

### After Each Task

```bash
bundle exec rubocop <changed_files>
bundle exec rails zeitwerk:check
```

When available, also check logs after code changes to catch
runtime errors invisible to static analysis.

### After Each Phase (Full)

```bash
bundle exec rails zeitwerk:check
bundle exec rspec <affected_test_files>
bundle exec rubocop
```

### Per-Feature Behavioral Smoke Test

After completing a feature (all phases for a domain), verify
end-to-end behavior:

| Annotation | Smoke Test Pattern |
|------------|-------------------|
| `[active record]` | Create record -> fetch -> verify fields match |
| `[hotwire]` | Navigate to route, check for JS errors |
| `[sidekiq]` | Enqueue job -> check Sidekiq web UI for state |
| `[security]` | Test unauthenticated access returns error |
| `[direct]` | Verify no regressions in logs |

Use tests with transactions to verify without persisting data.

### After ALL Phases (Final Gate)

```bash
bundle exec rspec  # full suite
```

### Ruby-Specific Verification

After each task, also run domain-appropriate checks:

| After | Extra Verification |
|-------|-------------------|
| `[active record]` task | Verify migration safety, check N+1 queries |
| `[hotwire]` task | Verify Turbo Stream usage, Stimulus controllers |
| `[sidekiq]` task | Verify idempotency, job args are JSON-safe |
| `[security]` task | Verify authorization in every controller action |

If verification fails, fix the issue and re-verify. After 3 failed
attempts, create a BLOCKER (see error-recovery.md).

## Proactive Patterns

### Factory Updates for Required Fields

When a task adds validations with `validates :field, presence: true`,
BEFORE running tests: grep for all factories that build the affected
model (`FactoryBot.create(:X)`, `build(:X)`, `def X_factory`), add
new required fields with sensible defaults to EVERY factory, THEN
run the test suite. Prevents cascading test failures from missing
factory fields.

### Module Existence Check

When a plan says "create new module" or "extract to new module":

1. FIRST check if the module/class already exists:

   ```bash
   grep -rn "class MyApp::ModuleName" app/
   grep -rn "module MyApp::ModuleName" app/
   ```

2. If it exists, add to the existing module instead of creating a
duplicate file (causes load errors from duplicate definitions)

## Checkpoint Pattern

After each task passes verification:

1. **Update plan**: Mark checkbox `- [x] [Pn-Tm]...` and **append
   implementation note** — key decisions, gotchas, actual values.
   Example: `- [x] [P2-T2] Add password validations — used bcrypt, 12 rounds, added virtual :password`
   These notes survive context compaction since the plan is re-read on resume.
2. **Update phase status**: If all tasks done, change to `[COMPLETED]`
3. **Log progress**: Append to `.claude/plans/{feature}/progress.md`
4. **Start next task**: Move to next unchecked task

### Progress Log Entry

```markdown
## 14:32 - Task Completed [P2-T2]

**Task**: Add password validations to user model
**Files Modified**: app/models/user.rb, db/migrate/xxx_add_password_to_users.rb
**Verification**: PASS (syntax, format, tests)
```

## Phase Transitions

**CRITICAL: Auto-continue between phases.** When all tasks in a
phase complete, mark it `[COMPLETED]` and IMMEDIATELY start the
next phase. Do NOT stop to ask the user. Do NOT output a summary
between phases. Just keep going until all phases are done or a
BLOCKER is hit.

```markdown
# Before
## Phase 1: Schema Design [IN_PROGRESS]
- [x] [P1-T1] Create users migration
- [x] [P1-T2] Add indexes
- [x] [P1-T3] Create user model

# After
## Phase 1: Schema Design [COMPLETED]
- [x] [P1-T1] Create users migration — citext for email, added password_digest string field
- [x] [P1-T2] Add indexes — unique on email, composite on [user_id, status]
- [x] [P1-T3] Create user model — used has_secure_password, added virtual :password

## Phase 2: Controller Implementation [IN_PROGRESS]  <-- Auto-start immediately
```

## Git Integration

### Commit Strategy

Don't commit after every task. Instead:

1. **After each phase**: Offer to create commit with phase summary
2. **After blockers**: Commit working state before human intervention
3. **After completion**: Ask user about final commit

### Branch Strategy (for /rb:full)

```bash
git checkout -b feature/{feature-slug}
# ... phases execute ...
# On completion, ready for PR
```

## Error Recovery

### Auto-Fix (Common Errors)

| Error Pattern | Auto-Fix |
|--------------|----------|
| RuboCop auto-correctable | Run `bundle exec rubocop -A` |
| Unused variable | Prefix with `_` |
| Missing require | Add require statement |

### Retry with Context

If first attempt fails, retry with error context in the prompt.

### Escalate to BLOCKER

After 3 failures, create blocker in progress file:

```markdown
## BLOCKER

**Task ID**: P2-T3
**Description**: Implement User.register
**Attempts**: 3

**Error History**:
1. Syntax error: undefined method hash_password
2. Test failure: expected User got nil
3. Test failure: validation errors [:email, "has already been taken"]

**Suggested Actions**:
- Review test setup (database not cleaned?)
- Check has_secure_password configuration
- Verify unique constraint handling

**Resume**: `/rb:work plan.md --from P2-T3`
```
