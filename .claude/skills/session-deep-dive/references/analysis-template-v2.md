# Session Analysis Template v2

Analyze this Claude Code session transcript and produce a structured report.
You have both pre-computed quantitative metrics AND the full transcript.

## Goals

1. **Validate metrics** — do the pre-computed scores match the qualitative reality?
2. **Add depth** — identify specific friction moments, user preferences, workflow patterns
3. **Assess plugin fit** — which commands/skills would help, which wouldn't?
4. **Tag evidence** — every finding must have a strength tag

## Evidence Strength Tags

Tag every finding with one of:

- **STRONG**: Direct evidence (user complained, explicit error, 3+ occurrences)
- **MODERATE**: Indirect evidence (pattern suggests friction, 1-2 occurrences)
- **WEAK**: Inference only (could be interpreted differently)

## Analysis Sections

### 1. Session Summary

- What was the developer trying to accomplish?
- Single task or multiple tasks?
- Success level: fully, partially, not at all?
- Ruby/Rails/Grape domains touched (Hotwire/Turbo, Active Record, Sidekiq, etc.)?
- Does the fingerprint from metrics match your assessment?

### 2. User Correction Tracking

Enumerate every user correction or redirection:

| # | User Said | What Went Wrong | Impact |
|---|-----------|-----------------|--------|
| 1 | "no, I meant..." | Claude misunderstood scope | Wasted 5 tool calls |

This directly validates the `user_corrections` friction signal.

### 3. Decision Preferences

Identify code style and workflow preferences:

- Pattern matching vs if/else/cond?
- `with` chains vs nested `case`?
- Test-first vs implementation-first?
- Inline vs extracted functions?
- Prefers detailed explanations or terse responses?
- How they handle review findings (fix all vs selective)?

### 4. How They Worked

- Planned before coding or dove straight in?
- Iterative cycle pattern (edit → test → fix → test)?
- Used subagents or worked solo?
- Debugging approach (read-first vs trial-and-error)?
- Used runtime tooling? (project_eval, browser_eval, execute_sql_query)
- Tool mix interpretation (Read-heavy = exploration, Edit-heavy = implementation)

### 5. Friction Points

For each friction point found:

| # | Type | Description | Evidence | Strength |
|---|------|-------------|----------|----------|
| 1 | Error loop | rails zeitwerk:check failed 4× | Bash calls 23-27 | STRONG |
| 2 | Approach change | Switched from inline job to Sidekiq | Edits 15-20 | MODERATE |

Types: error_loop, approach_change, manual_repetition, long_debugging,
scope_creep, missing_context, tool_confusion

### 6. Plugin Skills Assessment

#### Used Commands

If any `/rb:*` commands were used:

| Command | Worked Well? | Issues? |
|---------|-------------|---------|
| `/rb:plan` | Yes — kept scope focused | Plan was too detailed for small task |

#### Suggested Commands

For each friction point, suggest a specific plugin command:

| Friction Point | Suggested Command | Why It Helps | Strength |
|----------------|-------------------|-------------|----------|
| Error loop (#1) | `/rb:investigate` | Structured 4-track analysis | STRONG |

Only suggest commands that genuinely match. Don't force-fit.

#### Hook Effectiveness

- Did PostToolUse verification fire? (rails zeitwerk:check + rubocop after edits)
- Was the security Iron Laws reminder shown for auth files?
- Did the developer heed or ignore hook output?

### 7. Plugin Improvement Opportunities

Most important section. For each opportunity:

```
**[STRONG/MODERATE/WEAK] {Category}: {Description}**

Evidence: {specific messages, commands, patterns from transcript}
Session count estimate: {how many other sessions likely have this}
Suggested implementation: {concrete suggestion}
```

Categories:

- Missing automation
- Missing Iron Law
- Missing skill/agent
- Auto-loading gap
- Workflow friction WITH plugin
- Tool integration gap

### 8. Efficiency Assessment

Rate: **Smooth** / **Some friction** / **High friction** / **Abandoned**

Estimate effort savings with right plugin skills: {X}%

## Output Format

Write structured markdown with all sections above.
Keep under 200 lines. Be concrete — cite actual messages, commands, patterns.
Every finding must have an evidence strength tag.
