# Output Verification Checklist

## Audience: Agents, Not Humans

Imperative-only. Use when changing research/review verification
workflows, the `output-verifier` agent, or `lab/eval` output-artifact
checks.

## Shipped Contract vs Contributor Checks

| Layer | Path |
|---|---|
| shipped plugin contract | [`plugins/ruby-grape-rails/references/output-verification/provenance-template.md`](../../../../plugins/ruby-grape-rails/references/output-verification/provenance-template.md) |
| contributor-only validation | `make eval-output`, `npm run eval:output` |
| tracked fixtures | [`research-good.md`](../../../../lab/eval/fixtures/output/research-good.md), [`research-bad.md`](../../../../lab/eval/fixtures/output/research-bad.md), [`review-good.md`](../../../../lab/eval/fixtures/output/review-good.md), [`review-bad.md`](../../../../lab/eval/fixtures/output/review-bad.md) |

Keep these surfaces separate.

## Research Artifact Expectations

- top-level heading
- `Date:` or `Last Updated:` metadata
- `## Sources` section
- explicit source tier marks in sources list
- inline `[T1]` / `[T2]` / `[T3]` markers for important external claims
- decision-oriented section: `## Summary` / `## Recommendation` / `## Risks` / `## Quick Facts`

## Review Artifact Expectations

- consolidated review contract from [`plugins/ruby-grape-rails/skills/review/references/review-template.md`](../../../../plugins/ruby-grape-rails/skills/review/references/review-template.md)
- verdict line
- findings cite `file:line`
- review artifacts stay findings-only
- NO task lists in the review artifact itself
- NO `## Next Steps` or follow-up planning sections in the review artifact itself
- mandatory at-a-glance finding table

## Provenance Sidecar Expectations

- follow shipped [`provenance-template.md`](../../../../plugins/ruby-grape-rails/references/output-verification/provenance-template.md)
- always include:
  - artifact pointer
  - summary counts
  - source tier summary
  - claim log
  - required fixes
- prefer local code evidence for review findings
- prefer T1/T2 sources for research claims
- T4/T5 evidence allowed in claim logs to explain why a source was treated as weak / rejected; summary line stays focused on T1/T2/T3
- soften or remove unsupported claims — do NOT leave them implicit

## Contributor Validation

Run:

- `make eval-output` or `npm run eval:output`
- `python3 -m unittest discover -t . -s lab/eval/tests -p 'test_*.py' -v`
