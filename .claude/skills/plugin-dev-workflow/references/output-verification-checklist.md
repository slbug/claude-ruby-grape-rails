# Output Verification Checklist

Use this checklist when a contributor changes research/review verification
workflows, the `output-verifier` agent, or the `lab/eval` output-artifact
checks.

## Shipped Contract vs Contributor Checks

- shipped plugin contract:
  - [`plugins/ruby-grape-rails/references/output-verification/provenance-template.md`](../../../../plugins/ruby-grape-rails/references/output-verification/provenance-template.md)
- contributor-only validation:
  - `make eval-output`
  - `npm run eval:output`
  - tracked fixtures under
    [`lab/eval/fixtures/output/`](../../../../lab/eval/fixtures/output/)

Keep those surfaces separate.

## Research Artifact Expectations

- include a top-level heading
- include `Date:` or `Last Updated:` metadata
- include a `## Sources` section
- mark source tiers explicitly in the sources list
- use inline `[T1]` / `[T2]` / `[T3]` markers for important external claims
- include a decision-oriented section such as:
  - `## Summary`
  - `## Recommendation`
  - `## Risks`
  - `## Quick Facts`

## Review Artifact Expectations

- use the consolidated review contract in
  [`plugins/ruby-grape-rails/skills/review/references/review-template.md`](../../../../plugins/ruby-grape-rails/skills/review/references/review-template.md)
- include a verdict line
- cite findings with `file:line`
- keep review artifacts findings-only
- do not add task lists to the review artifact itself
- keep the mandatory at-a-glance finding table

## Provenance Sidecar Expectations

- follow the shipped
  [`provenance-template.md`](../../../../plugins/ruby-grape-rails/references/output-verification/provenance-template.md)
- always include:
  - artifact pointer
  - summary counts
  - source tier summary
  - claim log
  - required fixes
- prefer local code evidence for review findings
- prefer T1/T2 sources for research claims
- T4/T5 evidence is allowed in claim logs when it explains why a source was
  treated as weak or rejected, but the summary line should stay focused on
  T1/T2/T3
- soften or remove unsupported claims instead of leaving them implicit

## Contributor Validation

Run:

- `make eval-output` or `npm run eval:output`
- `python3 -m unittest discover -t . -s lab/eval/tests -p 'test_*.py' -v`
