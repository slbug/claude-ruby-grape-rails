---
name: rb:review
description: "Use when you need code review of changed files with parallel specialist agents for correctness, security, testing, Active Record, Grape, and Sidekiq boundaries. Use after implementation before commit or PR."
when_to_use: "Triggers: \"review my changes\", \"code review\", \"review before commit\", \"check this PR\", \"review for security\". Does NOT handle: fixing code, full project audit, planning, verification/test runs."
argument-hint: "[test|security|sidekiq|deploy|iron-laws|all]"
effort: xhigh
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

## Collecting Changed Files

Resolve the base ref before spawning reviewers:

```bash
eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref)"
MERGE_BASE=$(git merge-base HEAD "$BASE_REF")
git diff --name-only --diff-filter=ACMR "$MERGE_BASE"...HEAD
```

Pass the resulting file list when dispatching `parallel-reviewer` so all
sub-reviewers scope to branch changes only.

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

## Complexity Classification

Classify the review before spawning agents. File count determines base tier;
critical-path files force escalation regardless of count.

| Tier | Files Changed | Depth | Agents |
|------|--------------|-------|--------|
| **Simple** | 1-3 | Core reviewers only, concise output | 4 |
| **Medium** | 4-10 | Core + conditional by file type | 4-8 |
| **Complex** | 11+ | All relevant reviewers, detailed output | 8-11 |

**Auto-escalate to Complex** when any changed file matches:

- `**/auth/**`, `**/authentication/**`, `**/authorization/**`
- `**/payment/**`, `**/billing/**`, `**/checkout/**`
- `db/migrate/**`
- `config/routes*`, `config/initializers/devise*`
- `**/middleware/**`

Log the classification in the consolidated review header:
`**Complexity**: Simple (2 files) | Medium (7 files) | Complex (15 files, escalated: db/migrate)`

## Default Review Tracks

Based on complexity tier and what changed, spawn appropriate reviewers:

### Core Reviewers (Always — all tiers)

- `ruby-reviewer` - Ruby idioms, syntax, correctness
- `security-analyzer` - Security vulnerabilities
- `testing-reviewer` - Test coverage and quality
- `verification-runner` - Automated checks pass

### Conditional Reviewers (Medium + Complex tiers)

- `iron-law-judge` - When diff is risky or touches critical paths
- `sidekiq-specialist` - When workers or jobs changed
- `deployment-validator` - When container or deploy config changed
- `rails-architect` - When service layer, Grape APIs, or architecture changed
- `ruby-runtime-advisor` - When performance, memory, or hot paths changed
- `data-integrity-reviewer` - When models, constraints, or transactions changed
- `migration-safety-reviewer` - When migrations add columns or modify tables

## Iron Laws

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
Use `output-verifier` only when the review depends on external evidence,
versioned sources, or claims that need explicit verification, for example:

- "Rails 8.1 behavior changed here"
- "Sidekiq best practices require this pattern"
- "This gem feature is unsupported in the current version"

If the finding is already proven directly by changed code, line references in the
review itself are enough and no provenance sidecar is needed.

When used:

1. write the draft consolidated review
2. run `output-verifier` against the draft
3. save the result to `.claude/reviews/{review-slug}.provenance.md`
4. remove or soften unsupported external claims before presenting the final review

Use the shared provenance contract:

- `${CLAUDE_PLUGIN_ROOT}/references/output-verification/provenance-template.md`

Detailed reviewer focus areas, file-type checklists, and common Ruby
anti-patterns live in
`${CLAUDE_SKILL_DIR}/references/review-playbook.md`.

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

## Confidence Levels

Every finding MUST include a confidence label. This tells the user which
findings are backed by evidence vs. pattern-based hunches.

| Level | Meaning | Example |
|-------|---------|---------|
| **HIGH** | Direct code evidence — specific line, test failure, static analysis finding | "Line 42: `params[:id]` interpolated into SQL string" |
| **MEDIUM** | Pattern match — known anti-pattern or convention violation, no direct proof of bug | "Service object bypasses transaction boundary (common data-loss pattern)" |
| **LOW** | Subjective — style preference, naming opinion, architecture suggestion | "Consider extracting this into a form object" |

When consolidating findings from multiple agents, keep the highest confidence
level among duplicates. Sort findings by confidence (HIGH first) within each
severity level.

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

## Integration with Workflow

Review happens after `/rb:work` and before commit:

```

/rb:plan ──▶ /rb:work ──▶ /rb:review ──▶ /rb:triage (if issues)
                                              │
                                              ▼
                                         COMMIT/PR

```

Reviews can also be triggered standalone for existing code audits.

## Trust States

When a finding cites a sidecar, read the sidecar's `trust_state` (see
`${CLAUDE_PLUGIN_ROOT}/references/output-verification/trust-states.md`):

- `conflicted`: escalate severity by one level.
- `missing`: tag the finding `[unverified]`; do not gate merge.
- `weak`: keep severity; add a provenance note.
- `clean`: proceed silently.
