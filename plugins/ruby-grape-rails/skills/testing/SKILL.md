---
name: testing
description: Testing patterns for Ruby, Rails, Grape, and Sidekiq. Load for request specs, model/service tests, worker tests, factories, and anti-flake practices.
user-invocable: false
paths:
  - spec/**
  - test/**
  - "**/spec/**"
  - "**/test/**"
effort: medium
---
# Testing

## Good Defaults

- request specs or API tests for transport behavior
- focused unit tests for service/query objects
- worker tests for enqueue and perform paths
- factories or fixtures that stay small and deterministic
- explicit time and randomness control in flaky paths
