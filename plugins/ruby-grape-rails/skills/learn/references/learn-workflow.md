# Learn Workflow — Detailed Reference

> **READ-ONLY**: This file ships with the plugin. Do NOT edit it
> at runtime — changes to cached plugin files are lost on update.

## Destination Decision Tree

```
Is the lesson specific to THIS project's codebase?
  YES → Project CLAUDE.md
  NO  → Is it a general Ruby/Rails/Grape pattern?
    YES → Is it a simple rule (one sentence)?
      YES → Auto-memory (with user consent)
      NO  → .claude/solutions/ via /rb:compound
    NO  → Skip — too niche for any persistent store
```

## Duplicate Detection

Check in this order (stop if found):

1. `${CLAUDE_SKILL_DIR}/references/common-mistakes.md` — shipped reference
2. Project `CLAUDE.md` — grep for keywords from the root cause
3. `.claude/solutions/` — grep for symptom or error message
4. Auto-memory — check `~/.claude/projects/{hash}/memory/MEMORY.md`

Common false negatives:

- Same root cause, different symptom (search by cause, not error)
- Different wording for the same rule (use multiple keywords)
- Already an Iron Law but not recognized as covering this case

## Project CLAUDE.md Format

Append under a `## Lessons Learned` section (create if missing):

```markdown
## Lessons Learned

1. **Eager load in loops** — Do NOT access associations in loops without
   `includes`. Instead preload all needed associations in the query.
   Why: Each iteration fires a separate SQL query (N+1).

2. **Factory build vs create** — Do NOT use `create` inside factory
   definitions. Instead use `association` or `build`.
   Why: `create` persists to DB even on `build(:record)`.
```

## Auto-Memory Format

Write as a feedback-type memory file:

```markdown
---
name: eager-load-associations
description: Always preload associations before iterating — prevents N+1 queries
type: feedback
---

Do NOT access ActiveRecord associations in loops without `includes` or `preload`.

**Why:** Each loop iteration fires a separate SQL query. This causes N+1
performance degradation that is invisible in development with small datasets.

**How to apply:** Before any code that iterates over records and accesses
an association, check the query for `.includes(:association_name)`.
```

## Compound Handoff

When the fix is complex (multi-file, required investigation), hand off:

```
This fix has a detailed investigation story. Handing off to /rb:compound
for full documentation.

Context: [brief summary of what was fixed and why]
```

## Iron Law Suggestions

Only suggest a new Iron Law when ALL of these are true:

- The mistake is safety-critical or causes data loss
- It applies universally to Ruby/Rails projects (not project-specific)
- No existing Iron Law already covers it
- The rule can be stated in one sentence

Format the suggestion as:

```
This might warrant an Iron Law:

"NEVER [bad pattern] — [consequence]. Instead [good pattern]."

Want me to suggest this as a PR to the plugin's iron-laws.yml?
```

## Root Cause Classification

| Type | Example | Typical destination |
|------|---------|-------------------|
| Knowledge gap | Didn't know `has_many` needs `dependent:` | Auto-memory |
| Wrong assumption | Assumed `params` uses symbol keys | Project CLAUDE.md |
| Tooling gap | No N+1 detection in test suite | Suggest hook/linter |
| Process failure | Skipped `bundle exec rspec` before commit | Project CLAUDE.md |

## Edge Cases

**User corrects you mid-conversation**: This is the most common trigger.
Capture what you got wrong and the correct approach. The user's correction
IS the lesson.

**Multiple lessons from one fix**: Write each as a separate entry. Don't
bundle unrelated lessons into one.

**Lesson contradicts existing rule**: Flag the conflict. Ask the user
which rule should win. Update or remove the outdated rule.

**Lesson is about this plugin, not the project**: Suggest the user file
an issue or PR on the plugin repo. Do NOT edit plugin files.
