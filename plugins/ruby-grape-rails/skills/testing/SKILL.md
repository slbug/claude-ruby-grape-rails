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

## References

| Need | Reference |
|---|---|
| verify-before-claiming-done discipline (Iron Law 21) | `${CLAUDE_SKILL_DIR}/references/discipline.md` |
| RSpec patterns (subject, let, contexts, shared examples) | `${CLAUDE_SKILL_DIR}/references/rspec-patterns.md` |
| FactoryBot patterns (build vs create, traits, sequences, transient) | `${CLAUDE_SKILL_DIR}/references/factory-patterns.md` |
| RSpec mocks, instance_double, allow vs expect | `${CLAUDE_SKILL_DIR}/references/mock-patterns.md` |
| Capybara + Turbo Stream + ActionCable system tests | `${CLAUDE_SKILL_DIR}/references/system-testing.md` |
