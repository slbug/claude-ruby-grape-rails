# Cross-Session Synthesis Template

Synthesize findings from multiple session analysis reports into a
trend-aware summary that compares against known patterns.

## Inputs

1. **Per-session reports** (from analysis-template-v2)
2. **Previous synthesis report** (for trend comparison)
3. **MEMORY.md** (for known findings baseline)

## Synthesis Sections

### 1. Confirmed Patterns

Patterns seen in previous reports/MEMORY.md that are still present.

| Pattern | Previous Count | New Count | Total | Trend |
|---------|---------------|-----------|-------|-------|
| Zero skill auto-loading | 137 | +5 | 142 | Stable |
| PR review workflow demand | 9 | +2 | 11 | Growing |

Only include patterns with STRONG or MODERATE evidence in new sessions.

### 2. New Patterns

Patterns not found in previous reports or MEMORY.md.

| Pattern | Sessions | Evidence | Strength |
|---------|----------|----------|----------|
| {new finding} | 3 | {citations} | STRONG |

Require at least 2 sessions OR 1 session with STRONG evidence.

### 3. Resolved Patterns

Previously noted patterns with no new occurrences.

| Pattern | Last Seen | Sessions Since | Status |
|---------|-----------|----------------|--------|
| {old issue} | 2026-01-15 | 12 | Likely resolved |

### 4. Actionable Recommendations

Max 5 recommendations, ordered by evidence strength × impact.

| # | Recommendation | Evidence | Impact | Effort |
|---|----------------|----------|--------|--------|
| 1 | {what to do} | {N sessions, strength} | High | Low |

Each recommendation must cite specific sessions and evidence.

### 5. Updated Statistics

| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Total sessions analyzed | 160 | 165 | +5 |
| Avg friction score | 0.22 | 0.24 | +0.02 |
| Plugin adoption rate | 8% | 10% | +2% |
| Tier 2 eligible rate | 30% | 28% | -2% |
| Most common fingerprint | bug-fix | bug-fix | — |

### 6. MEMORY.md Update Suggestions

List specific edits to MEMORY.md based on findings:

- **Add**: {new confirmed pattern to add}
- **Update**: {existing entry with new data}
- **Remove**: {pattern that appears resolved}

## Output Format

Write as structured markdown. Every claim must cite sessions.
Keep under 150 lines. Focus on actionable, evidence-backed findings.
