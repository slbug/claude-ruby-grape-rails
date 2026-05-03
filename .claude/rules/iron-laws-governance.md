---
paths: "**/iron-laws.yml"
---

# Iron Laws Governance

## Audience: Agents, Not Humans

Imperative-only. Match existing schema, regenerate downstream
artifacts, attach incident provenance.

## When to Add a New Iron Law

All three MUST hold:

1. Reproducible incident occurred **at least twice** (same root cause, different times or codebases).
2. Existing laws do not cover the failure mode.
3. Deterministic detector / review-time check exists, OR rule is non-negotiable enough that every contributor agrees.

Do NOT add when:

| Trigger | Wrong because |
|---|---|
| another plugin has a similar rule | symmetry is not evidence |
| single dramatic incident | one-shot ≠ pattern |
| feels dangerous, no reproduced damage | not provenance |
| contributor style preference | belongs in `preferences.yml` |

## When to Remove or Demote

| Action | Trigger |
|---|---|
| Remove | underlying failure mode impossible (API removed upstream) |
| Demote to `preferences.yml` | incidents stop recurring for two release cycles AND rule generates false positives |

## Update Procedure

1. Edit `plugins/ruby-grape-rails/references/iron-laws.yml`.
2. Run `bash scripts/generate-iron-law-outputs.sh all`.
3. Confirm drift check + lint pass.
4. Include incident references (issue / PR / ticket) in the commit or CHANGELOG entry — provenance is traceable.
