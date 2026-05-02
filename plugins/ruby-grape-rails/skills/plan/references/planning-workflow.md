# Planning Workflow — Detailed Steps

Full step-by-step details for `/rb:plan`. The SKILL.md has a
summary; this reference has the complete workflow.

## Clarification Questions (when requirements are fuzzy)

When the description is vague, unclear, or missing key details,
ask clarifying questions **one at a time** before planning.

### When to Use /rb:brainstorm Instead

Use `/rb:brainstorm` when:

- 3+ clarification questions would be needed
- User is unsure about scope or approach ("not sure how", "multiple ways")
- Multiple valid architectural paths exist
- Brainstorm produces `.claude/plans/{slug}/interview.md` with Status: COMPLETE
- Plan consumes it: skips clarification, uses interview context to scope
  agent research (current-code agents like `rails-patterns-analyst` still run)

### Inline Clarification (when brainstorm is not needed)

**Signals that clarification is needed:**

- Description is under 10 words without specifics
- Contains "some kind of", "maybe", "I think", "not sure"
- Missing WHO (which users), WHAT (specific behavior), or WHY
- Multiple possible interpretations exist
- Security/data implications that need explicit decisions

**Question flow** (ask ONE at a time, not all at once):

1. **Purpose**: "What problem does this solve for users?"
2. **Scope**: "Which specific behavior should this include?"
3. **Users**: "Who will use this? Any role/permission differences?"
4. **Constraints**: "Any technical constraints or preferences?"
5. **Edge cases**: "What should happen when [X]?"

**Stop asking when**: You have enough to write a plan with
concrete tasks. 2-4 questions is usually enough. Don't
interrogate — if the user gives a detailed answer, extract
what you need and move on.

**Capture decisions**: Save all clarification answers to
`.claude/plans/{slug}/scratchpad.md` under
`## Decisions` → `### Clarifications` for future reference.

## Depth Detection

If `--depth` not specified, auto-detect from **both** the clarity
of the request and the technical complexity:

| Request Clarity            | Technical Scope                    | Depth                       |
| -------------------------- | ---------------------------------- | --------------------------- |
| Clear + specific           | 1 context, <5 files                | `quick`                     |
| Clear + specific           | 2-3 contexts, models/controllers     | `standard`                  |
| Clear + specific           | 4+ contexts, security, new workers   | `deep`                      |
| Vague (post-clarification) | Any                                | At least `standard`         |
| From review file           | Any                                | `standard` (scope is known) |

**Depth determines agent count AND plan detail:**

| Depth      | Agents             | Clarification           | Plan Detail                          |
| ---------- | ------------------ | ----------------------- | ------------------------------------ |
| `quick`    | 1 (patterns only)  | Skip if clear           | Task list, minimal prose             |
| `standard` | 2-3 specialists    | 1-2 questions if needed | Phased tasks with code patterns      |
| `deep`     | 4+ (full research) | 3-5 questions           | Full system map, risks, alternatives |

**Ruby-specific complexity signals**: New migration? New Hotwire/Turbo?
New Sidekiq worker? Changes Rails model associations? Multiple
models affected? These push toward deeper planning.

## Agent Spawning

Spawn agents using `Agent(...)` based on what's actually needed.
Delegate broad research to agents. You MAY read specific files
(CI config, a single model) for plan detail, but do NOT do the
agents' job -- let them handle pattern discovery.

**Agent count scales with depth:**

- `quick`: 1 agent (rails-patterns-analyst only)
- `standard`: 2-3 agents (patterns + relevant specialists)
- `deep`: 4+ agents (patterns + specialists +
  web-researcher + ruby-gem-researcher)

**Always spawn:**

- `rails-patterns-analyst`: Analyze codebase for existing patterns

**Spawn conditionally based on feature needs:**

