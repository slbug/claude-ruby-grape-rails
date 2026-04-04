---
name: intent-detection
description: "First-message command router. Use when the user's opening message describes work without specifying an /rb: command and needs help picking the right workflow."
user-invocable: false
effort: low
---
# Intent Detection — Workflow Routing

When user describes work WITHOUT specifying a `/rb:` command, analyze their intent and suggest the appropriate workflow BEFORE starting work.

## Routing Table

| Signal | Detected Intent | Suggest |
|--------|----------------|---------|
| "bug", "error", "crash", "failing", "broken", stack trace | Bug investigation | `/rb:investigate` |
| "add", "implement", "build", "create" + multi-step | New feature | `/rb:plan` |
| "review", "check", "audit" code | Code review | `/rb:review` |
| "fix" + small/specific scope | Quick fix | handle directly or `/rb:quick` |
| "refactor", "clean up", "improve" | Refactoring | `/rb:plan` (needs scope) |
| "research", "how to", "what's the best" | Research | `/rb:research` |
| "evaluate", "compare", "adopt", "library", "should we use" | Library evaluation | `/rb:research --library` |
| "test", "spec", "coverage" | Testing | handle directly or `/rb:plan` |
| Describes 1-2 file changes, < 50 lines | Small task | handle directly |
| "deploy", "release", "production" | Deployment | `/rb:verify` then deploy |
| "performance", "slow", "N+1", "memory" | Performance | `/rb:perf` |
| "PR review", "review comments", "address feedback", "respond to PR" | PR response | `/rb:pr-review` |
| "permission prompts", "stop asking", "settings.json", "allow commands", "permission fatigue" | Permission tuning | `/rb:permissions` |
| "that worked", "fixed it", "problem solved" | Knowledge capture | `/rb:compound` |
| "enhance plan", "more detail", "deepen" | Plan enhancement | `/rb:plan --existing` |
| "triage", "which findings", "prioritize fixes" | Finding triage | `/rb:triage` |
| "brainstorm", "explore options", "not sure how", "multiple approaches", "what's the best way to architect" | Design exploration | `/rb:brainstorm` |

## Behavior

1. Read user's first message
2. Match against routing table (use keyword + context signals, not exact match)
3. If match found with multi-step workflow: "This looks like [intent]. I'd suggest `[command]` — want me to run it, or should I just dive in?"
4. If trivial task (typo, single-line fix, config change): skip suggestion, just do it
5. If user already specified a `/rb:` command: follow it, don't re-suggest
6. **NEVER block the user** — suggestion only, not mandatory

## Confidence Signals

High confidence (suggest immediately):

- Stack trace or error message pasted → `/rb:investigate`
- "Add [feature] with [multiple components]" → `/rb:plan`
- "Review my changes" or "check this PR" → `/rb:review`

Medium confidence (suggest with caveat):

- "Fix [thing]" — could be quick or complex, suggest based on scope description
- "Update [thing]" — could be small edit or refactor

Low confidence (just do it):

- Single file mentioned, clear change
- "Change X to Y"
- Configuration or dependency updates

## Complexity Signals

When a task matches a workflow command, check complexity before suggesting:

**Trivial signals** (suggest `/rb:quick` or handle directly):

- Single file mentioned explicitly
- "exclude X from Y", "add X to config", "rename", "change X to Y"
- Problem + solution both stated ("X is wrong, change to Y")
- One-line fix described

**Complex signals** (suggest `/rb:plan` or `/rb:investigate`):

- 3+ modules or files mentioned
- "intermittent", "race condition", "sometimes", "random"
- Stack trace with 5+ frames
- "across", "all", "every" (scope indicators)

**Override rule**: If user invokes `/rb:full` but task matches trivial signals:
"This looks like a quick fix. Want `/rb:quick` instead, or stick with the full cycle?"

## Iron Laws

1. **NEVER block on suggestion** — If user starts explaining, just do the work
2. **One suggestion max** — Don't re-suggest if user ignores first suggestion
3. **Commands are shortcuts, not gates** — All work can be done without commands

## Integration

This skill is consulted at session start. It works alongside:

- SessionStart hook (shows plugin loaded message)
- CLAUDE.md routing instructions (passive reference)
- Individual workflow skills (activated by commands)
