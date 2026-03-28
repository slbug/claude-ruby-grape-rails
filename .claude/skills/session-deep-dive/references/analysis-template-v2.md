# Session Analysis Template v2

Analyze one contributor session transcript and produce a structured report.

You have:

- the full transcript
- pre-computed heuristic metrics from `/session-scan`

Your job is to validate, refine, or contradict those heuristics with transcript
evidence.

## Ground Rules

1. Do not overclaim from one session.
2. Every finding must carry an evidence-strength tag.
3. If a metric looks wrong, say so explicitly.

## Evidence Strength Tags

- `STRONG`: direct evidence or repeated pattern
- `MODERATE`: plausible pattern with limited evidence
- `WEAK`: inference only

## Sections

### 1. Session Summary

- What was the contributor trying to do?
- Single task or multi-task?
- Outcome:
  - fully successful
  - partially successful
  - unresolved
- Which Ruby-plugin surfaces were involved:
  - skills
  - agents
  - hooks
  - docs / release metadata
- Does the reported fingerprint fit the session?

### 2. Correction Tracking

Enumerate explicit user corrections or redirections.

| # | User Said | What Went Wrong | Impact |
|---|-----------|-----------------|--------|
| 1 | "No, use the shipped hook file" | Scope drift into contributor-only code | 3 wasted tool calls |

### 3. Workflow Preferences

Identify contributor preferences visible in the session:

- plan-first vs direct implementation
- small patches vs broad rewrites
- test/validation-first vs patch-first
- terse vs detailed close-out
- evidence-heavy review vs quick approval
- prefers `rg` / `jq` / shell vs ad-hoc scripting

Only record preferences with actual transcript support.

### 4. How the Work Happened

- did the contributor stay on one problem or bounce between tasks?
- was the workflow read-first, patch-first, or tool-first?
- were subagents used effectively?
- did runtime tooling appear?
  - Tidewave
  - browser or HTTP helpers
  - DB query helpers
- what does the tool mix imply?

### 5. Friction Points

For each meaningful friction point:

| # | Type | Description | Evidence | Strength |
|---|------|-------------|----------|----------|
| 1 | error_loop | repeated hook-schema fix attempts | shell output + edits | STRONG |

Suggested types:

- `error_loop`
- `approach_change`
- `manual_repetition`
- `scope_creep`
- `missing_context`
- `tool_confusion`
- `manual_verification`

### 6. Plugin Skill Assessment

#### Used Commands

If `/rb:*` commands were used:

| Command | Helped? | Issues? |
|---------|---------|---------|
| `/rb:plan` | yes | over-detailed for a tiny task |

#### Suggested Commands

Only suggest a command if the transcript evidence is clear.

| Friction Point | Suggested Command | Why | Strength |
|----------------|-------------------|-----|----------|
| repeated manual verification | `/rb:verify` | structured verification pass | STRONG |

#### Hook and Workflow Assessment

- did hook output help or create noise?
- were checks ignored for a good reason or because they were weak?
- did the workflow rely on stale contributor assumptions?

### 7. Improvement Opportunities

For each real opportunity:

```text
[STRENGTH] Category: description
Evidence: concrete transcript evidence
Confidence: high / medium / low
Suggested change: specific file or workflow change
Corroboration needed: what should be checked next
```

Good categories:

- missing automation
- stale contributor guidance
- docs-check false positive
- workflow friction
- evaluation blind spot
- tool taxonomy drift

### 8. Overall Assessment

Rate the session:

- smooth
- some friction
- high friction
- misleading signals

Then estimate whether the current plugin helped, hurt, or was mostly irrelevant.
