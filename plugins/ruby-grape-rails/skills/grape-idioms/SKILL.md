---
name: grape-idioms
description: Grape API patterns for versioning, param coercion, declared params, error handling, presentation, and Rails integration. Load for mounted APIs and request boundary design.
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
