---
name: rb:review
description: Review code with parallel specialist agents covering Ruby correctness, security, testing, Active Record, Rails/Grape boundaries, and Sidekiq behavior. Use after implementation before commit or PR.
argument-hint: "[test|security|sidekiq|deploy|iron-laws|all]"
disable-model-invocation: true
effort: high
---
# Review Ruby/Rails/Grape Code

Review changed code by spawning specialist agents. Review is **read-only** - never fix during review.

## Review Philosophy

Reviews catch issues before they reach production. Each specialist focuses on their domain:

- **Correctness**: Does it work? Handle edge cases?
- **Security**: Are there vulnerabilities? Input validation?
- **Maintainability**: Can others understand and modify this?
- **Performance**: Will it scale? Any N+1s?
- **Style**: Does it follow conventions?

## Review State Machine

```
START ──▶ COLLECT CHANGES ──▶ SELECT AGENTS ──▶ SPAWN PARALLEL
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  WAIT FOR ALL   │
                                    │  COMPLETION     │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  SYNTHESIZE     │
                                    │  FINDINGS       │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
              [CLEAN]                  [WARNINGS]               [CRITICAL]
                    │                        │                        │
                    ▼                        ▼                        ▼
           Suggest compound          Suggest triage          Require triage
           or learn                   or plan                 or plan
```

## Default Review Tracks

Based on what changed, spawn appropriate reviewers:

### Core Reviewers (Always)

- `ruby-reviewer` - Ruby idioms, syntax, correctness
- `security-analyzer` - Security vulnerabilities
- `testing-reviewer` - Test coverage and quality
- `verification-runner` - Automated checks pass

### Conditional Reviewers

- `iron-law-judge` - When diff is risky or touches critical paths
- `sidekiq-specialist` - When workers or jobs changed
- `deployment-validator` - When container or deploy config changed
- `rails-architect` - When service layer, Grape APIs, or architecture changed
- `ruby-runtime-advisor` - When performance, memory, or hot paths changed
- `data-integrity-reviewer` - When models, constraints, or transactions changed
- `migration-safety-reviewer` - When migrations add columns or modify tables

## Review Laws

1. **Never fix code inside `/rb:review`** - findings only, fixes later
2. **Focus on changed lines first** - label unchanged issues as pre-existing
3. **Deduplicate overlapping findings** - merge similar issues from different agents
4. **Keep noise low** - prefer findings a senior Ruby reviewer would care about
5. **Be specific** - cite line numbers, provide examples
6. **Prioritize** - mark as critical/warning/info
7. **Contextualize** - explain why it matters, not just what's wrong
8. **Identify package + ORM first** - do not apply flat Rails / Active Record advice to Sequel or modular packages

## Provenance Guard

Most review findings are code-local and can be justified directly from the diff.
Use `output-verifier` only when the review depends on external or versioned
claims, for example:

- "Rails 8.1 behavior changed here"
- "Sidekiq best practices require this pattern"
- "This gem feature is unsupported in the current version"

When used:

1. write the draft consolidated review
2. run `output-verifier` against the draft
3. save the result to `.claude/reviews/{review-slug}.provenance.md`
4. remove or soften unsupported external claims before presenting the final review

## Agent Descriptions

### ruby-reviewer

Focus: Ruby correctness, idioms, readability

- Uses `it` keyword where appropriate (Ruby 3.4+)
- Pattern matching opportunities
- Method extraction candidates
- Variable naming
- Control flow clarity

### security-analyzer

Focus: Security vulnerabilities

- SQL injection vectors
- XSS in views/serializers
- Mass assignment risks
- Authentication bypasses
- Authorization holes
- Secrets exposure

### testing-reviewer

Focus: Test quality and coverage

- Missing test cases
- Fragile tests
- Test readability
- Coverage gaps
- Mock/stub misuse

### iron-law-judge

Focus: Iron Law violations

- Transaction safety
- Commit-safe enqueue discipline for the active ORM
- N+1 query prevention
- Decimal for money
- Safe HTML rendering
- JSON-safe Sidekiq args

### sidekiq-specialist

Focus: Background job correctness

- Idempotency
- Retry safety
- Argument serialization
- Commit-safe enqueueing for the active ORM
- Error handling
- Queue configuration

### rails-architect

Focus: Service layer and API design

- Context boundaries
- Grape API patterns
- Service object design
- Cross-context coupling
- Architectural consistency

### ruby-runtime-advisor

Focus: Performance and runtime issues

- N+1 queries
- Missing indexes
- Memory bloat
- Algorithmic complexity
- Caching opportunities

### data-integrity-reviewer

Focus: Data consistency and constraint enforcement

