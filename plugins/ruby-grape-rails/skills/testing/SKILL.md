---
name: testing
description: "Authoring Ruby/Rails/Grape/Sidekiq tests: request specs, factories, anti-flake. Triggers: \"RSpec patterns\", \"factory setup\", \"flaky test\". Do NOT use for: running tests, executing rspec."
user-invocable: false
effort: medium
---
# Testing

## Good Defaults

- request specs or API tests for transport behavior
- focused unit tests for service/query objects
- worker tests for enqueue and perform paths
- factories or fixtures that stay small and deterministic
- explicit time and randomness control in flaky paths

## Gotchas

- Factory cycles. `create(:user)` triggers `create(:account)` triggers
  `create(:user)` — silent infinite loop. Detect via FactoryBot's
  `:build_stubbed` strategy or explicit `:user_without_account`
  factory.
- DatabaseCleaner truncation drift. `truncation` strategy doesn't
  reset sequences. Tests asserting on auto-increment IDs fail
  randomly. Use `transaction` or
  `ActiveRecord::Base.connection.reset_pk_sequence!`.
- Time-sensitive flakies. `Time.current` in factory +
  `expect(record.created_at).to eq Time.current` — race on test
  runner clock. Use `freeze_time` or `Timecop.freeze`.
- RSpec random order seed. Test passing alone but failing in suite is
  order-dependent. Reproduce with `rspec --seed <N>`; fix via
  `before(:each) do; reset_state; end` or split tests.

## References

| Need | Reference |
|---|---|
| verify-before-claiming-done discipline (Iron Law 21) | `${CLAUDE_SKILL_DIR}/references/discipline.md` |
| RSpec patterns (subject, let, contexts, shared examples) | `${CLAUDE_SKILL_DIR}/references/rspec-patterns.md` |
| FactoryBot patterns (build vs create, traits, sequences, transient) | `${CLAUDE_SKILL_DIR}/references/factory-patterns.md` |
| RSpec mocks, instance_double, allow vs expect | `${CLAUDE_SKILL_DIR}/references/mock-patterns.md` |
| Capybara + Turbo Stream + ActionCable system tests | `${CLAUDE_SKILL_DIR}/references/system-testing.md` |
