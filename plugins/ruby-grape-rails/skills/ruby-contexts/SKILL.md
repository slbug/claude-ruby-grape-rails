---
name: ruby-contexts
description: "Use when designing Ruby application boundaries: service layers, command objects, adapters, value objects, and integration seams outside framework glue."
when_to_use: "Triggers: \"service layer\", \"command object\", \"adapter\", \"value object\", \"plain Ruby\"."
user-invocable: false
effort: medium
---
# Ruby Contexts

## Principles

- one object should have one reason to change
- boundary objects should make side effects obvious
- integration points should be wrapped behind project-owned APIs
- avoid framework leakage in plain Ruby business code where practical
