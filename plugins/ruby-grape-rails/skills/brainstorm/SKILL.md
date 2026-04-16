---
name: rb:brainstorm
description: "Use when you have a vague idea and want to explore approaches, compare options, and gather requirements before planning a Ruby/Rails/Grape feature."
when_to_use: "Triggers: \"brainstorm\", \"explore ideas\", \"not sure how to approach\", \"discuss before planning\", \"what if we\". Does NOT handle: detailed planning, implementation, research with citations."
effort: high
argument-hint: <topic or feature idea>
disable-model-invocation: true
---
# Brainstorm

Adaptive requirements gathering before planning. Produces an `interview.md`
that `/rb:plan` consumes to skip clarification.

## Workflow

```
/rb:brainstorm {topic}
    |
    v
[INTERVIEW] <───────────────────┐
    |                            |
    v (sufficient OR user exit)  |
[DECISION POINT]                 |
    ├─ Research ──> [RESEARCH] ──┘
    ├─ Continue interview ───────┘
    ├─ Make a plan ──> STOP (suggest /rb:plan .claude/plans/{slug}/interview.md)
    ├─ Store & exit ──> STOP (artifacts saved)
    └─ Discuss ──> freeform ──> [DECISION POINT]
```

## Phase 1: Adaptive Interview

Ask ONE question at a time. Track coverage across 6 dimensions:

| Dimension | Target | Sufficient | Score |
|-----------|--------|------------|-------|
| What | Specific behavior/features | Concrete verbs, not vague | 0-2 |
| Why | Problem solved, user need | Clear benefit stated | 0-2 |
| Scope | In/out boundaries | Explicit exclusions | 0-2 |
| Where | Modules, contexts, files | Paths or context names | 0-2 |
| How | Approach, constraints | At least one constraint | 0-2 |
| Edge | Error states, scale, auth | 2+ edge cases identified | 0-2 |

**Scoring:** 0 = uncovered, 1 = partial ("maybe some caching"), 2 = sufficient
("Redis cache for session tokens, 15min TTL").

**Interview sufficient** when total score >= 8 out of 12 and every dimension
has at least a score of 1.

### Question Order

1. **What** — almost always first
2. **Why** — understand motivation before narrowing
3. **Scope** — ask within first 3-4 questions, especially for "optimize X" topics
4. **Where/How/Edge** — order by lowest coverage, informed by codebase scans

### Between-Question Codebase Scans

Before each question after the first, run a brief codebase scan with Grep/Glob
based on what the user just said. See `references/interview-techniques.md` for
the scan pattern table.

Scan depth:

- **First mention**: Medium scan — Grep + Read 1-2 key files (~5s)
- **Follow-up on same topic**: Light scan — Grep only (~2s)
- **User asks "what do I have?"**: Full scan — Glob + Grep + Read multiple files (~10s)
- **Never**: spawn an agent for scanning during interview (too slow)

### Ruby Stack Detection (Once at Start)

At brainstorm start, detect and record:

- ORM: Active Record vs Sequel (from Gemfile)
- API: Grape vs Rails API vs standard Rails (from `app/api/` or `app/apis/`)
- Jobs: Sidekiq vs Solid Queue (from Gemfile/config)
- Monolith: Packwerk/packages vs flat (from `packwerk.yml` or `packs/`)
- Testing: RSpec vs Minitest (from `spec/` vs `test/`)
- Formatter: StandardRB vs RuboCop (from `.standard.yml` or `.rubocop.yml`)

Record in `interview.md` under `## Codebase Context`.

## Signal Detection

**Vague answers** ("something like...", "maybe", "whatever you think"):
Probe deeper on the SAME dimension with a more specific question. Offer
concrete options: "Would it be more like A or B?"

**Expertise signals** (uses framework terms correctly, mentions modules by name):
Skip basic questions. Ask at implementation level.

**Scope creep** (mentions 3+ new features not in original topic):
Acknowledge, then narrow: "Great ideas. Should we focus on {core} first and
note {extras} as future work?"

**Saturation** (2 consecutive answers add no new coverage):
Present Decision Point.

## Phase 2: Decision Point (Mandatory)

**CRITICAL: This is the most important phase. Never skip it.**

1. Write current state to `.claude/plans/{slug}/interview.md`
2. Show coverage summary: `Coverage: What 2/2 | Why 2/2 | Scope 1/2 | ...`
3. Use AskUserQuestion with EXACTLY these options:
   - **Research** — search codebase + internet for approaches (2 agents)
   - **Continue interview** — ask more questions
   - **Make a plan** — suggest: `/rb:plan .claude/plans/{slug}/interview.md`
   - **Store & exit** — save everything, come back later
   - **Discuss** — freeform conversation about what we've gathered
4. **STOP after presenting options** — do NOT proceed without user input

## Phase 3: Research (Diverge-Evaluate-Converge)

See `references/research-integration.md` for the full pattern.

**First cycle: MAX 2 agents.** Spawn both in ONE Tool Use block with
`run_in_background: true`:

1. **`rails-patterns-analyst`**: "How does this codebase handle {topics}?"
   Writes findings to `.claude/plans/{slug}/research/codebase-scan.md`
2. **`web-researcher`**: "Ruby/Rails approaches to {topics}"
   Returns summary

**Evaluate** (in main context):

- **Thesis**: Why it works for THIS codebase
- **Antithesis**: Why it might NOT work

**Converge**: Present 2-3 approaches with trade-offs. Never recommend one.

Return to Decision Point.

**Soft limit**: After 3 research cycles, suggest moving to a plan.

## Output

Produces `.claude/plans/{slug}/interview.md`. See
`references/interview-techniques.md` for the full template.

Key sections: Summary, Coverage Details (per dimension), Codebase Context
(Ruby stack), Research Findings, Open Questions, Transcript.

**Status: COMPLETE** when all dimensions >= 1 and total >= 8.
**Status: IN_PROGRESS** when user chose "Store & exit" before sufficient coverage.

## Iron Laws

1. **NEVER auto-transition to `/rb:plan`** — always present as option
2. **ONE question at a time** — never dump a question list
3. **Always write artifacts** — `interview.md` is the contract with `/rb:plan`
4. **Scan codebase between questions** — every question context-aware
5. **AskUserQuestion at EVERY decision point** — most critical law. After
   interview, after research, after discuss — always present options. Never
   skip the checkpoint
6. **STOP after presenting options** — do not proceed without user input
7. **MAX 2 agents in first research cycle** — deeper dives are subsequent
   cycles (user picks "Research" again)

## Integration

```
/rb:brainstorm ──> interview.md ──> /rb:plan (skips clarification)
                               ──> stored for later session
```

Position in workflow: Optional upstream of `/rb:plan`.
