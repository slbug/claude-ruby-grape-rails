---
name: rb:document
description: "Generating documentation for implemented Ruby/Rails/Grape features: YARD/RDoc method docs, README updates, ADRs. Runs after /rb:review passes."
argument-hint: "[plan-file OR feature-name]"
effort: low
disable-model-invocation: true
---
# Document

Generate documentation for newly implemented features.

## Usage

```
/rb:document .claude/plans/magic-link-auth/plan.md
/rb:document magic link authentication
/rb:document  # Auto-detect from recent plan
```

## Iron Laws

1. **Never remove existing documentation** — Existing docs may reflect design intent that isn't obvious from code alone; update rather than replace
2. **YARD/RDoc on every public class/module** — Undocumented code accumulates quickly and creates onboarding friction for new team members
3. **ADRs capture the "why", not the "what"** — Code shows what was built; ADRs explain why this approach was chosen over alternatives
4. **Match docs to method's public API** — Document parameters, return values, and edge cases; callers shouldn't need to read the implementation

## What Gets Documented

| Output | Description |
|--------|-------------|
| Class/module docs | For new classes/modules missing documentation |
| Method docs | For public methods without docs |
| README section | For user-facing features |
| ADR | For significant architectural decisions |

## Workflow

### Step 0: Pre-check (avoid no-op runs)

Run `${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref` → 3 `KEY=value` lines
on stdout (`BASE_REF`, `REMOTE`, `DEFAULT_BRANCH`; handles custom
remotes, non-standard default branches, fetches before resolving).
Use emitted values as substitutions: run
`git merge-base HEAD BASE_REF_VALUE` and capture the result.
Run `git diff --name-only --diff-filter=A MERGE_BASE_VALUE HEAD -- '*.rb'`
to list new Ruby files added on the current branch.

If NO new `.rb` files were added (only modifications), skip the full
audit and report: "No new modules — documentation coverage unchanged."
This prevents 35-message analysis sessions that conclude "PASS" with
zero output (confirmed: session bb0a0454 wasted ~2K tokens on no-op).

1. **Identify** new modules from recent commits or plan file
2. **Check** documentation coverage (YARD, RDoc)
3. **Generate** missing docs using templates
4. **Add** README section if user-facing feature
5. **Create** ADR if architectural decision was made
6. **Write** report to `.claude/plans/{slug}/docs/{feature}.md`

## When to Generate ADRs

| Trigger | Create ADR |
|---------|-----------|
| New external dependency | Yes |
| New database table | Maybe (if schema non-obvious) |
| New background job system | Yes (explain why new system needed) |
| New service layer | Maybe (if boundaries non-obvious) |
| New auth mechanism | Yes |
| Performance optimization | Yes |

## Integration with Workflow

```text
/rb:plan → /rb:work → /rb:review
       ↓
/rb:document  ← YOU ARE HERE (optional, suggested after review passes)
```

## References

- `references/doc-templates.md` — YARD, RDoc, README, ADR templates
- `references/output-format.md` — Documentation report format
- `references/doc-best-practices.md` — Ruby documentation best practices
- `references/documentation-patterns.md` — Detailed documentation patterns
