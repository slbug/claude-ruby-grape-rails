# Cross-Session Synthesis Template

## Audience: Agents, Not Humans

Imperative-only.

## Inputs

Use only real inputs that exist:

1. per-session analysis reports
2. previous synthesis reports (if present)
3. contributor-supplied notes via `--compare` (if present)
4. recent deterministic signals (`lab/eval`) when relevant

Do NOT depend on `MEMORY.md` or untracked old local report artifacts.

## Sections

### 1. Repeated Patterns

Patterns that appear again in the new set:

| Pattern | Sessions | Evidence | Strength |
|---------|----------|----------|----------|
| stale docs-check guidance | 3 | report citations | STRONG |

### 2. New Patterns

Patterns not in earlier synthesis notes / not previously tracked:

| Pattern | Sessions | Evidence | Strength |
|---------|----------|----------|----------|

Required: ≥ 2 sessions OR 1 session with unusually strong direct evidence.

### 3. Resolved or Weakened Patterns

Patterns previously reported that no longer appear or appear less often:

| Pattern | Previous Evidence | Current Evidence | Interpretation |
|---------|-------------------|------------------|----------------|

### 4. Corroboration

Per important cross-session claim, state corroboration source:

- `lab/eval`
- docs-check findings
- deterministic plugin validation
- transcript evidence only

Prevents observational claims from sounding stronger than they are.

### 5. Recommendations

Maximum 5, ordered by evidence strength + likely impact:

| # | Recommendation | Evidence | Confidence | Effort |
|---|----------------|----------|------------|--------|

### 6. Follow-Up Notes

Contributor should update a tracked note → name it. No tracked note
appropriate → state so explicitly. Do NOT invent a memory file.

## Output Rules

1. Every material claim cites specific session reports.
2. Mark purely observational claims as such.
3. Keep report concise + action-oriented.
