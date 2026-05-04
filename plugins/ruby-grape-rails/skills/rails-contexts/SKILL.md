---
name: rails-contexts
description: "Use when deciding where business logic belongs in Rails: controllers, services, forms, queries, policies, serializers, and mounted Grape APIs."
when_to_use: "Triggers: \"where does this go\", \"service object\", \"form object\", \"query object\", \"policy\", \"serializer\"."
user-invocable: false
effort: medium
---
# Rails Contexts

## Iron Laws

1. Controllers translate HTTP; they do not own business rules.
2. Model callbacks should not silently trigger external side effects.
3. Policy and authorization checks must be explicit at boundaries.
4. Service, query, and form objects should clarify ownership, not add ceremony for its own sake.

## Good Rails Boundaries

- controller or endpoint for transport concerns
- application service or command for workflow orchestration
- query object when a query grows beyond a scope or two
- policy object for authorization rules
- job only for deferred or async work

## References

| Need | Reference |
|---|---|
| service / form / query / policy / serializer placement | `${CLAUDE_SKILL_DIR}/references/context-patterns.md` |
| strong-params discipline | `${CLAUDE_SKILL_DIR}/references/strong-params.md` |
| routing / namespacing / engine boundaries | `${CLAUDE_SKILL_DIR}/references/routing-patterns.md` |
| JSON / API controller, serializer, JSON:API, JWT auth | `${CLAUDE_SKILL_DIR}/references/json-api-patterns.md` |
| middleware + before-action filter patterns | `${CLAUDE_SKILL_DIR}/references/middleware-before-action-patterns.md` |
| Pundit / CanCanCan + manual authorization + multi-tenant scopes | `${CLAUDE_SKILL_DIR}/references/scopes-auth.md` |
