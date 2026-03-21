# Plan Template Format

## Full Plan Template

```markdown
# Plan: {Feature Name}

**Status**: PENDING
**Created**: {date}
**Detail Level**: {minimal|more|comprehensive}
**Input**: {review path, or "from description"}

## Summary

{What we're building in 2-3 sentences}

## Scope

**In Scope:**

- Item 1
- Item 2

**Out of Scope:**

- Item 1

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library | {name} | {why} |
| Storage | {type} | {why} |

## Data Model

{If database changes needed}

## Module Structure

{If new modules needed}

## System Map (Hotwire/Turbo features with 2+ pages/components only)

{Omit this entire section for non-Hotwire/Turbo or simple features.
Include when the rails-architect produced a breadboard.}

### Places

| ID | Place | Entry Point | Notes |
|----|-------|-------------|-------|
| P1 | {ControllerName} | {route} | {notes} |

### UI Affordances

| ID | Place | Component | Affordance | Type | Wires Out | Returns To |
|----|-------|-----------|------------|------|-----------|------------|
| U1 | P1 | {comp} | {element} | turbo-{*} | {N-id} | {S-id} |

### Code Affordances

| ID | Place | Module | Affordance | Wires Out | Returns To |
|----|-------|--------|------------|-----------|------------|
| N1 | P1 | {Module} | {method} | {targets} | {S-id} |

### Data Stores

| ID | Store | Type | Read By | Written By |
|----|-------|------|---------|------------|
| S1 | {name} | {type} | {U/N ids} | {N ids} |

### Spikes

{List any ⚠️ unknowns from the tables above.}

## Phase 0: Spikes [PENDING] (only if ⚠️ unknowns exist)

- [ ] [P0-T1][direct] Spike: {investigate unknown}
  **Unknown**: {what we don't know}
  **Success criteria**: {what resolves it}
  **Time-box**: 30 minutes max

## Phase 1: {Phase Name} [PENDING]

- [ ] [P1-T1][active record] Create user model and migration
  **Implementation**: Generate with `rails generate model`.
  Add fields: email (string, unique), password_digest (string).
  Add unique index on email.

- [ ] [P1-T2][direct] Configure deps and environment
  **Locations**: Gemfile, config/application.rb
  **Pattern**: Add bcrypt to Gemfile, configure hash rounds.

## Phase 2: {Phase Name} [PENDING]

- [ ] [P2-T1][hotwire] Build registration form with Turbo
  **Implementation**: Create controller with form view.
  Handle form submission with validation errors.
  Redirect to login on success.
  **Locations**: app/controllers/registrations_controller.rb,
  app/views/registrations/new.html.erb

### Parallel: {Group Name}

- [ ] [P2-T2][direct] Task that can run in parallel
- [ ] [P2-T3][direct] Another parallel task

### Sequential

- [ ] [P2-T4][hotwire] Task that depends on above

## Phase N: Verification [PENDING]

- [ ] [PN-T1][test] Unit tests for {model}
- [ ] [PN-T2][test] Integration tests for {feature}
- [ ] [PN-T3][test] Run full verification suite

## Task Agent Annotations

| Annotation | Agent | Use For |
|------------|-------|---------|
| `[active record]` | active-record-schema-designer | Models, migrations, queries |
| `[hotwire]` | rails-architect | Hotwire/Turbo, real-time UI, ActionCable |
| `[sidekiq]` | sidekiq-specialist | Background jobs, workers |
| `[concurrency]` | ruby-runtime-advisor | Threads, fibers, async |
| `[security]` | security-analyzer | Auth, tokens, permissions |
| `[test]` | testing-reviewer | Tests, mocks, factories |
| `[direct]` | (none) | Simple tasks, config |

**Rules:** Primary focus wins. Security always wins for auth tasks.

## Files to Follow as Patterns

Existing files to read first when implementing (reduces cold-start):

- `{path/to/similar_model.rb}` — follow this pattern for {reason}
- `{path/to/existing_test.rb}` — follow this test structure
- `{path/to/component.rb}` — follow this component pattern

## Patterns to Follow

From codebase analysis:

- {Pattern 1}
- {Pattern 2}

## Session Handoff

Key context from planning session for `/rb:work` to use:

- **Discovery**: {key findings, bugs found, gotchas learned}
- **Decisions**: {choices made and why}
- **Warnings**: {things to watch out for during implementation}

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| {potential issue} | {how to handle} |

## Verification Checklist

- [ ] `bundle exec rails zeitwerk:check` passes
- [ ] `bundle exec rubocop` passes (or `bundle exec standardrb`)
- [ ] `bundle exec rspec` passes

```

## Task Granularity

Tasks are logical work units, NOT individual file edits.

**BAD** (too atomic -- one task per file):

```markdown
- [ ] [P3-T3][direct] Replace wait_for_timeout in file_a.rb
- [ ] [P3-T4][direct] Replace wait_for_timeout in file_b.rb
- [ ] [P3-T5][direct] Replace wait_for_timeout in file_c.rb
```

**GOOD** (grouped by pattern with locations and implementation):

```markdown
- [ ] [P3-T2][direct] Replace all hardcoded waits with
  condition-based waits
  **Locations** (71 calls across 14 files):
  - proposal_form_test.rb (15 calls)
  - space_inputs_test.rb (7 calls)
  - (12 more files)
  **Pattern**: Replace `sleep(1)` with:
  - Capybara: `expect(page).to have_selector("css")`
  - Assertion: `expect(page).to have_content("expected")`
  - Async: `expect { some_action }.to eventually eq expected`
```

**Guidelines:**

- 3-8 tasks per phase (not 15+)
- Group by PATTERN, list LOCATIONS within
- Include implementation detail: code examples, before/after
- Sub-locations are indented lists, not separate tasks
- Each task completable in one sitting

**IMPORTANT**: Plan template does NOT auto-start `/rb:work`. The
skill presents the plan and asks the user how to proceed.