| Condition                             | Agent                    |
| ------------------------------------- | ------------------------ |
| NEW gem needed (not in Gemfile)       | `ruby-gem-researcher`    |
| UI, form, real-time features          | `rails-architect`        |
| Database, schema, table changes       | `active-record-schema-designer` |
| Job, async, queue                      | `sidekiq-specialist`     |
| Threads, concurrency, async           | `ruby-runtime-advisor`   |
| Auth, login, permission, security     | `security-analyzer`      |
| Unfamiliar tech, need community input | `web-researcher`         |
| Changing method signatures            | `call-tracer`            |

**ruby-gem-researcher rules (STRICT):**

- ONLY spawn when evaluating a gem NOT already in Gemfile
- Do NOT spawn for: review blockers, refactoring, existing gems
- To understand an existing gem's API, use Read/Grep on
  `Gemfile.lock` or gem source instead

**CRITICAL**: Spawn ALL applicable agents via multiple Agent tool
calls in ONE Tool Use block (foreground parallel — do NOT use
`run_in_background: true`). Minimum 1 agent spawned.

**Agent prompts must be FOCUSED.** Scope each prompt to the
relevant directories, files, and patterns. Do NOT give vague
prompts like "analyze the codebase."

## Research Cache Reuse

Before spawning `web-researcher` or `ruby-gem-researcher`, check
whether fresh research already exists:

1. Create the planning namespace early:
   - `.claude/plans/{slug}/research/`
   - `.claude/plans/{slug}/summaries/`
   - `.claude/plans/{slug}/scratchpad.md`
2. Glob both:
   - `.claude/research/*.md`
   - `.claude/plans/*/research/*.md`
3. Compare the feature description or review against candidate
   filenames/content. Treat 2+ keyword matches as relevant.
4. Reuse only files whose in-file freshness metadata meets all of the
   following:
   - the file contains one of:
     `Last Updated:`, `Date:`, `**Last Updated**:`, `**Date**:`
   - the value after the colon is parseable as `YYYY-MM-DD` or an ISO
     datetime
   - the parsed timestamp is within the last 48 hours
5. Fresh file types you can reuse:
   - `*-evaluation.md` → skip `ruby-gem-researcher` for that topic
   - `.claude/research/{topic-slug}.md` or `research-*.md` →
     skip `web-researcher` for that topic
6. Record every reuse in
   `.claude/plans/{slug}/scratchpad.md` under
   `## Decisions` → `### Research Cache Reuse`:

   ```markdown
   ## Decisions

   ### Research Cache Reuse
   - REUSED: .claude/research/sidekiq-vs-solid-queue.md -> skipped web-researcher
   ```

**Do NOT reuse blindly.**

- Old/stale files may inform context, but they do not suppress fresh
  research.
- Files without parseable in-file freshness metadata may inform
  context, but they do not suppress fresh research.
- Never skip current-code discovery agents such as
  `rails-patterns-analyst`, `call-tracer`, or
  schema/security/job specialists based only on cached research.

## Waiting for Agents

Wait for every agent to complete before plan generation.

Apply Artifact Recovery for each agent in the run manifest at
`${REPO_ROOT}/.claude/plans/{plan-slug}/research-fanout/RUN-CURRENT.json`:

- Exists, `size_bytes >= 1000` → trust. Do NOT overwrite. Patch
  `status: complete` into manifest.
- Exists, `size_bytes < 1000`, return text substantially larger AND
  parses as findings → replace stub. Patch `status: stub-replaced`.
- Exists, `size_bytes < 1000`, return text empty/unusable → keep
  stub, treat as coverage gap. Patch `status: stub-no-output`.
- Missing, return text usable → extract findings from return text and
  write. Patch `status: recovered-from-return`.
- Missing, return text empty/unusable → write a stub with heading
  `# {topic-slug} — recovery stub` and body `Run produced no
  artifact and no usable return text. Research coverage gap.` Patch
  `status: stub-no-output`.

Status patch via
`echo '<json>' | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch <path>`.

NEVER copy or symlink prior-run artifacts. Decide from filesystem;
ignore return-text denial claims. Never re-spawn.

Read each verified artifact + any reused cached files in scratchpad.md
`## Decisions` → `### Research Cache Reuse`. Synthesize plan directly.

If a research agent fails AND its file is missing AND return text is
unusable, do the research yourself with Read/Grep from main session.

