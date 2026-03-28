# Cross-Session Synthesis Template

Synthesize multiple session-analysis reports into a cautious, evidence-backed
summary.

## Inputs

Use only real inputs that exist:

1. per-session analysis reports
2. previous synthesis reports, if present
3. contributor-supplied notes via `--compare`, if present
4. recent deterministic signals such as `lab/eval`, when relevant

Do not depend on `MEMORY.md` or old local report artifacts that are not tracked.

## Sections

### 1. Repeated Patterns

Patterns that appear again in the new set.

| Pattern | Sessions | Evidence | Strength |
|---------|----------|----------|----------|
| stale docs-check guidance | 3 | report citations | STRONG |

### 2. New Patterns

Patterns not seen in earlier synthesis notes or not previously tracked.

| Pattern | Sessions | Evidence | Strength |
|---------|----------|----------|----------|

Require either:

- at least 2 sessions, or
- 1 session with unusually strong direct evidence

### 3. Resolved or Weakened Patterns

Patterns previously reported that no longer appear or appear much less often.

| Pattern | Previous Evidence | Current Evidence | Interpretation |
|---------|-------------------|------------------|----------------|

### 4. Corroboration

For each important cross-session claim, state whether it is corroborated by:

- `lab/eval`
- docs-check findings
- deterministic plugin validation
- transcript evidence only

Use this section to prevent observational claims from sounding stronger than
they are.

### 5. Recommendations

Maximum 5 recommendations, ordered by evidence strength and likely impact.

| # | Recommendation | Evidence | Confidence | Effort |
|---|----------------|----------|------------|--------|

### 6. Follow-Up Notes

If the contributor should update a tracked note, say which one. If no tracked
note is appropriate, say so explicitly instead of inventing a memory file.

## Output Rules

1. Every material claim must cite specific session reports.
2. Mark purely observational claims as such.
3. Keep the report concise and action-oriented.
