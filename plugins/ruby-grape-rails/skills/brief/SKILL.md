---
name: rb:brief
description: "Walking through a Ruby/Rails/Grape plan, diff, or review in a concise summary. Triggers: \"explain plan\", \"summarize review\", \"walk me through\"."
argument-hint: "[plan|diff|review path]"
effort: low
---
# Brief the Work

Read the supplied artifact, then explain what matters in a concise summary.

## Purpose

Briefs provide high-signal explanations for busy developers. After planning, working, or reviewing, use `/rb:brief` to understand:

- What's happening
- What matters most
- What to do next

## Brief Process

```
START ──▶ READ ARTIFACT(S) ──▶ EXTRACT SIGNAL ──▶ SYNTHESIZE
                                                │
                                                ▼
                                         STRUCTURE BRIEF
                                                │
                                                ▼
                                              OUTPUT
```

## Brief Structure

### 1. One-Line Summary

The goal in 10-15 words.

### 2. The Moving Parts (3-5 bullets)

What changed or will change:

- Files modified/created
- New components
- Dependencies added
- Configuration changes

### 3. Risk Areas

What could go wrong:

- Breaking changes
- Security implications
- Performance concerns
- Deployment risks

### 4. Next Action

What to do now:

- Start implementation
- Address review findings
- Run specific commands
- Make decisions

## Brief by Artifact Type

### Briefing a Plan

**Read**: `plan.md`

**Extract**:

- Goal from overview
- Phases and task count
- Risk areas from risk table
- Recommended next step

**Format**:

```
## Plan Brief: {Feature Name}

**Goal**: {one line}

**Scope**: {N} tasks across {N} phases
- Phase 1: {summary}
- Phase 2: {summary}
...

**Key Risks**:
- {risk} ({severity})
- {risk} ({severity})

**Next Step**: {action}
```

### Briefing Work Results

**Read**: `plan.md` (updated), changed files

**Extract**:

- What was completed
- What was blocked
- Files that changed
- Verification results

**Format**:

```
## Work Brief: {Feature Name}

**Completed**: {N}/{N} tasks

**Changes**:
- Created: {files}
- Modified: {files}
- Deleted: {files}

**Blockers**: {N}
- {blocker description}

**Verification**: {status}
- Tests: {pass/fail}
- Linter: {clean/issues}

**Next Step**: {action}
```

### Briefing Review Findings

**Read**: Review files in `reviews/`

**Extract**:

- Blocker count (new findings only)
- Warning count
- Suggestion count
- Canonical verdict (PASS / PASS WITH WARNINGS / REQUIRES CHANGES / BLOCKED)
- Most severe finding

**Format** (`Blocker[s] / Warning[s] / Suggestion[s]` count-aware:
singular when N == 1, plural otherwise including 0):

```
## Review Brief: {Feature Name}

**Summary**: {N} Blocker[s], {N} Warning[s], {N} Suggestion[s]

**Blockers**:
1. {description} ({file}:{line})
2. ...

**Top Warnings**:
1. {description}
2. ...

**Verdict**: PASS | PASS WITH WARNINGS | REQUIRES CHANGES | BLOCKED

**Next Step**: {action}
```

## Brief Laws

1. **Be concise** - 30 seconds to read
2. **Be specific** - Cite files, line numbers
3. **Be actionable** - Clear next step
4. **Prioritize** - Blockers first, then Warnings, then Suggestions (per review bucket vocabulary)
5. **Contextualize** - Why it matters

## What to Skip

Don't include in briefs:

- Implementation details
- Full code snippets
- Obvious information
- Pre-existing issues
- Formatting/style issues (unless egregious)

## Brief Length Guidelines

| Section | Length |
|---------|--------|
| Summary | 1 line |
| Moving parts | 3-5 bullets |
| Risk areas | 2-4 items |
| Next action | 1 clear step |
| Total | < 30 lines |

## Example Briefs

### Plan Brief Example

```
## Plan Brief: User Authentication

**Goal**: Add Devise-free authentication to the API

**Scope**: 12 tasks across 3 phases
- Phase 1: Database & models (4 tasks)
- Phase 2: Controllers & sessions (5 tasks)
- Phase 3: Security & verification (3 tasks)

**Key Risks**:
- Session storage (HIGH) - need Redis config
- Password hashing (Blocker) - use bcrypt, not MD5

**Next Step**: Run `/rb:work .claude/plans/user-auth/plan.md`
```

### Review Brief Example

```
## Review Brief: Payment Processing

**Summary**: 3 Blockers, 2 Warnings, 2 Suggestions

**Blockers**:
1. Float used for money calculation (app/models/order.rb:45)
   - Must use Decimal to prevent rounding errors (Iron Law 1)
2. N+1 query in checkout flow (app/controllers/checkout_controller.rb:23)
   - Use `.includes()` / `.preload()` (Iron Law 3)
3. Missing authorization check in `PaymentsController#charge` (Iron Law 13)

**Top Warnings** (non-Iron-Law):
1. No rate limiting on payment endpoint
2. Missing test for refund edge case

**Verdict**: BLOCKED

**Next Step**: Run `/rb:triage` to prioritize fixes
```

## When to Brief

Brief after:

- `/rb:plan` - to understand the plan
- `/rb:work` - to see what was done
- `/rb:review` - to understand findings
- Long sessions - to recap progress

Don't brief:

- During active work (wait for checkpoint)
- When user already understands
- For trivial changes (< 5 lines)

## Brief vs Review

- **Brief**: Summary for the user, actionable
- **Review**: Detailed analysis, findings only

Briefs synthesize; reviews analyze.

## Output

Present the brief directly to the user:

- No file output needed
- Format with markdown
- Include clear next step

## References

| Need | Reference |
|---|---|
| pre-work + post-work section templates with rules per artifact type | `${CLAUDE_SKILL_DIR}/references/briefing-guide.md` |
| when to suggest visual-explainer third-party skill for HTML diagram output | `${CLAUDE_SKILL_DIR}/references/visual-explainer.md` |
