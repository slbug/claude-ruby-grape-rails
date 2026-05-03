# Skill Improvement Analysis Template

## Audience: Agents, Not Humans

Imperative-only.

## Inputs

1. aggregated dashboard metrics
2. flagged skills
3. session IDs
4. matching session-analysis reports
5. corroborating deterministic signals (if available)

## Sections

### 1. Executive Summary

State:

- how many skills reviewed
- how many flagged
- overall confidence level
- whether conclusions are transcript-only or corroborated

### 2. Per-Skill Analysis

For each flagged skill:

```markdown
## /rb:{skill}

**Status**: {Watch | Needs improvement | High priority}
**Confidence**: {High | Medium | Low}

### What the dashboard shows

| Metric | Value | Notes |
|--------|-------|-------|
| Action rate | 0.45 | low follow-through |
| Avg post-errors | 2.3 | visible friction after use |
| Avg post-corrections | 1.1 | contributor redirects often |
| Dominant outcome | friction | heuristic only |

### Confounders

- small sample?
- mixed providers?
- unusually hard sessions?
- stale docs or schema drift rather than skill quality?

### Session Evidence

| Session | Date | Outcome | Key evidence |
|---------|------|---------|--------------|

### Corroboration

- `lab/eval`: {supports / does not support / not checked}
- docs-check: {supports / does not support / not checked}
- manual transcript review: {supports / does not support / not checked}

### Recommended Change

1. **Type**: {SKILL_PROMPT | AGENT_PROMPT | IRON_LAW | REFERENCE | WORKFLOW}
   - File: `{path}`
   - Change: {specific change}
   - Why: {link to evidence}
   - Expected outcome: {what should improve}
```

### 3. Cross-Skill Patterns

Multiple skills show same issue → capture once:

| Pattern | Skills | Evidence | Confidence | Fix direction |
|---------|--------|----------|------------|---------------|

### 4. Positive Patterns

List what appears to work — prevents accidental regression.

### 5. Priority Ranking

Order by:

- evidence quality
- likely impact
- ease of verification

### 6. Tracking Plan

Follow-up plan order:

1. deterministic validation (`lab/eval`, docs-check, plugin validate)
2. targeted transcript review
3. rescan to see whether observational signals moved

## Anti-Patterns

- Do NOT recommend changes from one weak session alone.
- Do NOT present observational data as causal proof.
- Do NOT suggest new skills when likely issue is stale guidance or bad routing.
