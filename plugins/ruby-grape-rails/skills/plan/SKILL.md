---
name: rb:plan
description: Use for any multi-file feature, new boundary, risky refactor, background job workflow, API change, or database change that benefits from upfront design. Also accepts review files and existing plans.
argument-hint: <feature description OR path to review/plan file>
disable-model-invocation: true
---

# Plan Ruby/Rails/Grape Work

Plan a feature by spawning Ruby specialists, then write a structured plan with checkboxes.

## What Makes /rb:plan Different

1. It routes research through Ruby/Rails/Grape specialists.
2. It plans with `[rails]`, `[grape]`, `[ar]`, `[sidekiq]`, `[security]`, `[perf]`, `[ruby]` task hints.
3. It bakes in verification gates for Zeitwerk, formatter, tests, and optional Brakeman.
4. It understands Rails controllers, service objects, Active Record, Grape APIs, Redis, and Sidekiq jobs.

## Workflow State Machine

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   START     │───▶│  RESEARCH   │───▶│   DESIGN    │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐
│    DONE     │◀───│  EXECUTE    │◀───│    PLAN     │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                   ┌──────▼──────┐
                   │  VERIFY     │
                   └─────────────┘
```

Each phase has entry/exit criteria. Do not skip phases.

## Research Phase

Spawn only what the request needs:

### Core Research Agents

- `rails-patterns-analyst` - Rails conventions and patterns
- `active-record-schema-designer` - Database schema and AR patterns
- `security-analyzer` - Security implications and Brakeman checks
- `sidekiq-specialist` - Background job design and queue strategy
- `ruby-gem-researcher` - Gem evaluation and alternatives
- `call-tracer` - Code flow analysis and dependency tracing
- `rails-architect` - High-level architecture decisions

### Research Checklist

- [ ] Identify all files that will be created/modified
- [ ] Document transaction boundaries
- [ ] Note after-commit behavior requirements
- [ ] List external dependencies (gems, services)
- [ ] Identify security considerations
- [ ] Assess performance implications

## Design Phase

### Breadboarding for Hotwire/Turbo

When planning Hotwire features, sketch the wireframe:

```
┌─────────────────────────────────────┐
│  [Frame: users#index]               │
│  ┌─────────┐  ┌─────────────────┐  │
│  │ Sidebar │  │  Users Table    │  │
│  │         │  │  [turbo-frame]  │  │
│  │ Filters │  │  ┌─────┐┌─────┐ │  │
│  │         │  │  │ Edit││Del  │ │  │
│  └─────────┘  │  │[link]│[btn]│ │  │
│               │  └─────┘└─────┘ │  │
│               │  [pagy]         │  │
│               └─────────────────┘  │
└─────────────────────────────────────┘
```

### Design Decisions to Document

1. **Transaction Boundaries**: Where do transactions start/end?
2. **Enqueue Timing**: `after_commit` vs `after_save` vs inline
3. **Error Handling**: What happens when things fail?
4. **Idempotency**: Can this operation run multiple times safely?
5. **Rollback Strategy**: How to undo if something goes wrong?

## Ruby Planning Laws

1. Never auto-start `/rb:work` after writing the plan.
2. Prefer the existing stack before adding a gem.
3. Every review finding must become a task or an explicit defer decision.
4. Record transaction boundaries, after-commit behavior, and verification strategy in the plan.
5. Use web research for unfamiliar gems, Rails features, or Grape behavior.
6. Design for testability from the start - each task should be verifiable.
7. Plan for the worst case: network failures, database locks, job retries.

## Checkpoint & Continue Pattern

Plans may be interrupted. Use this pattern:

```markdown
## Checkpoint: {timestamp}
- Phase: {current phase}
- Completed: {what's done}
- Blocked on: {any blockers}
- Next: {next task}

## Continue
When resuming:
1. Read `.claude/plans/{slug}/plan.md`
2. Check off completed tasks
3. Resume from next unchecked item
```

## Error Recovery Planning

### Ralph Wiggum Debugging Checklist

Before finalizing the plan, verify:

- [ ] No bare `rescue` - always specify exception classes
- [ ] `StandardError` caught, not `Exception`
- [ ] Failed jobs can be retried safely (idempotent)
- [ ] Database transactions wrap multi-step operations
- [ ] Sidekiq jobs use `after_commit` not `after_save`
- [ ] N+1 queries prevented with `includes` or `preload`
- [ ] Money uses `decimal`, not `float`
- [ ] No sensitive data in logs
- [ ] JSON arguments for Sidekiq (not symbols, no Ruby objects)

### Recovery Strategies by Failure Type

| Failure Type | Strategy | Implementation |
|--------------|----------|----------------|
| DB Rollback | Transaction rescue | `rescue ActiveRecord::Rollback` |
| Job Fail | Retry with backoff | `sidekiq_options retry: 5` |
| External API | Circuit breaker | `circuitbox` or custom |
| Validation | Early return | Guard clauses, service objects |
| Timeout | Async fallback | Background job, notification |

## Verification Checklist to Include in Plans

- `bundle exec rails zeitwerk:check` if Rails is present
- formatter/linter if configured (`standardrb` or `rubocop`)
- targeted specs or tests for changed behavior
- `bundle exec brakeman` if present for security-sensitive work
- `bundle exec rspec` or `bin/rails test` - full test suite
- Migration safety check (for production deployments)

## Compound Documentation Lookup

When planning, check these references for patterns:

1. `ruby-idioms` - Ruby 3.4+ features, `it` keyword, pattern matching
2. `rails-idioms` - Rails 8 patterns, Solid Queue, Thruster
3. `active-record-patterns` - Transactions, N+1 prevention, enums
4. `sidekiq` - Job design, retries, enqueue-after-commit
5. `security` - Brakeman, SQL injection, XSS prevention
6. `testing` - RSpec/Minitest patterns, factories, VCR

Spawn `compound-docs` agent if you need synthesis across multiple domains.

## Agent Spawning with Progress Tracking

When spawning multiple agents:

```
Spawn Order:
1. rails-patterns-analyst (async) - analyze existing patterns
2. security-analyzer (async) - identify risks
3. sidekiq-specialist (async) - job design
4. active-record-schema-designer (async) - schema changes

Wait for all, then synthesize findings.
```

Track progress:

- Use todo lists with status markers
- Update as agents complete
- Note any blocking findings

## Plan Structure Template

```markdown
# Plan: {Feature Name}

## Overview
- Goal: {one sentence}
- Scope: {what's in/out}
- Risk Level: {low/medium/high}

## Research Findings
{summary of agent findings}

## Design Decisions
{architecture choices, trade-offs}

## Tasks

### Phase 1: Setup & Migration
- [ ] {task with [rails] hint}
- [ ] {task with [ar] hint}

### Phase 2: Implementation
- [ ] {task with [ruby] hint}
- [ ] {task with [sidekiq] hint}

### Phase 3: Verification
- [ ] Run zeitwerk:check
- [ ] Run formatter
- [ ] Run tests
- [ ] Run brakeman

## Risks & Mitigations
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| {risk} | {L/M/H} | {strategy} |

## Checkpoint
- Created: {timestamp}
- Last Updated: {timestamp}
- Status: {planning/ready/in-progress}
```

## Output

Write the plan to `.claude/plans/{slug}/plan.md`.

**After creating the plan, set the active plan marker:**

```bash
${CLAUDE_PLUGIN_ROOT}/hooks/scripts/active-plan-marker.sh set .claude/plans/{slug}
```

This marker allows `/rb:work` to auto-detect which plan to resume, enables session resume detection, and tracks the current active plan for context-aware operations.

Then stop and present:

- task count
- phases
- key risks
- recommended next step (`/rb:brief` or `/rb:work`)

## Success Criteria

A good plan has:

- [ ] 5-20 granular tasks with clear hints
- [ ] Transaction boundaries documented
- [ ] After-commit behavior specified
- [ ] Verification steps for each phase
- [ ] Error recovery strategy
- [ ] No hidden assumptions
