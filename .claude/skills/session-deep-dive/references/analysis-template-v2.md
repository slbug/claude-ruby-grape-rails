# Session Analysis Template v2

## Audience: Agents, Not Humans

Imperative-only.

Inputs:

- full transcript
- pre-computed heuristic metrics from `/session-scan`

Validate, refine, or contradict heuristics with transcript evidence.

## Ground Rules

1. Do NOT overclaim from one session.
2. Every finding carries an evidence-strength tag.
3. Wrong-looking metric → state it explicitly.

## Evidence Strength Tags

| Tag | Meaning |
|---|---|
| `STRONG` | direct evidence or repeated pattern |
| `MODERATE` | plausible pattern with limited evidence |
| `WEAK` | inference only |

## Sections

### 1. Session Summary

- contributor's goal
- single task or multi-task?
- outcome: fully successful / partially successful / unresolved
- Ruby-plugin surfaces involved: skills, agents, hooks, docs / release metadata
- does the reported fingerprint fit the session?

### 2. Correction Tracking

Enumerate explicit user corrections / redirections:

| # | User Said | What Went Wrong | Impact |
|---|-----------|-----------------|--------|
| 1 | "No, use the shipped hook file" | scope drift into contributor-only code | 3 wasted tool calls |

### 3. Workflow Preferences

Record contributor preferences visible in the session:

- plan-first vs direct implementation
- small patches vs broad rewrites
- test/validation-first vs patch-first
- terse vs detailed close-out
- evidence-heavy review vs quick approval
- prefers `Grep` / `Glob`, `ag` / `rg`, `jq`, shell vs ad-hoc scripting

Only record preferences with actual transcript support.

### 4. How the Work Happened

- stayed on one problem or bounced between tasks?
- workflow read-first, patch-first, or tool-first?
- subagents used effectively?
- runtime tooling appeared? (Tidewave, browser/HTTP helpers, DB query helpers)
- what does the tool mix imply?

### 5. Friction Points

Per friction point:

| # | Type | Description | Evidence | Strength |
|---|------|-------------|----------|----------|
| 1 | error_loop | repeated hook-schema fix attempts | shell output + edits | STRONG |

Suggested types: `error_loop`, `approach_change`, `manual_repetition`, `scope_creep`, `missing_context`, `tool_confusion`, `manual_verification`.

### 6. Plugin Skill Assessment

#### Used Commands

`/rb:*` commands used:

| Command | Helped? | Issues? |
|---------|---------|---------|
| `/rb:plan` | yes | over-detailed for a tiny task |

#### Suggested Commands

Only suggest a command when transcript evidence is clear:

| Friction Point | Suggested Command | Why | Strength |
|----------------|-------------------|-----|----------|
| repeated manual verification | `/rb:verify` | structured verification pass | STRONG |

#### Hook and Workflow Assessment

- did hook output help or create noise?
- were checks ignored for good reason or because they were weak?
- did workflow rely on stale contributor assumptions?

### 7. Improvement Opportunities

Per real opportunity:

```text
[STRENGTH] Category: description
Evidence: concrete transcript evidence
Confidence: high / medium / low
Suggested change: specific file or workflow change
Corroboration needed: what should be checked next
```

Categories: missing automation, stale contributor guidance, docs-check
false positive, workflow friction, evaluation blind spot, tool taxonomy
drift.

### 8. Overall Assessment

Rate the session: smooth / some friction / high friction / misleading signals.

Estimate whether the current plugin helped, hurt, or was mostly irrelevant.