- Missing foreign key constraints
- Missing uniqueness constraints
- Transaction boundaries
- Validation gaps (model validates but DB doesn't enforce)
- Rollback safety

### migration-safety-reviewer

Focus: Migration safety and schema changes

- Adding columns with defaults on large tables
- Missing NOT NULL constraints
- Missing indexes on foreign keys
- Irreversible migrations
- Data migration in schema migrations

## Review Checklist by File Type

### Ruby Files (.rb)

- [ ] Syntax valid (`ruby -c`)
- [ ] Formatter clean (`standardrb`/`rubocop`)
- [ ] No bare `rescue` clauses
- [ ] Method length reasonable (< 20 lines preferred)
- [ ] Clear variable names
- [ ] No code duplication

### Rails Controllers

- [ ] Strong parameters defined
- [ ] Authentication checked
- [ ] Authorization enforced
- [ ] Service objects for complex logic
- [ ] Transaction boundaries
- [ ] Proper redirects/renders

### Models (Active Record / Sequel)

- [ ] Validations present and tested
- [ ] Associations have correct dependent options
- [ ] Scopes are chainable
- [ ] Callbacks are necessary and safe
- [ ] No business logic in callbacks
- [ ] ORM-specific patterns match the owning package
- [ ] Index hints for queries

### Sidekiq Jobs

- [ ] Includes `Sidekiq::Job`
- [ ] Arguments are JSON-safe
- [ ] Idempotent implementation
- [ ] After_commit hook usage
- [ ] Retry strategy configured
- [ ] Dead letter queue considered

### Grape APIs

- [ ] Params declared with types
- [ ] Error handling present
- [ ] Authentication middleware
- [ ] Content type correct
- [ ] Response serialization
- [ ] Documentation current

### Tests

- [ ] Tests the behavior, not implementation
- [ ] Setup is clear and minimal
- [ ] Assertions are specific
- [ ] Edge cases covered
- [ ] Test names describe behavior
- [ ] No test code duplication

### Migrations

- [ ] Migration framework identified first (Active Record vs Sequel)
- [ ] Reversible (up/down or change)
- [ ] Indexes added for foreign keys
- [ ] Null constraints appropriate
- [ ] No data loss in changes
- [ ] Production-safe (no locking tables long)

## Review Artifact Contract

Every `/rb:review` run produces two artifact layers:

- Per-reviewer artifacts: `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md`
- Consolidated review: `.claude/reviews/{review-slug}.md`
- Optional provenance sidecar when `output-verifier` is used:
  `.claude/reviews/{review-slug}.provenance.md`

Rules:

- Every spawned reviewer MUST leave an artifact, even on a clean pass
- Clean passes still write `PASS`, files reviewed, and why no findings were raised
- Review artifacts never live under `.claude/plans/...`
- If review is part of a plan, reference the consolidated review from the plan or progress log instead of nesting the report inside the plan namespace

## Consolidated Review Format

Write the synthesized review to `.claude/reviews/{review-slug}.md`:

```markdown
# Review: {track}
**Date**: {timestamp}
**Files Changed**: {list}

## Summary
- Critical: {N}
- Warnings: {N}
- Info: {N}
- Clean: {Y/N}

## Critical Issues

### 1. {Issue Title}
**File**: `path/to/file.rb:{line}`
**Severity**: Critical
**Category**: {security/performance/correctness}

{description of issue}

**Current**:
```ruby
{bad code}
```

**Suggested**:

```ruby
{good code}
```

**Why it matters**: {explanation}

## Warnings

### 2. {Issue Title}

...

## Pre-existing Issues (unchanged code)

- {issue} (not introduced by this change)

## Positive Findings

- {what was done well}

```

## Severity Levels

### Critical
Must fix before merge:
- Security vulnerabilities
- Data loss risks
- Production outages
- Iron Law violations in critical paths

### Warning
Should fix before merge:
- Performance issues
- Maintainability problems
- Test coverage gaps
- Potential bugs

### Info
Nice to have:
- Style suggestions
- Refactoring opportunities
- Documentation improvements

## Deduplication Strategy

When multiple agents find the same issue:

1. Merge into single finding
2. Cite all agents who found it
3. Use most specific description
4. Keep highest severity
5. List all affected lines

## Review Output Location

Write artifacts to:

- `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md` for each reviewer
- `.claude/reviews/{review-slug}.md` for the synthesized output

`review-slug` must be filesystem-safe:

- lowercase
- replace `/` and whitespace with `-`
- strip characters outside `[a-z0-9._-]`
- collapse repeated `-`

Use the current branch name only after slugifying it. If the branch name is not meaningful, derive the slug from the reviewed diff or user-supplied target.

## After Review

Based on findings severity:

### Clean Review (0 critical, 0-2 warnings)
- Suggest `/rb:compound` - for knowledge synthesis
- Suggest `/rb:learn` - for pattern extraction
- User can proceed with confidence

### Warning Review (0 critical, 3+ warnings)
- Suggest `/rb:triage` - to prioritize fixes
- Suggest `/rb:plan` - if fixes need planning
- User decides which warnings to address

### Critical Review (1+ critical)
- Require `/rb:triage` - address critical issues first
- Suggest `/rb:plan` - if significant rework needed
- Do not proceed without fixes

## Review Best Practices

1. **Review small chunks** - Large diffs are harder to review well
2. **Review your own code first** - Self-review catches obvious issues
3. **Explain the 'why'** - Teach, don't just correct
4. **Suggest, don't dictate** - Offer options when appropriate
5. **Acknowledge trade-offs** - Some issues have valid reasons
6. **Celebrate good code** - Positive feedback matters too

## Common Ruby Anti-patterns to Catch

| Anti-pattern | Issue | Better Approach |
|--------------|-------|-----------------|
| `rescue => e` | Catches all exceptions | `rescue StandardError => e` |
| `!user.nil?` | Double negative | `user.present?` |
| `if condition; return x; end` | Unnecessary control flow | `return x if condition` |
| `ary.map { |x| x.name }` | Redundant block param | `ary.map(&:name)` or `ary.map { it.name }` (Ruby 3.4) |
| `ary.each do ... end` | Side effects | `ary.each { ... }` for single line |
| `user && user.name` | Safe navigation | `user&.name` |
| `DateTime.now` | Wrong class | `Time.current` (Rails) or `Time.now` |

## Integration with Workflow

Review happens after `/rb:work` and before commit:

```

/rb:plan ──▶ /rb:work ──▶ /rb:review ──▶ /rb:triage (if issues)
                                              │
                                              ▼
                                         COMMIT/PR

```

Reviews can also be triggered standalone for existing code audits.