Mark manifest `status: complete` after `plan.md` is written.

Manifest schema + helper subcommands:
`${CLAUDE_PLUGIN_ROOT}/references/run-manifest.md`.

## Infrastructure Knowledge Persistence

When Explore agents discover **project infrastructure** (not
feature-specific code) — e.g., test helpers, factory patterns,
API endpoint maps — write a compact summary to
`.claude/plans/{slug}/scratchpad.md` under
`## Decisions` → `### Infrastructure`. This prevents re-exploration
in follow-up sessions.

Signals that knowledge is infrastructure (not feature-specific):

- Test setup patterns (`spec/support/`, `test/support/`)
- Custom RAILS_ENV configurations
- Factory/fixture patterns (FactoryBot)
- CI/deployment pipeline structure

## Breadboard System Map (Hotwire/Turbo Features)

**When to breadboard**: The feature touches 2+ pages or
components, has complex event flows (Turbo Streams, multi-step
forms), or involves navigation between multiple routes.
**Skip** for single-page CRUD, config changes, or non-Hotwire work.

If rails-architect was spawned, its report should include
affordance tables. Use these to build a system map. See
`breadboarding.md` for full details.

## Completeness Check

**MANDATORY when planning from review.** List ALL findings from
the source and verify every one is covered:

> Source has N items. Coverage:
>
> - Finding 1: -> Plan A / Task X
> - Finding 2: -> Plan A / Task Y
>
> All N items are planned.

Every finding gets a task. No exceptions. If the user wants to
exclude something, they must say so explicitly.

**Ruby completeness**: Does the plan include migration if schema
changes? Tests for new public methods? Controller actions + view
handlers? Service objects for new domain logic?

## Split Decision

**One plan = one MD file = one focused work unit.**

If the feature is small (up to ~8 tasks, same domain), skip this
step and create one plan. Do NOT ask unnecessary questions.

If the feature is large, present OPTIONS with concrete numbers:

> Based on my analysis, this feature has N concerns and ~M tasks.
> How should I structure the plans?
>
> 1. **One plan** -- 1 file, ~M tasks across K phases
> 2. **Split into X plans** -- grouped by domain:
>    - `auth/plan.md` (5 tasks) -- login, register, reset
>    - `profiles/plan.md` (4 tasks) -- avatar, bio, settings

## Plan Generation

Create plan(s) at `.claude/plans/{slug}/plan.md`.

Key requirements:

- Tasks in `- [ ] [Pn-Tm][annotation] Description` format
  (required for `/rb:work`). Valid annotations:
  `[direct]` (most common), `[active record]`, `[hotwire]`, `[sidekiq]`,
  `[concurrency]`, `[security]`, `[test]`.
  Do NOT use subagent_type names like `[general-purpose]` or
  `[solo]` -- those are not valid annotations.
- Include: Summary, Scope, Technical Decisions, Phased Tasks,
  Patterns, Risks

