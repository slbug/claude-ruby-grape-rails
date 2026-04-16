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
