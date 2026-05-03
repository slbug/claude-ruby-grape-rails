# Testing Discipline

Practical rules for writing tests in this repo. Not framework docs.

## Before writing a new test

1. **Search for existing coverage.** Pattern
   `describe .*<ClassUnderTest>|def test_<behavior>` over `spec/`
   and `test/`. If found: extend it. Don't spawn a parallel spec
   for the same class.

2. **State RSpec vs Minitest explicitly** in the test file. No mixing.
   - RSpec: `describe`, `it`, `expect(x).to eq y`, `let`, `context`
   - Minitest: `class TestX < ActiveSupport::TestCase`, `def test_foo`, `assert_equal y, x`
   - Rails 7+ default is Minitest; Grape APIs often use RSpec — check your repo's `Gemfile.lock`.

3. **Mirror the structure** of existing specs in the same directory. If sibling specs use `let!(:user) { create(:user) }`, don't introduce a fresh pattern.

## When writing the test

1. **Fail first.** The test must fail before the implementation exists, and fail for the right reason.
2. **One behavior per test.** If your test name contains "and", split.
3. **Descriptive names.** `describe "POST /items"` + `it "rejects missing title"` beats `it "works"`.
4. **No conditional assertions.** `if cond; expect(a).to eq b; end` is a bug — the path might never execute.

## After the test passes

Ask yourself: **what edge cases did I skip?**

- Null / empty inputs
- Unicode / very long strings
- Race conditions (for Sidekiq / transactional code)
- Integer overflow / timestamp edge
- Authorization edge (different user roles)
- Transaction rollback (record left behind?)

Add the ones that matter. Document the ones you skipped (why).

## References

- Anthropic skill-formation study: conceptual-inquiry patterns score 86% mastery vs delegation <40%. Writing tests yourself > reading-only review.
- Parent skill: `testing` (auto-loaded for files under `spec/` or `test/`)
