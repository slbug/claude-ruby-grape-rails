# Workflow Orchestrator Playbook

Use this playbook when `workflow-orchestrator` needs detailed templates or
phase examples without bloating the main agent file.

## Phase Details

- `INITIALIZING`: load context, detect runtime, create namespace
- `DISCOVERING`: inspect code, patterns, and likely file set
- `PLANNING`: delegate to `planning-orchestrator`
- `WORKING`: execute unchecked tasks and log blockers
- `VERIFYING`: run the verification stack
- `REVIEWING`: delegate to `parallel-reviewer`
- `COMPOUNDING`: capture learnings and reusable patterns
- `COMPLETED`: summarize and archive as appropriate

## Phase Transitions

- `INITIALIZING -> DISCOVERING`: namespace + context ready
- `DISCOVERING -> PLANNING`: enough code context to plan safely
- `PLANNING -> WORKING`: `plan.md` written with tasks and verification
- `WORKING -> VERIFYING`: tasks complete or explicitly deferred
- `VERIFYING -> REVIEWING`: checks pass
- `REVIEWING -> COMPOUNDING`: critical issues resolved or triaged
- `COMPOUNDING -> COMPLETED`: learnings captured

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

## Verification Gate

Run in this order when applicable:

1. `bundle exec rails zeitwerk:check`
2. configured formatter/linter
3. full or targeted test suite
4. `bundle exec brakeman`
5. optional extra checks like `srb tc`, `steep check`, `reek`

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

## Progress File Skeleton

```markdown
# Progress: {Feature Name}

## Current State
**Phase**: {phase}
**Status**: {active/blocked/completed}
**Last Updated**: {timestamp}

## Phase History
- [x] INITIALIZING
- [x] DISCOVERING
- [x] PLANNING
- [▶] WORKING
- [ ] VERIFYING
- [ ] REVIEWING
- [ ] COMPOUNDING
- [ ] COMPLETED

## Checkpoints
{links}

## Blockers
{active blockers}

## Decisions
{key decisions}
```

## Integration Points

- `/rb:plan` owns decomposition and research coordination
- `/rb:work` owns task execution and checkbox state
- `/rb:review` owns findings-first read-only review
- `/rb:compound` owns durable learning capture
