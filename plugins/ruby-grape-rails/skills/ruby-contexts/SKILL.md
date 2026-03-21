---
name: ruby-contexts
description: General Ruby application boundaries outside framework glue. Load for service layers, command objects, adapters, value objects, and integration seams.
user-invocable: false
---

# Ruby Contexts

## Principles

- one object should have one reason to change
- boundary objects should make side effects obvious
- integration points should be wrapped behind project-owned APIs
- avoid framework leakage in plain Ruby business code where practical
