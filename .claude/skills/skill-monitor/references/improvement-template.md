# Skill Improvement Analysis Template

Template for the skill-effectiveness-analyzer agent. Produces
actionable recommendations for improving underperforming skills.

## Inputs

1. **Aggregated metrics** — per-skill dashboard data
2. **Flagged skills** — skills below effectiveness thresholds
3. **Session IDs** — sessions where skills had friction outcomes
4. **Session reports** (if available) — qualitative analysis from deep-dive

## Analysis Sections

### 1. Executive Summary

One paragraph: how many skills analyzed, how many flagged, overall
plugin health trend.

### 2. Per-Skill Analysis

For each flagged skill:

```markdown
## /rb:{skill} — Effectiveness: {score}

**Status**: {Needs improvement | Critical | Watch}
**Evidence strength**: {STRONG | MODERATE | WEAK}

### Failure Pattern

Describe the dominant failure mode:
- What goes wrong when this skill underperforms?
- At what stage does friction occur?
- Is it a skill design issue, agent behavior issue, or user expectation mismatch?

### Supporting Data

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Action rate | 0.45 | > 0.7 | BELOW |
| Avg post-errors | 2.3 | < 1.0 | ABOVE |
| Avg post-corrections | 1.1 | < 0.5 | ABOVE |
| Friction outcome % | 40% | < 30% | ABOVE |

### Session Evidence

| Session | Date | Project | Outcome | Key Signal |
|---------|------|---------|---------|------------|
| abc123 | 2026-02-28 | myapp | friction | 4 corrections after review |
| def456 | 2026-03-01 | myapp | no_action | Review output ignored |

### Root Cause Hypothesis

{Specific hypothesis about WHY the skill underperforms}

Examples:
- "Review agent flags too many low-severity issues, causing fatigue"
- "Investigation skill doesn't check compound solutions first"
- "Plan tasks are too granular for simple features"
- "Skill prompt doesn't handle edge case X"

### Recommended Changes

1. **{Change type}**: {Description}
   - File: `{path to skill or agent file}`
   - What: {specific change}
   - Expected impact: {how this improves effectiveness}
   - Evidence: {session IDs supporting this}

Change types:
- SKILL_PROMPT — Modify skill SKILL.md instructions
- AGENT_PROMPT — Modify agent system prompt
- IRON_LAW — Add new Iron Law to prevent pattern
- REFERENCE — Update or add reference documentation
- HOOK — Add/modify hook behavior
- WORKFLOW — Change skill interaction/ordering
```

### 3. Cross-Skill Patterns

Patterns that affect multiple skills:

| Pattern | Affected Skills | Impact | Fix |
|---------|----------------|--------|-----|
| Over-verbose output | review, plan | Information fatigue | Add output length limits |
| Missing context handoff | plan → work | Rework on transition | Add scratchpad passing |

### 4. Positive Patterns

What's working well — don't break these:

| Skill | Strength | Why It Works |
|-------|----------|--------------|
| /rb:compound | High action rate | Clear schema, minimal friction |
| /rb:plan | Good completion | Checkbox format enables tracking |

### 5. Priority Ranking

Ordered by: evidence_strength × impact × ease_of_fix

| # | Skill | Change | Evidence | Impact | Effort | Priority |
|---|-------|--------|----------|--------|--------|----------|
| 1 | /rb:review | Reduce false positives | STRONG (5 sessions) | High | Low | P0 |
| 2 | /rb:investigate | Add solution search | MODERATE (3 sessions) | High | Medium | P1 |

### 6. Tracking Plan

How to verify improvements after changes:

```
1. Apply recommended changes
2. Run /session-scan --rescan after 5+ sessions
3. Run /skill-monitor --window 7d
4. Compare effectiveness scores to this report's baseline
5. If improved: continue monitoring
   If not: run /skill-monitor --improve for new analysis
```

## Output Format

Write as structured markdown to:
`.claude/skill-metrics/recommendations-{date}.md`

Keep under 200 lines. Every recommendation must cite specific
sessions and metrics. Include tracking plan so improvements
can be verified.

## Anti-Patterns

- **Don't recommend adding complexity** to fix simplicity issues
- **Don't suggest new skills** when existing ones need fixing
- **Don't blame the user** — if corrections are high, the skill
  is misleading, not the user
- **Don't recommend changes without evidence** — every change
  needs session citations
