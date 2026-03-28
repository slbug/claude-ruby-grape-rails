# Scratchpad Template

Use this canonical structure for `.claude/plans/{slug}/scratchpad.md`.

```markdown
# Scratchpad: {slug}

- Request: {summary}
- Plan: .claude/plans/{slug}/plan.md

## Dead Ends

(none yet)

## Decisions

### Clarifications

(none yet)

### Research Cache Reuse

(none yet)

### Infrastructure

(none yet)

## Hypotheses

(none yet)

## Open Questions

(none yet)

## Handoff

- Branch: {branch}
- Next: (to be filled)
```

## Section Rules

- `Dead Ends`
  - failed approaches that future sessions should not retry blindly
- `Decisions`
  - durable choices and why they were made
  - use the provided subsections for:
    - clarification answers
    - cache-reuse notes
    - infrastructure discoveries
- `Hypotheses`
  - ideas worth testing that are not yet decisions
- `Open Questions`
  - unresolved product, architecture, or implementation questions
- `Handoff`
  - session continuity notes, API failures, branch info, and next-step guidance

## Notes

- Keep `Handoff` as the last top-level section so hooks can append to it safely.
- Replace `(none yet)` when real content appears.
- Do not add extra top-level sections unless the plugin contract changes.
