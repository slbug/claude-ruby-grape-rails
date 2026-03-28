---
name: rb:compound
description: Capture a solved Ruby/Rails/Grape problem as reusable knowledge for future sessions.
argument-hint: "[path to fix|review|plan]"
effort: low
---
# Compound Knowledge

Capture a solved problem as reusable knowledge. This creates a knowledge base that helps future sessions solve similar problems faster.

## What to Compound

Compound problems that:

- Took significant time to solve (> 30 minutes)
- Involved multiple files or systems
- Required debugging or root cause analysis
- Have reusable patterns or lessons
- Others might encounter

Don't compound:

- Trivial syntax errors
- One-line fixes
- Problems specific to unique project state
- Already well-documented issues

## Compound Process

```
START ──▶ VALIDATE AGAINST SCHEMA ──▶ USE RESOLUTION TEMPLATE ──▶ WRITE DOC
                                               │
                                               ▼
                                        UPDATE INDEX
                                               │
                                               ▼
                                             DONE
```

## Document Structure

Solution documents use YAML frontmatter defined in `../compound-docs/references/schema.md` and follow the template in `../compound-docs/references/resolution-template.md`.

### Required Frontmatter Fields

- `module`: Ruby module or context area (e.g., "Accounts", "Hotwire/Turbo.UserList")
- `date`: Creation date in YYYY-MM-DD format
- `problem_type`: Category of problem (build_error, test_failure, runtime_error, etc.)
- `component`: Affected component area (active_record_model, hotwire_mount, sidekiq_job, etc.)
- `symptoms`: Array of 1-5 observable symptoms (error messages, unexpected behavior)
- `root_cause`: Detailed explanation of WHY this happened
- `severity`: critical, high, medium, or low
- `tags`: Array of up to 8 searchable keywords (lowercase, hyphen-separated)

### Optional Fields

- `ruby_version` / `rails_version`: Specific version pattern X.Y.Z
- `iron_law_number`: Integer (1-21) indicating which Iron Law was violated
- `related_solutions`: Array of file paths to related solutions

## Example Compound Document

```markdown
---
module: "Accounts"
date: "2026-03-22"
problem_type: "runtime_error"
component: "active_record_model"
symptoms:
  - "ActiveRecord::AssociationNotLoaded: association 'posts' not loaded"
  - "N+1 query detected in controller"
root_cause: "missing includes on :posts association"
severity: medium
tags: ["preload", "association", "n-plus-one"]
---

# N+1 Query in Posts Controller

## Symptoms

- ActiveRecord::AssociationNotLoaded: association 'posts' not loaded
- N+1 query detected in controller
- Slow response time when loading user profiles

## Investigation

1. **Hypothesis 1**: Missing database index — Added index, query still slow
2. **Hypothesis 2**: Inefficient Ruby processing — Profiled code, bottleneck was DB
3. **Root cause found**: Missing preload on association

## Root Cause

The controller loads users and then accesses each user's posts association without preloading, causing N+1 query behavior. Each user triggers a separate query to load their posts.

## Solution

```ruby
# BEFORE (problematic)
def index
  @users = User.all
end

# AFTER (fixed)
def index
  @users = User.all.includes(:posts)
end
```

### Files Changed

- `app/controllers/users_controller.rb:15` — Added includes(:posts)
- `spec/controllers/users_controller_spec.rb:20` — Added test for preload

## Prevention

- [ ] Add to Iron Laws? (consider adding "Eager load associations when accessing in loops")
- [x] Add to test patterns? (added controller test)
- [x] Specific guidance: "Always use includes/preload for associations accessed in views or loops"

## Related

- `.claude/solutions/rails-controller-n-plus-one-20260322.md` — Similar issue in different controller
- Iron Law #3: "USE includes/preload for associations — avoids N+1 queries"

```

## Categories

Organize solutions by category for discoverability:

- **ruby** - Ruby language issues
- **rails** - Rails framework issues
- **grape** - Grape API issues
- **sidekiq** - Background job issues
- **security** - Security vulnerabilities
- **perf** - Performance issues
- **ar** - Active Record issues
- **deploy** - Deployment issues

## Compound Index

Maintain `.claude/solutions/index.md`:

```markdown
# Knowledge Index

## Ruby
- `ruby/hash-keys.md`
- `ruby/memoization.md`

## Rails
- `rails/strong-params.md`
- `rails/turbo-streams.md`

## Sidekiq
- `sidekiq/job-not-enqueuing.md`
- `sidekiq/idempotency.md`

## Security
- `security/sql-injection.md`
- `security/mass-assignment.md`
```

## When to Update Index

Update the index when:

- Adding a new solution
- Solutions accumulate (reorganize by category)
- Finding similar existing solutions (link them)

## Cross-referencing

Link related solutions:

- Similar symptoms, different causes
- Prerequisites or follow-ups
- Alternative approaches

Format:

```markdown
## Related Solutions
- `path/to/x.md` - Similar: X, different root cause
- `path/to/y.md` - Prerequisite: Y, setup needed first
```

## Integration with Workflow

Compound after successful resolution:

```
/rb:plan ──▶ /rb:work ──▶ /rb:verify ──▶ /rb:review ──▶ COMPOUND
                                               │
                                               ▼
                                         SOLUTION DOC
```

Or compound during `/rb:learn` when extracting patterns.

## Compound vs Learn

- **Compound**: Capture specific problem/solution
- **Learn**: Extract general patterns and update skills

Use both: Compound first for the instance, Learn to generalize.

## References

- `${CLAUDE_SKILL_DIR}/references/compound-workflow.md` — Detailed capture workflow
- `../compound-docs/SKILL.md` — Knowledge-base conventions and search expectations
- `../compound-docs/references/schema.md` — Solution frontmatter schema
- `../compound-docs/references/resolution-template.md` — Canonical solution template

## Decision Menu

After creating a solution document, consider:

1. **Continue** (default) - Move on to next task
2. **Promote to Iron Law check** - If this represents a foundational pattern that should be an Iron Law
3. **Update skill reference** - If this reveals a gap in existing skill documentation
4. **Update CLAUDE.md** - If this changes how the plugin should behave or document functionality

## Auto-Trigger Phrases

When user says any of the following, suggest `/rb:compound`:

- "that worked"
- "it's fixed"
- "problem solved"
- "the fix was"
- "resolved the issue"
- "thanks, that fixed it"

## Quality Checklist

Good compounds have:

- [ ] Clear symptom description
- [ ] Accurate root cause analysis
- [ ] Copy-pasteable solution
- [ ] Actionable prevention rule
- [ ] Proper categorization
- [ ] Links to related docs
- [ ] Valid YAML frontmatter against schema
- [ ] Follows resolution template format

## File Naming

Use kebab-case, descriptive names:

- `sidekiq-job-not-enqueuing.md` ✓
- `fix.md` ✗
- `issue-123.md` ✗

Filename convention: `{sanitized-symptom}-{module}-{YYYYMMDD}.md`
Example: `association-not-loaded-accounts-20260322.md`
