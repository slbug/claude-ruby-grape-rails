# Library Evaluation Template

When `/rb:research --library` or evaluating a Ruby gem,
use this structured template instead of free-form research.

## Workflow

1. Check rubygems.org stats (downloads, recent releases, maintenance)
2. Read GitHub repo (issues, PRs, test quality, deps)
3. Analyze architecture fit with current project
4. Produce ONE structured document (not multiple files)

## Output Template

Write to `.claude/research/{library-name}-evaluation.md`:

```markdown
# Library Evaluation: {name}

Last Updated: 2026-03-25

## Quick Facts

| Metric | Value |
|--------|-------|
| RubyGems.org | {url} |
| Latest version | {version} ({date}) |
| Weekly downloads | {count} |
| License | {license} |
| Ruby version | {requirement} |
| Dependencies | {list} |

## What It Does

{2-3 sentences — what problem it solves}

## Maintenance Assessment

- Last release: {date}
- Open issues: {count} (oldest: {date})
- Recent commits: {count in last 3 months}
- Test coverage: {yes/no/unknown}
- CI: {passing/failing/unknown}
- Rating: Active / Maintained / Stale / Abandoned

## Architecture Fit

### Current Project Patterns

{What patterns the project uses today for this concern}

### Library Approach

{How the library handles it — key design decisions}

### Integration Points

{Where the library connects to your code}

### Breaking Changes Risk

{What would need to change in your codebase}

## Recommendation

**Adopt / Wait / Skip**

Reason: {1-2 sentences}

If adopting:
1. {First integration step}
2. {Key configuration}
3. {Migration path from current approach}

## Watch Out For

- {Gotcha 1}
- {Gotcha 2}
```

Keep `Last Updated:` current. Planning may reuse fresh evaluation docs
to avoid respawning duplicate gem-research work.

## Size Target

One document, ~5KB max. No separate summary, index, or
integration guide files — everything in one evaluation doc.

## After Evaluation — STOP

Present the recommendation and ask user what to do next:

- "Plan the integration" -> `/rb:plan`
- "Research more" -> continue
- "Skip it" -> end
