# Interview Techniques

## Codebase Scan Patterns

Run these scans between questions based on what the user mentions:

| User mentions | Grep/Glob pattern | What to look for |
|---|---|---|
| authentication, auth, login | `**/*auth*.rb`, `**/*session*.rb` | Devise, Warden, has_secure_password, custom auth |
| real-time, live, WebSocket | `**/*channel*.rb`, `**/*_component.rb` | ActionCable, Turbo Streams, ViewComponent |
| background, jobs, async | `**/*job*.rb`, `**/*worker*.rb` | Sidekiq, Solid Queue, ActiveJob config |
| upload, files, images | `**/*upload*`, `**/*attachment*` | ActiveStorage, Shrine, CarrierWave |
| email, notification | `**/*mailer*.rb`, `**/*notification*` | ActionMailer, letter_opener config |
| API, endpoint, REST, GraphQL | `**/*controller*.rb`, `**/*_api.rb`, `app/apis/**` | Grape endpoints, Rails API, GraphQL |
| payment, billing, subscription | `**/*payment*`, `**/*billing*` | Stripe, decimal fields, webhook handlers |
| search, filter, query | `**/*search*`, `**/*filter*` | Ransack, pg_search, Elasticsearch |
| admin, dashboard | `**/*admin*`, `**/admin/**` | ActiveAdmin, Administrate, custom admin |
| database, schema, migration | `db/migrate/*.rb`, `**/*model*.rb` | Recent migrations, schema patterns |
| test, testing, coverage | `spec/**/*_spec.rb`, `test/**/*_test.rb` | Test patterns, factories, fixtures |
| deploy, production, CI | `config/deploy*`, `Dockerfile`, `fly.toml` | Deploy config, Kamal, CI workflows |
| cache, Redis, performance | `**/*cache*`, `config/initializers/*redis*` | Rails.cache config, Redis namespaces |
| Grape, API versioning | `app/api/**/*.rb`, `app/apis/**/*.rb` | Grape::API classes, version modules |
| Packwerk, packages, boundaries | `packwerk.yml`, `packs/*/package.yml` | Package definitions, dependencies |

## Scan Depth Rules

- **First mention of a topic**: Medium scan — Grep + Read 1-2 key files (~5s)
- **Follow-up on same topic**: Light scan — Grep only, check for new patterns (~2s)
- **User asks "what do I have?"**: Full scan — Glob + Grep + Read multiple files (~10s)
- **Never**: spawn an agent for scanning during interview (too slow, breaks flow)

## Signal Detection

### Vague Answer Signals

- "Something like...", "maybe", "I'm not sure", "kind of"
- Very short answers (< 20 words) to open-ended questions
- Deflection: "whatever you think is best", "the usual way"

**Response**: Probe deeper on the SAME dimension with a more specific question.
Offer concrete options: "Would it be more like A or B?"

### Expertise Signals

- Uses framework-specific terms correctly (ActiveRecord, Grape::API, Sidekiq::Worker)
- References specific modules, files, or patterns
- Provides implementation-level detail unprompted

**Response**: Skip basic questions. Ask at the implementation level: "Should
this use `ActiveJob` or a direct `Sidekiq::Worker` for the background fetch?"

### Scope Creep Signals

- Answer mentions 3+ new features or systems not in original topic
- "And also we could...", "while we're at it..."
- Answer would require touching 5+ contexts

**Response**: Acknowledge, then gently narrow: "Those are great ideas. For this
brainstorm, should we focus on {core feature} first, and note {extras} as
future work?"

### Saturation Signals

- 2 consecutive answers add no new coverage (same dimensions, same scores)
- User answers become shorter or repetitive
- All 6 dimensions at >= 1 (partial coverage everywhere)

**Response**: Present Decision Point.

## interview.md Output Format

```markdown
# Brainstorm: {Topic}

**Status**: COMPLETE | IN_PROGRESS
**Date**: {YYYY-MM-DD}
**Coverage**: What ██░░ | Why ████ | Where ███░ | How ██░░ | Edge ░░░░ | Scope ████
**Score**: {N}/12

## Summary

{3-5 sentence synthesis of what was gathered. Written as requirements, not as
a transcript recap. Focus on WHAT the user wants, WHY, and key constraints.}

## Coverage Details

### What ({score}/2)

{Synthesized understanding of the desired behavior}

### Why ({score}/2)

{Problem statement and user need}

### Where ({score}/2)

{Affected modules, contexts, routes. Include file paths found during scans.}

### How ({score}/2)

{Technical approach preferences, constraints, patterns to follow}

### Edge Cases ({score}/2)

{Error handling, scale, permissions, failure modes}

### Scope ({score}/2)

{What's in, what's explicitly out, v1 vs future}

## Codebase Context

{Ruby stack detection results: ORM, API style, job framework, testing framework,
formatter, monolith layout. Plus key findings from between-question scans —
existing patterns, relevant modules, current architecture.}

## Research Findings

{Populated after Research phase. Empty if user chose plan/store without research.}

### Approaches Found

#### Approach 1: {name}
- **Thesis**: {why it works for this codebase}
- **Antithesis**: {why it might not}
- **Key files**: {existing files that would change}

#### Approach 2: {name}
...

## Open Questions

- {Anything still unclear or needing investigation}
- {Topics where research was suggested but not done}

## Transcript

### Q1: {question}
**Context scan**: {what Grep/Glob found before this question}
**Answer**: {verbatim user response}
**Coverage update**: What 0→1, Why 0→1

### Q2: {question}
**Context scan**: {scan results}
**Answer**: {verbatim}
**Coverage update**: Where 0→2

...
```

**Format notes:**

- **Summary** is what `/rb:plan` reads first — must be self-contained
- **Coverage Details** replace `/rb:plan`'s clarification questions
- **Codebase Context** reduces duplicate work for `/rb:plan`'s research agents
- **Transcript** at the bottom for audit trail — not consumed by `/rb:plan`
- **Status: COMPLETE** means all dimensions >= 1 and total >= 8
- **Status: IN_PROGRESS** means user chose "Store & exit" before sufficient coverage
