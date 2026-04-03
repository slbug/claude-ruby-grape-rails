# Research Integration

## Diverge-Evaluate-Converge Pattern

### Step 1: Diverge (Generate Diverse Approaches)

Spawn 2 agents in ONE Tool Use block with `run_in_background: true`:

1. **`rails-patterns-analyst`**: "How does this codebase handle {topics}?"
   - Writes findings to `.claude/plans/{slug}/research/codebase-scan.md`
   - Focus: existing patterns, conventions, relevant modules

2. **`web-researcher`**: "Ruby/Rails approaches to {topics}"
   - Returns 500-word summary of community patterns and approaches
   - Focus: proven patterns, trade-offs, library options

**Iron Law: MAX 2 agents in first research cycle.** Keep it fast (~2-3 min).
Do NOT spawn additional specialists in the first cycle.

### Step 2: Evaluate (Thesis + Antithesis per Approach)

Happens in main context (not subagent) — synthesize both agents' findings
with interview context:

- **Thesis**: Why this approach works for THIS codebase
  - Aligns with existing patterns found by rails-patterns-analyst
  - Satisfies constraints from interview
  - Handles edge cases identified

- **Antithesis**: Why this approach might NOT work
  - Conflicts with existing architecture
  - Scale or complexity concerns
  - Library incompatibility or version constraints
  - Breaks existing conventions

### Step 3: Converge (Present 2-3 Options)

Format each approach as:

- **Description**: What the approach is
- **Fits your codebase because**: Reasons grounded in existing code
- **Might not fit because**: Honest trade-offs
- **Would touch**: Files/modules that would change
- **Complexity**: Low / Medium / High
- **Libraries needed**: New dependencies (if any)

**Rules:**

- Always present at least 2 approaches (even if one is "do nothing differently")
- Never recommend one as "the best" — present trade-offs, let user choose
- Include an approach that uses existing patterns when possible

After presenting research: Return to Decision Point.

## Subsequent Research Cycles

When user picks "Research" again after the first cycle:

- Spawn 1-2 targeted agents for specific questions
- Focus on gaps identified during evaluation
- Deeper dives into specific libraries, patterns, or trade-offs

## Research Log

Track iterations in `interview.md` under Research Findings:

```markdown
## Research Log
- Cycle 1: rails-patterns-analyst + web-researcher (3 approaches found)
- Cycle 2: deep-dive on service object approach (web-researcher)
- Cycle 3: ...
```

**Soft limit**: After 3 research cycles, suggest: "We have substantial research
now. Ready to move to a plan, or is there a specific gap remaining?"

## Integration with /rb:plan

When `/rb:plan` detects `.claude/plans/{slug}/interview.md` with research:

1. **Skips clarification** — interview IS the clarification
2. **May skip rails-patterns-analyst spawn** — `codebase-scan.md` already exists
3. **May skip web-researcher** — external findings already exist
4. **Uses approach selection** — if user chose an approach, plan focuses on it
5. **Notes in scratchpad**: "Requirements from /rb:brainstorm interview"
