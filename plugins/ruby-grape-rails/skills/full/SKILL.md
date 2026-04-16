---
name: rb:full
description: "Use when running the hands-off end-to-end lifecycle: autonomously runs plan, work, verify, review, and compound in one command with no user intervention needed."
when_to_use: "Triggers: \"do everything\", \"full lifecycle\", \"hands-off\", \"plan and implement\", \"end to end\"."
argument-hint: "<feature description OR plan path>"
effort: max
---
# Full Workflow

`/rb:full` runs:

0. `/rb:brainstorm` (optional) → if requirements are vague, run before planning
1. `/rb:plan` → sets active plan marker
2. `/rb:work` → uses marker to resume, clears on completion
3. `/rb:verify` → validates implementation
4. `/rb:review` → quality check
5. `/rb:compound` → captures learnings

Use it for well-scoped work when the user wants the full cycle, not for vague requirements.

## Active Plan Marker Lifecycle

The marker tracks the current plan through the full cycle:

1. **Start /rb:full**: Begin autonomous cycle
2. **Run /rb:plan**: Creates plan and sets marker
3. **Run /rb:work**: Uses marker, clears it on completion
4. **Run /rb:verify, /rb:review, /rb:compound**

If interrupted during work, the marker enables session resume on next startup.

**Note:** `/rb:full` does not directly write the marker—it relies on `/rb:plan` to set it and `/rb:work` to clear it.