**Task granularity**: Tasks are logical work units, NOT individual
file edits. Group by PATTERN (what you're doing), list LOCATIONS
within. Each task includes implementation detail (code examples,
before/after). Aim for 3-8 tasks per phase, not 15+.

**Method signature precision**: When a task involves extracting,
refactoring, or renaming methods, ALWAYS specify the exact
`ClassName#method_name` for both source and target.
Example: "Extract `UserService#currency_options` from
`User` model to `Shared::CurrencyHelpers` module".
Never write vague tasks like "extract existing pattern" without
specifying the method signature — this causes issues.

**Scratchpad**: Create `.claude/plans/{slug}/scratchpad.md`
at the start of planning with initial context (feature name, brief
description, plan file path). Use the canonical structure from
`${CLAUDE_SKILL_DIR}/references/scratchpad-template.md` for:

- `## Decisions` → `### Clarifications`
- `## Decisions` → `### Research Cache Reuse`
- `## Decisions` → `### Infrastructure`
- `## Hypotheses`
- `## Open Questions`

**The plan template lives in this file** (see "Plan Template" section below).
Inline it from here when synthesizing the plan.

## Self-Check (Deep Plans Only)

For `deep` plans, answer these three questions in the plan's
**Risks** section before presenting:

1. **"What was the hardest decision?"** — Which technical choice
   had the most tradeoffs? Document alternatives considered.
2. **"What alternatives were rejected?"** — For each major
   decision, note what else was considered and why it lost.
3. **"What am I least confident about?"** — Flag areas where
   the plan might be wrong. Mark with ⚠️ for user review.

## Presenting the Plan

**STOP and present the plan.** Briefly summarize the plan (task
count, phase names, key scope). Then use `AskUserQuestion`:

For single plan:

- **Start in fresh session** (recommended for 5+ tasks)
- **Get a briefing** -- interactive walkthrough via `/rb:brief`
- **Start here** -- in current session (fine for small plans)
- **Review the plan** -- walk through phases in detail
- **Adjust the plan** -- tell me what to change

Do NOT say "Start Phase 1" — `/rb:work` runs the whole plan.

**When user selects "Start in fresh session"**, print clear
step-by-step:

```
1. Run `/new` to start a fresh session
2. Then run one of:
   /rb:work .claude/plans/{slug}/plan.md
   /rb:full .claude/plans/{slug}/plan.md  (includes review + compound)
```

## Deepening an Existing Plan (--existing mode)

When `--existing` is passed with a plan file path, enhance the
plan with deeper research instead of creating a new one.

### Deepening Workflow

1. **Load plan** -- Parse phases, tasks, annotations, `???` markers
2. **Search compound docs** -- Find known issues in planned areas
   (`grep -rl "KEYWORD" .claude/solutions/`)
3. **Spawn research agents** -- Use SPECIALIST agents (same
   selection rules as main flow), NOT Explore agents. Each agent
   MUST write detailed output to
   `.claude/plans/{slug}/research/{topic-slug}.md` and return ONLY a
   500-word summary. Spawn via multiple Agent tool calls in ONE Tool
   Use block (foreground parallel — do NOT use `run_in_background: true`)
4. **Wait for ALL agents** -- You'll be notified as each completes.
   Read each agent's output file. Do NOT proceed until all complete
5. **Enhance plan** -- Add implementation detail, resolve spikes,
   add verification criteria, note risk from compound docs
6. **Present diff summary** -- Show what was enhanced

### When Deepening Adds Value

- Plan has 5+ tasks touching unfamiliar code
- Feature involves external API integration
- Security-sensitive features (auth, payments)
- Plan generated from review findings
- Tasks have `???` or spike markers

### Deepening Rules

- **NEVER delete existing tasks** — Only add detail and risks
- **Preserve task IDs** — `[Pn-Tm]` identifiers must not change
- **Compound docs first** — Check solution docs before spawning
  agents (saves context)
- **Context budget** — `--existing` often runs in sessions with
  prior history. Use specialist agents that write to files and
  return short summaries. Never use Explore agents (they return
  full output inline and exhaust context)

## Slug Pre-Bind Detection (strict guards)

Bash sequence used by `/rb:plan` skill body for pre-bind detection.
Reads `.claude/ACTIVE_PLAN` directly. Does NOT call
`active-plan-marker.sh get`.

```bash
ACTIVE_FILE="$(pwd)/.claude/ACTIVE_PLAN"

if [[ -f "$ACTIVE_FILE" && ! -L "$ACTIVE_FILE" ]]; then
  IFS= read -r MARKED_DIR < "$ACTIVE_FILE"
  case "$MARKED_DIR" in
    /*) ;;
    *)  MARKED_DIR="$(pwd)/${MARKED_DIR#./}" ;;
  esac

  # ALL FOUR guards must pass to reuse the pre-bound namespace:
  if [[ -d "$MARKED_DIR" \
        && ! -L "$MARKED_DIR" \
        && -f "$MARKED_DIR/progress.md" \
        && ! -L "$MARKED_DIR/progress.md" \
        && ! -f "$MARKED_DIR/plan.md" \
        ]] && grep -qE '^- \*\*State\*\*: (INITIALIZING|DISCOVERING)$' \
                  "$MARKED_DIR/progress.md"; then
    SLUG_DIR="$MARKED_DIR"   # reuse pre-bound namespace
  fi
fi
# Otherwise: derive fresh slug, create namespace, set marker AFTER plan.md write.
```

## Agent Selection Matrix

| Request Contains | Spawn Agent |
|---|---|
| Rails UI/feature | `rails-patterns-analyst` + `rails-architect` |
| Database changes | `active-record-schema-designer` |
| Background jobs | `sidekiq-specialist` |
| Auth/payments/admin | `security-analyzer` |
| New gem/library | `ruby-gem-researcher` |
| Cross-cutting change | `call-tracer` |
| Complex workflow | `rails-architect` |
| API changes | `rails-patterns-analyst` + `security-analyzer` |

## Spawning Strategy

```text
Phase 1: Research (parallel block)
├─ rails-patterns-analyst    (always)
├─ active-record-schema-designer (if DB changes)
├─ security-analyzer         (if auth/data sensitive)
└─ sidekiq-specialist        (if jobs)

Phase 2: Architecture (if needed)
└─ rails-architect           (if service layer / cross-cutting)
```

## Agent Briefing Template

```text
Task: Analyze [aspect] for [feature]

Context:
- Feature: [description]
- Files involved: [list]
- Constraints: [list]
- Questions to answer:
  1. [question]
  2. [question]

Output:
- Write detailed findings to .claude/plans/{slug}/research/{topic-slug}.md
- Return ONLY a 500-word summary in Agent() result text

Stop after returning. Do NOT call Agent() — this is a leaf research.
```

## Progress Tracking Template

```markdown
## Agent Coordination

### Spawned
- [x] rails-patterns-analyst (completed)
- [x] active-record-schema-designer (completed)
- [▶] security-analyzer (in progress)
- [ ] sidekiq-specialist (pending)

### Findings Summary
- Patterns: [key findings]
- Schema: [key findings]
- Security: [awaiting]
- Jobs: [pending]
```

## Plan-Task Annotations Cross-Reference

Set A annotations (`[direct]`, `[active record]`, `[hotwire]`, `[sidekiq]`,
`[concurrency]`, `[security]`, `[test]`) are already canonicalized earlier
in this file under "Key requirements" (the `[Pn-Tm][annotation]` task
format checklist). That earlier section is the canonical source — do
NOT duplicate the list here.

NOTE: `work/SKILL.md` uses shorter domain labels (`[grape]`, `[ar]`,
`[sequel]`, `[perf]`, `[ruby]`) only as descriptive narrative — those
are NOT plan-task annotations and must not appear in plan checkboxes.
Use the Set A list documented earlier in this file for all
`[Pn-Tm][annotation]` entries.

## Plan Template (inline this when writing plan.md)

```markdown
# Plan: {Feature Name}

## Overview
**Goal**: {one sentence}
**Scope**: {boundaries}
**Risk Level**: {low/medium/high}
**Estimated Effort**: {N} tasks, {N} hours

## Research Findings
{summary of agent findings — synthesized directly from per-agent research artifacts}

## Design Decisions
{key choices with rationale}

## Tasks

### Phase 1: Foundation
- [ ] [P1-T1][active record] {task} → verify: {how}

### Phase 2: Implementation
- [ ] [P2-T1][direct] {task} → verify: {how}

### Phase 3: Verification
- [ ] [P3-T1][test] Run zeitwerk:check → verify: clean output
- [ ] [P3-T2][test] Run formatter/linter → verify: zero issues
- [ ] [P3-T3][test] Run test suite → verify: all green
- [ ] [P3-T4][security] Run brakeman → verify: no new findings

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| {risk} | {L/M/H} | {L/M/H} | {strategy} |
```

## Common Planning Pitfalls

- **over-planning**: too many tasks, too much implementation detail
- **under-planning**: missing verification or risk coverage
- **wrong agents**: missing security/jobs/schema specialists
- **ignoring context**: not reading existing code before decomposing work
