# Review Playbook

Use this reference when `/rb:review` needs deeper reviewer focus notes or
file-type-specific checklists without bloating the main routing surface.

## Reviewer Focus Areas

### `ruby-reviewer`

- Ruby correctness, idioms, readability
- `it` keyword opportunities for Ruby 3.4+
- pattern matching, extraction, naming, and control-flow clarity

### `security-analyzer`

- SQL injection vectors
- XSS in views and serializers
- mass assignment, auth bypasses, authorization holes, secrets exposure

### `testing-reviewer`

- missing cases, fragile tests, readability, coverage gaps, stub misuse

### `iron-law-judge`

- transaction safety
- commit-safe enqueue discipline for the active ORM
- N+1 prevention
- decimal-for-money rules
- safe HTML rendering
- JSON-safe Sidekiq arguments

### `sidekiq-specialist`

- idempotency
- retry safety
- argument serialization
- commit-safe enqueueing
- error handling and queue configuration

### `rails-architect`

- service-layer and Grape API boundaries
- cross-context coupling
- architectural consistency

### `ruby-runtime-advisor`

- N+1 queries
- missing indexes
- memory bloat
- algorithmic complexity
- caching opportunities

### `data-integrity-reviewer`

- foreign key and uniqueness constraints
- transaction boundaries
- validation gaps
- rollback safety

### `migration-safety-reviewer`

- large-table defaults
- missing NOT NULL constraints
- missing foreign-key indexes
- irreversible migrations
- data migration mixed into schema migrations

## File-Type Checklists

### Ruby Files

- [ ] `ruby -c` passes
- [ ] formatter is clean (`standardrb` or `rubocop`)
- [ ] no bare `rescue`
- [ ] names and control flow stay readable
- [ ] duplication is avoided

### Rails Controllers

- [ ] strong parameters exist
- [ ] authn/authz is explicit
- [ ] service objects handle complex work
- [ ] redirects/renders are explicit
- [ ] transaction boundaries are deliberate

### Active Record / Sequel Models

- [ ] validations are present and tested
- [ ] associations use correct dependent behavior
- [ ] callbacks are necessary and safe
- [ ] package ORM conventions match the owning code
- [ ] indexes exist for hot queries and foreign keys

### Sidekiq Jobs

- [ ] includes `Sidekiq::Job`
- [ ] arguments are JSON-safe
- [ ] implementation is idempotent
- [ ] enqueue-after-commit semantics are correct
- [ ] retry/dead-letter behavior is intentional

### Grape APIs

- [ ] params are typed
- [ ] auth middleware is applied
- [ ] error handling is present
- [ ] serialization/content-type behavior is correct
- [ ] docs stay current

### Tests

- [ ] tests assert behavior, not internals
- [ ] setup is minimal and legible
- [ ] edge cases are covered
- [ ] names describe the behavior under test

### Migrations

- [ ] migration framework is identified first
- [ ] migration is reversible
- [ ] foreign keys are indexed
- [ ] null constraints and defaults are safe
- [ ] change is production-safe for large tables

## Common Ruby Anti-Patterns

| Anti-pattern | Issue | Better approach |
|--------------|-------|-----------------|
| `rescue Exception => e` | Catches too broadly, including interrupts and exits | `rescue SpecificError => e` or a deliberate `rescue StandardError => e` boundary |
| `!user.nil?` | Double negative | `user.present?` |
| `if condition; return x; end` | Unnecessary control flow | `return x if condition` |
| `ary.map { |x| x.name }` | Redundant block param | `ary.map(&:name)` or `ary.map { it.name }` |
| `user && user.name` | Manual nil-guard | `user&.name` |
| `DateTime.now` | Wrong default in Rails apps | `Time.current` or `Time.now` |

## Diff Collection

`/rb:review` skill body uses these commands to resolve base ref and
collect changed file list:

```bash
eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref)"
MERGE_BASE=$(git merge-base HEAD "$BASE_REF")
CHANGED_FILES=$(git diff --name-only --diff-filter=ACMR "$MERGE_BASE"...HEAD)
```

Pass `$CHANGED_FILES` to every spawned reviewer Agent() call. Reviewers
scope all reads/grep/analysis to this file list — they must NEVER scan
unchanged files.

## Worker Briefing Template

Every reviewer `Agent(subagent_type:)` call from `/rb:review` skill body
includes this prompt template:

```text
Task: review {file list} for {scope}.

Scope: $CHANGED_FILES (from main session diff collection)
Base ref: $BASE_REF (from resolve-base-ref)
Artifact path: .claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md

Required output:
1. Write artifact to the exact path above
   (always — even if findings are empty, write PASS with files reviewed)
2. Return summary in Agent return text (used as artifact-recovery fallback)

Findings format:
- file:line — Title
- Severity: Critical | Warning | Info
- Confidence: HIGH | MEDIUM | LOW
- Description, current code, suggested code, why it matters

Stop after returning. Do NOT call Agent() — this is a leaf review.
```

## Artifact Recovery

After all spawned reviewers complete, `/rb:review` skill body MUST verify
each expected current-run artifact path exists:

1. For every reviewer in the spawn manifest, check
   `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md` exists.
2. If missing, extract findings from the Agent return text and write
   the artifact yourself from main session.
3. Do NOT re-spawn the reviewer — the work is done; only the file write
   failed (known CC platform behavior with Write permissions in
   spawned agents).
4. If the return text is empty/unusable, note the gap in the
   consolidated review and continue.

Compression must run only on the verified manifest (post-recovery).

## Consolidated Review Format

Write the synthesized review to `.claude/reviews/{review-slug}.md`:

```markdown
# Review: {track}
**Date**: {timestamp}
**Complexity**: {Simple|Medium|Complex} ({N} files{, escalated: reason})
**Files Changed**: {list}

## Summary
- Critical: {N}
- Warnings: {N}
- Info: {N}
- Clean: {Y/N}

## Critical Issues

### 1. {Issue Title}
**File**: `path/to/file.rb:{line}`
**Severity**: Critical | **Confidence**: HIGH
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

**Severity**: Warning | **Confidence**: MEDIUM

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
