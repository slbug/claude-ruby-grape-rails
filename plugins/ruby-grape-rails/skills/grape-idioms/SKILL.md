---
name: grape-idioms
description: "Grape APIs: endpoint design, param coercion, versioning, grape-entity. Triggers: \"API versioning\", \"param coercion\", \"endpoint design\", \"Grape::Entity\". Do NOT use for: Rails controllers."
user-invocable: false
effort: medium
---
# Grape Idioms

## Iron Laws

1. Define input contracts in `params do`.
2. Use `declared(params, include_missing: false)` or equivalent explicit shaping before passing data inward.
3. Keep endpoints thin and push business rules into application code.
4. Standardize error envelopes and auth behavior per version.

## Good Defaults

- namespaced versioning
- `rescue_from` for predictable API errors
- presenters/entities only when they clarify response shape
- request specs for transport behavior

## References

| Need | Reference |
|---|---|
| declared params, versioning, entities, mounted-API patterns, error envelopes, JWT/OAuth auth, Rails integration | `${CLAUDE_SKILL_DIR}/references/grape-patterns.md` |
| JSON API patterns (Rails-side overlap) | `${CLAUDE_PLUGIN_ROOT}/skills/rails-contexts/references/json-api-patterns.md` |
