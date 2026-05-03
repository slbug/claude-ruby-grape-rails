---
name: rb:plan
description: "Use when you need an implementation plan for multi-file Rails or Grape features, Sidekiq changes, or risky migrations and refactors before coding starts. Also accepts review files and existing plans."
when_to_use: "Triggers: \"plan this feature\", \"make a plan\", \"implementation plan\", \"how should we build\", \"plan before coding\". Does NOT handle: brainstorming ideas, implementing code, code review."
argument-hint: <feature description OR path to review/plan file>
effort: xhigh
---
# Plan Ruby/Rails/Grape Work

Plan a feature by spawning Ruby specialists, then write a structured plan with checkboxes.

## What Makes /rb:plan Different

1. It routes research through Ruby/Rails/Grape specialists.
2. It plans with `[direct]`, `[active record]`, `[hotwire]`, `[sidekiq]`, `[concurrency]`, `[security]`, `[test]` task annotations (canonical Set A; consumed by `/rb:work`).
3. In mixed stacks, it identifies the owning package and ORM before planning changes.
4. It bakes in verification gates for Zeitwerk, formatter, tests, and optional Brakeman.
5. It understands Rails controllers, service objects, Active Record, Sequel, Grape APIs, Redis, and Sidekiq jobs.

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

## Slug Pre-Bind Detection (`/rb:full` integration)

Before deriving a fresh slug, check for an EXPLICIT pre-set marker. Read
`.claude/ACTIVE_PLAN` directly — do NOT call `active-plan-marker.sh get`,
because that script falls back to disk globs (newest plan with unchecked
tasks, newest planning-phase dir) which can return an unrelated namespace.

Apply 4 strict guards before reusing a pre-bound namespace:

1. `.claude/ACTIVE_PLAN` exists and is not a symlink
2. The path it points to is an existing non-symlink directory
3. That directory contains a non-symlink `progress.md` whose `**State**:`
   line equals `INITIALIZING` or `DISCOVERING`
4. That directory does NOT yet contain `plan.md` (pre-plan phase)

All 4 must pass — otherwise derive a fresh slug, create namespace, and
set the marker AFTER `plan.md` write (existing standalone behavior).

This protocol allows `/rb:full` to pre-bind the namespace before invoking
`/rb:plan`. When `/rb:plan` runs standalone (no marker, or marker fails
the strict guards), behavior is unchanged: derive fresh slug.

For the exact shell-guard sequence, see
`${CLAUDE_SKILL_DIR}/references/planning-workflow.md` §
"Slug Pre-Bind Detection (strict guards)".

## Interview Detection (from /rb:brainstorm)

Before asking clarification questions, check for a brainstorm interview:

1. Check `$ARGUMENTS` for a path containing `interview.md` (explicit path always wins)
2. If no explicit path, glob `.claude/plans/*/interview.md` for files modified
   within the last 24 hours. If multiple match, use the newest by mtime.

If found with `Status: COMPLETE`:

- Read the interview.md Summary and Coverage Details
- Skip clarification questions — the interview IS the clarification
- Use interview content as input for agent spawning (depth detection still applies)
- Note in scratchpad: "Requirements from /rb:brainstorm interview"

If found with `Status: IN_PROGRESS`:

