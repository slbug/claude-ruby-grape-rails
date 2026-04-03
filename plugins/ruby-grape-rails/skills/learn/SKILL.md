---
name: rb:learn
description: Capture lessons after fixing a bug or receiving a correction — ActiveRecord, Rails, Grape, Sidekiq mistakes. Use when the user corrects your approach or teaches a pattern.
argument-hint: <description of what was fixed>
effort: low
---

# Learn From the Fix

After fixing a bug or receiving a correction, capture the lesson
to prevent future mistakes.

## Usage

```
/rb:learn Fixed N+1 query in user listing - was missing includes
/rb:learn String vs symbol key mismatch in params handling
/rb:learn Turbo Frame needs data-turbo-frame attribute in tests
```

## Workflow

### Step 1: Identify the Root Cause

Look at recent conversation context or the file/diff the user points at.
Classify the mistake:

- **Knowledge gap**: didn't know the correct API or pattern
- **Wrong assumption**: assumed behavior that doesn't match reality
- **Tooling gap**: lacked a check that would have caught this
- **Process failure**: skipped a step or checked the wrong thing

Extract the root cause, not the symptom. "Missing `includes` on
association" not "query was slow."

### Step 2: Check for Duplicates

Before writing anything, check all existing knowledge stores:

1. Read `${CLAUDE_SKILL_DIR}/references/common-mistakes.md` (shipped
   plugin reference — READ-ONLY, never edit)
2. Grep project `CLAUDE.md` for the pattern keyword
3. Grep `.claude/solutions/` for similar fixes
4. Check auto-memory for similar lessons

If already documented, tell the user and stop. Do not duplicate.

### Step 3: Decide Destination

**CRITICAL: NEVER edit plugin files.** Files under
`~/.claude/plugins/` are cached and get overwritten on updates.
Always write to project or memory locations.

| Scope | Destination | When to use |
|-------|-------------|-------------|
| This project only | Project `CLAUDE.md` | Convention or rule for this codebase |
| Cross-project | Auto-memory | General Ruby/Rails lesson that applies everywhere |
| Complex fix | `.claude/solutions/` via `/rb:compound` | Multi-step debugging story |
| Safety-critical | Iron Law suggestion | Suggest to user, never auto-add |

**Auto-memory requires consent.** Before writing to
`~/.claude/projects/{hash}/memory/`, ask the user: "This lesson applies
beyond this project. Save to auto-memory for future sessions?"

### Step 4: Write the Lesson

**For project CLAUDE.md** — append a concise rule:

```
## Lessons Learned

N. **[SHORT RULE]** — Do NOT [bad pattern]. Instead [good pattern].
   Why: [root cause in one sentence]
```

**For auto-memory** — write a memory file following the memory system
format with type `feedback` and a clear rule + why + how-to-apply.

**For `.claude/solutions/`** — hand off to `/rb:compound` with context.

### Step 5: Suggest Future Detection

Optionally suggest what would have caught this earlier:

- A hook check (e.g., "add N+1 detection to post-edit hooks")
- A linter rule (e.g., "StandardRB custom cop for this pattern")
- A test pattern (e.g., "add factory trait for this edge case")
- An Iron Law addition (only if safety-critical and universal)

## Output

After capturing, confirm:

```
Lesson captured in [destination]

Pattern: Do NOT [bad] — instead [good]
Category: [ActiveRecord/Rails/Grape/Sidekiq/Testing/Security/etc]
Root cause type: [knowledge gap/wrong assumption/tooling gap/process failure]
```

## Iron Laws

1. NEVER edit shipped plugin files — cached, overwritten on updates
2. DO NOT duplicate existing lessons — always check all 4 stores first
3. Capture root cause, not symptom
4. Keep lessons concise — one rule per lesson
5. Ask user before writing to auto-memory — cross-project scope needs consent

## Compound vs Learn

- **Learn**: Extract a concise, generalizable rule or pattern
- **Compound** (`/rb:compound`): Capture a specific problem/solution story

Use both: Learn for the rule, Compound for the detailed case.

## References (READ-ONLY — do NOT edit)

- `${CLAUDE_SKILL_DIR}/references/common-mistakes.md` — Common Ruby/Rails
  mistakes reference. Consult when checking for duplicates. Ships with
  the plugin — NEVER modify.
- `${CLAUDE_SKILL_DIR}/references/learn-workflow.md` — Detailed workflow
  with destination examples and edge cases
