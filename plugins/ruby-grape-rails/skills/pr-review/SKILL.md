---
name: rb:pr-review
description: "Use when addressing PR review comments: fetch them, categorize them, draft responses, and optionally fix code. Use when the user has PR feedback, reviewer suggestions, or shares a PR number or URL."
when_to_use: "Triggers: \"PR feedback\", \"review comments\", \"reviewer said\", \"address PR\", \"PR #\"."
argument-hint: <PR number or URL> [--fix]
disable-model-invocation: true
effort: high
---
# PR Review Response

Fetch PR review comments, categorize them, draft responses,
and optionally apply code fixes.

## Usage

```
/rb:pr-review 42              # Address comments on PR #42
/rb:pr-review 42 --fix        # Address + apply code fixes
/rb:pr-review https://...     # Full URL also works
```

## Arguments

`$ARGUMENTS` = PR number (or URL), optionally followed by `--fix`.

## Workflow

### Step 1: Fetch PR Context

Fetch PR context:

- Run `gh pr view {number} --json title,body,state,baseRefName,headRefName` for metadata
- Run `gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate` for inline comments
- Run `gh api repos/{owner}/{repo}/pulls/{number}/reviews --paginate` for review data
- Run `gh pr diff {number}` for the diff

Parse the PR number from `$ARGUMENTS`. If a URL, extract the
number from it. Detect `--fix` flag.

### Step 2: Categorize Comments

Group each comment into one of these categories:

| Category | Signal | Action |
|----------|--------|--------|
| **Code change** | "should be", "change to", "use X instead" | Draft fix + response |
| **Question** | "why", "what if", "how does" | Draft explanation |
| **Nitpick** | "nit:", style-only, formatting | Quick acknowledgment |
| **Praise** | "nice", "good", "LGTM" | No action needed |
| **Discussion** | Architecture, trade-offs, alternatives | Draft thoughtful response |

### Step 3: Map to Code Locations

For each code-change comment:

1. Find the file and line from the comment's `path` and `position`
2. Read the current code at that location
3. Understand the reviewer's suggestion in context
4. Check if the suggestion conflicts with Iron Laws

### Step 4: Draft Responses

For each comment, draft a response following patterns in
`references/response-patterns.md`.

Present ALL draft responses to the user for review:

```
## PR #{number}: {title}
### {n} comments to address

**Code changes ({n}):**
1. {file}:{line} — {reviewer suggestion} → {proposed fix}

**Questions ({n}):**
1. {question summary} → {draft answer}

**Nitpicks ({n}):**
1. {nit} → Acknowledged

**Discussion ({n}):**
1. {topic} → {draft response}
```

### Step 5: Apply Fixes (if --fix)

If `--fix` flag provided AND user approves:

1. Apply code changes from approved code-change responses
2. Run the narrowest correct verification set:
   - `bundle exec rails zeitwerk:check` only for full Rails apps
   - the configured direct linter (`standardrb` or `rubocop`)
   - targeted or full tests as appropriate
3. If tests pass, present the changes
4. Do NOT commit or push — leave that to the user

### Step 6: Post Responses (with user approval)

**STOP and ask user to review all draft responses.**

After user approves (may edit some):

Post each approved response with `gh api repos/{owner}/{repo}/pulls/{number}/comments/{id}/replies -f body="{response}"`.

## Iron Laws

1. **NEVER auto-post responses** — Always show drafts and get explicit approval
2. **NEVER dismiss a review** — Only the reviewer should dismiss
3. **Iron Laws override reviewer suggestions** — If a reviewer suggests code that violates an Iron Law, explain why in the response
4. **Keep responses constructive** — Acknowledge the feedback, explain reasoning
5. **Separate fixes from responses** — Apply code changes in a separate step

## Integration

```text
PR receives review comments
       ↓
/rb:pr-review {number}  ← YOU ARE HERE
       ↓
   Fix code? → --fix flag applies changes
       ↓
   Post responses (after user approval)
       ↓
   Push changes → user handles git push
```

## Next Steps

After addressing review comments, suggest follow-up:

```
- `/rb:plan` — Create a plan if findings reveal scope gaps
- `/rb:verify` — Run full verification before pushing
- Push changes — user handles git push
```

## References

- `references/response-patterns.md` — Response templates and common patterns