- Read what exists, note gaps in coverage
- Ask ONLY about uncovered dimensions (don't re-ask covered ones)

## Research Phase

Before finalizing tasks, identify:

- the owning package/app root for the touched code
- the active ORM for that package
- whether the repo uses Packwerk or a similar modular-monolith layout

If no explicit Packwerk signal is found but the repo appears modular, ask:

`No Packwerk detected. Do you have something similar implemented? Where are the modules/packages and what stack/ORM does each use?`

Before spawning topic research, reuse fresh planning research when it
is clearly relevant:

- check `.claude/research/*.md` and `.claude/plans/*/research/*.md`
- treat research docs as reusable only when they contain a parseable
  in-file freshness header within the last 48 hours
- accepted header keys:
  `Last Updated:`, `Date:`, `**Last Updated**:`, `**Date**:`
- preferred write format for new research:
  `Last Updated: YYYY-MM-DD` or ISO datetime
- require 2+ keyword/topic matches before reuse
- reuse prior gem/tool/community research to narrow or skip repeated
  `ruby-gem-researcher` / `web-researcher` work
- do **not** skip current-code discovery agents like
  `rails-patterns-analyst`, `call-tracer`, or security/schema/job
  specialists just because a prior feature researched something
  similar
- log reuse decisions in `.claude/plans/{slug}/scratchpad.md` under
  `## Decisions` → `### Research Cache Reuse` as
  `REUSED: {filename} -> skipped {agent}`
- after fresh research completes, read each research artifact +
  reused-cache files and synthesize the plan directly

Spawn only what the request needs:

### Common Research Agents

Quick reference. Canonical matrix (selection rules + conditional
specialists like `ruby-runtime-advisor`, `web-researcher`) lives in
`${CLAUDE_SKILL_DIR}/references/planning-workflow.md` § "Agent
Selection Matrix" + "Spawning Strategy".

- `rails-patterns-analyst` - Rails conventions and patterns
- `active-record-schema-designer` - Database schema and AR patterns
- `security-analyzer` - Security implications and Brakeman checks
- `sidekiq-specialist` - Background job design and queue strategy
- `ruby-gem-researcher` - Gem evaluation and alternatives
- `call-tracer` - Code flow analysis and dependency tracing
- `rails-architect` - High-level architecture decisions
- `ruby-runtime-advisor` - Performance, memory, hot paths
- `web-researcher` - Unfamiliar libraries / community patterns

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
2. **Enqueue Timing**: commit-safe enqueueing for the active ORM
3. **Error Handling**: What happens when things fail?
4. **Idempotency**: Can this operation run multiple times safely?
5. **Rollback Strategy**: How to undo if something goes wrong?

## Iron Laws

1. Never auto-start `/rb:work` after writing the plan.
2. Prefer the existing stack before adding a gem.
3. Every review finding must become a task or an explicit defer decision.
4. Record transaction boundaries, commit-safe enqueue behavior, package ownership, and verification strategy in the plan.
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
- [ ] Sidekiq jobs use the active ORM's commit-safe hook, not `after_save` or inline before commit
- [ ] N+1 queries prevented with `includes` or `preload`
- [ ] Money uses `decimal`, not `float`
- [ ] No sensitive data in logs
- [ ] JSON arguments for Sidekiq (not symbols, no Ruby objects)

### Recovery Strategies by Failure Type

| Failure Type | Strategy | Implementation |
|--------------|----------|----------------|
| DB Rollback | Transaction rescue | Use the ORM-specific rollback exception (`ActiveRecord::Rollback` / `Sequel::Rollback`) |
| Job Fail | Retry with backoff | `sidekiq_options retry: 5` |
| External API | Circuit breaker | `circuitbox` or custom |
| Validation | Early return | Guard clauses, service objects |
| Timeout | Async fallback | Background job, notification |

## Verification Checklist to Include in Plans

- `bundle exec rails zeitwerk:check` if Rails is present
- formatter/linter if configured (`standardrb` or `rubocop`); use Lefthook only when its config covers lint + security/static-analysis checks
- targeted specs or tests for changed behavior
- `bundle exec brakeman` if present for security-sensitive work
- optional final diff-scoped review: `eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref)"` then `bundle exec pronto run -c "$(git merge-base HEAD "$BASE_REF")"`
- `bundle exec rspec` or `bin/rails test` - full test suite
- Migration safety check (for production deployments)

## Compound Documentation Lookup

Before deeper topic research, check the compound knowledge base for similar
solved problems, known risks, and prevention ideas:

1. Search `.claude/solutions/` for relevant symptoms, components, and tags
2. Reuse only concrete prior fixes or prevention guidance that clearly match
3. Treat solution docs as evidence to surface, not as a reason to skip current
   codebase discovery

When you need pattern reminders while reading those solutions, check these
references:

1. `compound-docs` - KB conventions, schema, and search expectations
2. `ruby-idioms` - Ruby 3.4+ features, `it` keyword, pattern matching
3. `rails-idioms` - Rails 8 patterns, Solid Queue, Thruster
4. `active-record-patterns` - Transactions, N+1 prevention, enums
5. `sidekiq` - Job design, retries, enqueue-after-commit
6. `security` - Brakeman, SQL injection, XSS prevention
7. `testing` - RSpec/Minitest patterns, factories, VCR

## Main-Session Fanout

Specialists are leaf workers: research, write artifact, return summary.

1. Create plan namespace (if not pre-bound) + scratchpad.
2. Check compound docs + research cache. Skip duplicates.
3. Select research topics per matrix in
   `${CLAUDE_SKILL_DIR}/references/planning-workflow.md`. Topic slug
   becomes the manifest entry key + research filename stem.
4. Run
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run --skill=rb:plan
   --slug="$PLAN_SLUG" --agents=<csv-of-topic-slugs>`. No
   `--base-ref` (TTL-only staleness). Captures stdout as `$MANIFEST`.
5. Run
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-respawn "$MANIFEST"`.
6. Patch each entry `status: in-flight` via stdin `patch`.
7. Spawn all agents in ONE parallel block. Read paths via
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update spawn-paths "$MANIFEST"`.
   Pass absolute path verbatim in spawn prompt.
8. Wait for all agents to complete.
9. Apply Artifact Recovery (see below). Patch each entry's recovery
   `status` into the manifest.
10. Read each verified artifact + any reused cached files logged in
    scratchpad.md `## Decisions` → `### Research Cache Reuse`.
11. Read consolidated path via
    `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update field "$MANIFEST" consolidated_path`.
    Synthesize `plan.md` at that path.
12. Patch manifest `status: complete`.

## Worker Briefing

Every research Agent() call must:

- use the absolute artifact path passed in the spawn prompt verbatim
- return a ≤500-word summary in Agent return text
- run in parallel via multiple Agent calls in one response (do NOT
  use `run_in_background: true`)
- be scoped to specific files/patterns/questions
- NEVER call Agent() — leaf agents

## Artifact Path Rules

- Helper computes absolute paths from `--skill=rb:plan` + `--slug` +
  `--agents`. Path convention: `.claude/plans/{plan-slug}/research/{topic-slug}.md`
  (research files keyed by topic slug, no datesuffix — research is
  iterative across days; `prepare-respawn` rotates prior files to
  `.stale-<ts>.md` siblings).
- Skill body reads paths via `manifest-update spawn-paths "$MANIFEST"`.
- Pass each path verbatim in the spawn prompt.
- Agents use the exact path received. No filename invention.

## Artifact Recovery

For each manifest entry:

1. **CHECK pause signature first** per
   `${CLAUDE_PLUGIN_ROOT}/references/agent-resume.md`. If matched,
   apply that protocol (resume via `SendMessage` if available, else
   mark `stub-no-output`). The state machine below applies ONLY after
   the resume attempt resolves or is skipped.

2. **STAT the expected path.** Apply the state machine:

- Exists, `size_bytes >= 1000` → trust. Do NOT overwrite.
- Exists, `size_bytes < 1000`, return text substantially larger AND
  parses as findings → replace stub (`stub-replaced`).
- Exists, `size_bytes < 1000`, return text empty/unusable → keep
  stub, treat as coverage gap (`stub-no-output`).
- Missing, return text usable → extract from return text and write.
- Missing, return text empty/unusable → write a stub with heading
  `# {topic-slug} — recovery stub` and body `Run produced no
  artifact and no usable return text. Research coverage gap.`

NEVER copy or symlink prior-run artifacts to the current-run path.
Decide from filesystem; ignore Agent return-text denial claims.
Never re-spawn.

For selection matrix, briefing templates, and routing hints, see
`${CLAUDE_SKILL_DIR}/references/planning-workflow.md`.

For manifest schema + helper subcommands, see
`${CLAUDE_PLUGIN_ROOT}/references/run-manifest.md`.

For canonical plan.md template, see
`${CLAUDE_SKILL_DIR}/references/planning-workflow.md` § "Plan Template".

## Output

Write the plan to the path read via
`${CLAUDE_PLUGIN_ROOT}/bin/manifest-update field "$MANIFEST" consolidated_path`
(resolves to `.claude/plans/{plan-slug}/plan.md` per skill convention).

Create the planning namespace at the start of planning, not only at
plan-write time:

- `.claude/plans/{slug}/research/`
- `.claude/plans/{slug}/summaries/`
- `.claude/plans/{slug}/scratchpad.md`

Use the scratchpad to capture clarification answers, infrastructure
discoveries, and research-cache reuse decisions before `plan.md`
exists. Use the canonical structure from
`${CLAUDE_SKILL_DIR}/references/scratchpad-template.md`:

- `## Decisions` → `### Clarifications`
  - clarification answers and confirmed constraints
- `## Decisions` → `### Research Cache Reuse`
  - `REUSED:` entries for skipped duplicate research
- `## Decisions` → `### Infrastructure`
  - reusable project-setup discoveries
- `## Hypotheses`
  - ideas still being tested
- `## Open Questions`
  - unresolved issues that still block the plan

**After creating the plan, conditionally set the active plan marker:**

If `.claude/ACTIVE_PLAN` already exists and resolves to the current
plan namespace (set by `/rb:full` pre-bind), skip the marker write —
it is already correct. Otherwise (standalone `/rb:plan` invocation),
run `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/active-plan-marker.sh set .claude/plans/{slug}`.

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

## Trust States

When `--existing` references a research sidecar, read the sidecar's
`trust_state` (see
`${CLAUDE_PLUGIN_ROOT}/references/output-verification/trust-states.md`):

- `conflicted`: halt; surface the `conflicts[]` list; ask the user to
  resolve before planning proceeds.
- `missing`: warn that provenance is missing; suggest `/rb:research`
  to strengthen evidence before planning.
- `weak`: warn that evidence is weak; suggest `/rb:research`.
- `clean`: proceed silently.
