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
| `rescue => e` | Catches too broadly | `rescue StandardError => e` |
| `!user.nil?` | Double negative | `user.present?` |
| `if condition; return x; end` | Unnecessary control flow | `return x if condition` |
| `ary.map { |x| x.name }` | Redundant block param | `ary.map(&:name)` or `ary.map { it.name }` |
| `user && user.name` | Manual nil-guard | `user&.name` |
| `DateTime.now` | Wrong default in Rails apps | `Time.current` or `Time.now` |
