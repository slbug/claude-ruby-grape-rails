# Error Recovery

## Verification Rules

Verification is tiered to balance speed and safety:

**Per-task** (after each task):

| Change Type | Verification Steps |
|-------------|-------------------|
| Any .rb file | Configured direct linter (`bundle exec standardrb --fix` or `bundle exec rubocop -A`) + `bundle exec rails zeitwerk:check` when full Rails app |
| Schema/migration | Above + `bin/rails db:migrate` (dev) |

**Per-phase** (after all tasks in a phase):

| Scope | Verification Steps |
|-------|-------------------|
| Full Rails app | `bundle exec rails zeitwerk:check` |
| Always | `bundle exec rspec <affected_test_files>` |
| Always | Configured direct linter (`bundle exec standardrb` or `bundle exec rubocop`) |

**Final gate** (after all phases): `bundle exec rspec` (full suite)

## When Verification Fails

1. **Syntax error**: Read error, fix, retry
2. **Test failure**: Analyze failure, fix code or test
3. **RuboCop warning**: Auto-fix if possible, else flag
4. **After 3 retries**: Log blocker, skip task, continue

## BLOCKER Format

```markdown
## BLOCKER: Task could not be completed

**Task ID**: P2-T3
**Task**: Implement User.register
**Attempts**: 3
**Last Error**: Test assertion failed - expected User got nil
**Files**: app/models/user.rb:45

**Action Required**: Human review needed
**Resume**: `/rb:work plan.md --from P2-T3`
```

**Also write a DEAD-END entry** to the scratchpad so future
sessions don't re-try the same failed approach:

```markdown
### [HH:MM] DEAD-END: {task description}
Tried: {approach attempted}. Failed because: {root cause}.
Attempts: 3. See BLOCKER in progress.md for full error.
```

Append to `.claude/plans/{slug}/scratchpad.md`.

## Recovery After BLOCKER

When user resolves a blocker and resumes:

1. Re-read the plan file for current checkbox state
2. Start from the previously blocked task
3. Verify the fix compiles and tests pass
4. Mark checkbox and continue
