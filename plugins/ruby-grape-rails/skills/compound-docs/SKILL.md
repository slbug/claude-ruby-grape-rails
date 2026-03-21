---
name: compound-docs
description: Schema for documenting solved Ruby/Rails/Grape problems as reusable solution notes.
user-invocable: false
---

# Compound Docs

Each solution note should capture:

- symptom
- root cause
- fix
- prevention rule
- related commands or files

## Directory Structure

Solution documents are stored in `.claude/solutions/` with category subdirectories:

```
.claude/
└── solutions/
    ├── active-record-issues/
    ├── build-issues/
    ├── deployment-issues/
    ├── grapе-api-issues/
    ├── hotwire-issues/
    ├── performance-issues/
    ├── rails-issues/
    ├── ruby-issues/
    ├── security-issues/
    ├── service-issues/
    ├── sidekiq-issues/
    ├── testing-issues/
    └── workers-issues/
```

## Iron Laws for Compound Docs

1. **ALWAYS search solutions before investigating** - Check `.claude/solutions/` for similar issues
2. **VALIDATE frontmatter against schema** - Ensure required fields are present and correct
3. **USE the resolution template** - Start from the standard format for consistency
4. **LINK related solutions** - Connect symptoms, prerequisites, and alternatives

## Solution File Format

All solution documents use YAML frontmatter followed by markdown content. See:

- `skills/compound-docs/references/schema.md` for the field definitions
- `skills/compound-docs/references/resolution-template.md` for the full template

## Finding Solutions

Search for existing solutions using:

```bash
# Find by symptom
grep -r "symptom:" .claude/solutions/ | grep "N+1 query"

# Find by category
ls .claude/solutions/rails-issues/

# Find by tag
grep -r "tags:" .claude/solutions/ | grep "preload"
```

## Integration with Other Skills

Compound documents are consumed by:

- `/rb:plan` - Reference existing solutions during planning
- `/rb:work` - Apply proven patterns from solutions
- `/rb:review` - Verify fixes against documented solutions
- `/rb:learn` - Extract patterns to update skills and Iron Laws

## Maintenance

- Keep solution documents focused and actionable
- Update the index when adding new solutions
- Link related solutions to build knowledge chains
- Archive solutions older than 2 years if no longer relevant
