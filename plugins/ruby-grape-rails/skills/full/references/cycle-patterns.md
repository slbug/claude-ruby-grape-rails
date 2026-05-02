# Cycle Patterns for Autonomous Development

## State Persistence

Canonical `progress.md` schema lives in `state-machine.md` §
"Initial Progress Schema" + "State Writer". Use that as source of
truth. Files map:

| Type | Path |
|------|------|
| Plan | .claude/plans/{slug}/plan.md |
| Progress | .claude/plans/{slug}/progress.md |
| Review | .claude/reviews/{review-slug}-{datesuffix}.md |

## Recovery Patterns

### Context Window Reset

When context window fills, Claude loses memory. Recovery:

1. Read `progress.md` to find current `**State**:`.
2. Read `plan.md` to find first unchecked task.
3. Continue from that task.

```
# Recovery prompt (auto-generated)
Resume feature development:
- Progress file: .claude/plans/{slug}/progress.md
- Current state: <named state from progress.md, e.g. WORKING>
- Last error: {error from progress.md Phase History}

Continue with /rb:work .claude/plans/{slug}/plan.md
```

### Session Restart

If session ends unexpectedly:

```bash
# Find most recent progress
ls -t .claude/plans/*/progress.md | head -1

# Check state
grep "State:" .claude/plans/*/progress.md | head -1

# Resume
/rb:work .claude/plans/{slug}/plan.md
```

### Blocker Recovery

When human resolves a blocker:

```bash
# Mark blocker resolved in progress file
# Then resume
/rb:work .claude/plans/{slug}/plan.md --from {task-id}
```

## Cycle Optimization

### Fast Path

For simple features (detected during discovery):

```
Simple feature detected (1 context, <5 files)
→ Skip comprehensive research
→ Minimal plan
→ Direct implementation
→ Quick review
```

### Parallel Phases

Some phases can overlap:

```
Phase 2: Context     ████████████
Phase 3: Hotwire/Turbo         ████████████  (starts when context API stable)
Phase 4: Tests                 ████████████  (starts with Phase 2)
```

## Failure Modes

### Recoverable Failures

| Failure | Recovery |
|---------|----------|
| Test failure | Analyze, fix, retry |
| Compile error | Read error, fix, retry |
| RuboCop warning | Auto-fix with `rubocop -a` or skip |
| Format issue | Run bundle exec rubocop -A |

### Non-Recoverable Failures

| Failure | Action |
|---------|--------|
| Schema design flaw | Stop, return to planning |
| Wrong approach | Stop, return to planning |
| External dependency down | Stop, wait, retry later |
| Max retries exceeded | Create blocker, continue |

### Cascade Prevention

Prevent one failure from cascading:

```
IF task fails 3 times:
  - Mark as blocker
  - Check if dependent tasks can proceed
  - IF yes: Continue with independent tasks
  - IF no: Mark phase as blocked, try next phase
```

## Metrics Tracking

Track for learning:

```markdown
## Metrics

| Metric | Value |
|--------|-------|
| Total Duration | 45 minutes |
| Cycles | 2 |
| Tasks Completed | 16 |
| Tasks Blocked | 1 |
| Retries | 4 |
| Review Issues | 3 |
| Tests Added | 12 |
| Test Coverage Delta | +5% |
```

## Advanced: Multi-Feature Coordination

When implementing related features:

```
Feature A: User Registration
Feature B: User Profile (depends on A)
Feature C: User Settings (depends on A)

Execution:
1. Complete Feature A
2. Start B and C in parallel (different agents)
3. Sync at integration points
```

## Integration

For phase transitions and gating rules see
`${CLAUDE_SKILL_DIR}/references/state-machine.md`. `/rb:full` does not
run git lifecycle commands directly; users own staging, commits,
branches, and release artifacts.

## Checkpoint Template

```markdown
## Checkpoint: {timestamp}
**Phase**: {current phase}
**Status**: {in-progress/blocked/complete}

### Completed
- {what was done}

### Blockers
- {what is blocked}

### Context
- {key decisions or findings}

### Next Phase
- {what comes next}
```

## Blocker Template

```markdown
## Blocker: {id}
**Phase**: {phase}
**Description**: {what's blocked}
**Attempts**: {what was tried}
**Options**:
- A: {option}
- B: {option}
```
