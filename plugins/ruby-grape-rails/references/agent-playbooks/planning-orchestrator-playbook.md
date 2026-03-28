# Planning Orchestrator Playbook

Use this playbook when `planning-orchestrator` needs detailed examples or
templates that should not live in the main routing surface.

## Agent Selection Matrix

| Request Contains | Spawn Agent |
|-----------------|-------------|
| Rails UI/feature | `rails-patterns-analyst` + `rails-architect` |
| Database changes | `active-record-schema-designer` |
| Background jobs | `sidekiq-specialist` |
| Auth/payments/admin | `security-analyzer` |
| New gem/library | `ruby-gem-researcher` |
| Cross-cutting change | `call-tracer` |
| Complex workflow | `rails-architect` |
| API changes | `rails-patterns-analyst` + `security-analyzer` |

## Spawning Strategy

```text
Phase 1: Research (Parallel)
├─ rails-patterns-analyst
├─ active-record-schema-designer
├─ security-analyzer
└─ sidekiq-specialist

Phase 2: Architecture (if needed)
└─ rails-architect
```

## Agent Briefing Template

```text
Task: Analyze [aspect] for [feature]

Context:
- Feature: [description]
- Files involved: [list]
- Constraints: [list]
- Questions to answer:
  1. [question]
  2. [question]

Output format: [structured response]
```

## Progress Tracking Template

```markdown
## Agent Coordination

### Spawned
- [x] rails-patterns-analyst (completed)
- [x] active-record-schema-designer (completed)
- [▶] security-analyzer (in progress)
- [ ] sidekiq-specialist (pending)

### Findings Summary
- Patterns: [key findings]
- Schema: [key findings]
- Security: [awaiting]
- Jobs: [pending]
```

## Task Decomposition Guidance

Default decomposition shape:

1. foundation
2. implementation
3. integration
4. polish

Task format:

```markdown
- [ ] [task description] ([routing-hint])
  - Context: [what to know]
  - Verification: [how to verify]
  - Dependencies: [what must come first]
```

## Routing Hints

- `[rails]` controllers, views, routes, helpers
- `[grape]` endpoints, params, serializers, versioning
- `[ar]` Active Record models, queries, migrations
- `[sidekiq]` jobs, queues, retries, enqueue-after-commit
- `[security]` auth, validation, encryption, secrets
- `[perf]` caching, queries, optimization
- `[ruby]` pure Ruby services and libraries
- `[hotwire]` Turbo, Streams, Stimulus
- `[test]` specs, factories, coverage

## Plan Template

```markdown
# Plan: {Feature Name}

## Overview
**Goal**: {one sentence}
**Scope**: {boundaries}
**Risk Level**: {low/medium/high}
**Estimated Effort**: {N} tasks, {N} hours

## Research Findings
{summary of agent findings}

## Design Decisions
{key choices}

## Tasks
- [ ] {task} [hint]

## Verification Checklist
- [ ] {verification step}

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk} | {L/M/H} | {L/M/H} | {strategy} |
```

## Common Planning Pitfalls

- over-planning: too many tasks, too much implementation detail
- under-planning: missing verification or risk coverage
- wrong agents: missing security / jobs / schema specialists
- ignoring context: not reading the existing code before decomposing work
