---
name: testing
description: "Use when writing tests for Ruby, Rails, Grape, or Sidekiq: request specs, model/service tests, factories, fixtures, minitest, and anti-flake practices."
when_to_use: "Triggers: \"test\", \"RSpec\", \"spec\", \"factory\", \"fixture\", \"minitest\", \"flaky test\"."
user-invocable: false
paths:
  - "{spec,test}/**"
  - "**/{spec,test}/**"
effort: medium
---
# Testing

## Good Defaults

- request specs or API tests for transport behavior
- focused unit tests for service/query objects
- worker tests for enqueue and perform paths
- factories or fixtures that stay small and deterministic
- explicit time and randomness control in flaky paths
