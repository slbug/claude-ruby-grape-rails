---
paths: "**/iron-laws.yml"
---

# Iron Laws Governance

## When to Add a New Iron Law

Add a new Iron Law **only** when:

1. A real, reproducible incident has occurred **at least twice** (same root
   cause, different times or different codebases).
2. Existing laws do not already cover the failure mode.
3. A deterministic detector or review-time check can be written, OR the
   behavioral trigger is strong enough that every contributor agrees the
   rule is non-negotiable.

Do **not** add a law because:

- Another plugin or framework has a similar rule (symmetry is not evidence).
- A single dramatic incident happened once.
- A pattern feels dangerous but nobody has reproduced damage from it.
- A contributor prefers a style — preferences belong in `preferences.yml`,
  not `iron-laws.yml`.

## When to Remove or Demote a Law

- Remove if the underlying failure mode becomes impossible (e.g., API
  removed upstream).
- Demote to `preferences.yml` (advisory) if incidents stop recurring for
  two release cycles and the rule starts generating false positives.

## Update Procedure

1. Edit `plugins/ruby-grape-rails/references/iron-laws.yml` with the new
   or changed law.
2. Run `bash scripts/generate-iron-law-outputs.sh all`.
3. Confirm drift check + lint pass.
4. Include incident references (issue/PR/ticket) in the commit or
   CHANGELOG entry so the "repeated real incident" provenance is
   traceable.
