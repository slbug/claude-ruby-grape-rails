# Provenance Template

Use this structure for research and review provenance sidecars.

Preferred paths:

- research:
  - `.claude/research/{topic-slug}.provenance.md`
  - `.claude/plans/{slug}/research/{topic-slug}.provenance.md`
- review:
  - `.claude/reviews/{review-slug}.provenance.md`

```markdown
# Provenance: {artifact-name}

**Artifact**: `{artifact-path}`
**Verified**: {count}
**Unsupported**: {count}
**Conflicts**: {count}
**Weakly sourced**: {count}
**Source Tiers**: T1:{count} T2:{count} T3:{count}

## Claim Log

1. [VERIFIED] "{claim}"
   - Evidence: {path/to/file.rb:line}
   - Notes: {why the local code proves the claim}

2. [UNSUPPORTED] "{claim}"
   - Evidence: {paths or URLs checked}
   - Notes: {why it should be removed or softened}

3. [CONFLICT] "{claim}"
   - Evidence: <https://example.com/source> [T1]
   - Notes: {what disagrees and which source is stronger}

## Required Fixes

- {claim to remove, soften, or re-cite}
```

## Notes

- Use `file:line` evidence for review findings proven directly by local code.
- Use URL + source tier for external research claims.
- Keep `Required Fixes` even when the answer is "None." The section should
  always exist.
- `Source Tiers` is currently summarized as `T1`, `T2`, and `T3` because Ruby
  research guidance treats `T4/T5` as too weak for decisive recommendations.
