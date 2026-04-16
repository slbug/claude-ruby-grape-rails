---
name: grape-idioms
description: "Use when building Grape APIs: endpoint design, param coercion, declared params, versioning, error handling, grape-entity presentation, and Rails integration."
when_to_use: "Triggers: \"Grape\", \"API endpoint\", \"grape-entity\", \"API versioning\", \"param coercion\"."
user-invocable: false
effort: medium
paths:
  - "app/{api,apis,resources,representers,serializers,blueprints,endpoints,deserializers}/**"
  - "**/app/{api,apis,resources,representers,serializers,blueprints,endpoints,deserializers}/**"
  - "{packs,engines,components}/*/{api,apis,resources,representers,serializers,blueprints,endpoints,deserializers}/**"
  - "app/{packages,packs}/*/{api,apis,resources,representers,serializers,blueprints,endpoints,deserializers}/**"
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
