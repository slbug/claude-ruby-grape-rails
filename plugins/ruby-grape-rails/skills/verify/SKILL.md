---
name: rb:verify
description: Use to verify completed code with the project's strongest check stack. Prefer a repo-native CI wrapper when present, otherwise run Zeitwerk, lint, tests, Brakeman, security, and migration checks.
argument-hint: "[--quick|--full]"
effort: low
---
# Verify Ruby Work

Run verification in priority order, stopping at the first failure. Each step must pass before proceeding to the next.

## Iron Laws

1. **Never commit with failing tests.**
2. **Never skip security scans on public-facing code.**
3. **Always verify autoloading after structural changes.**
4. **Never ignore Zeitwerk check failures.**

## Tool Selection Policy

- Read `${REPO_ROOT}/.claude/.runtime_env` when present and non-symlinked; use
  its tool booleans as the primary command-selection source of truth.
- Prefer direct tools as the source of truth:
  - `bundle exec standardrb` or `bundle exec rubocop`
  - `bundle exec brakeman`
- Use `lefthook run <hook>` only when cached runtime detection shows:
  - `LEFTHOOK_AVAILABLE=true`
  - `LEFTHOOK_CONFIG_PRESENT=true`
  - `LEFTHOOK_LINT_SECURITY_COVERED=true`
- If Lefthook is available but no config is detected, ask the user where the config lives before treating it as authoritative.
- `LEFTHOOK_DIFF_LINT_COVERED=true` means Lefthook covers diff-scoped Pronto/RuboCop review only; it does not replace full direct linting.
- Tests are separate from Lefthook policy and should stay targeted/full based on change scope.
- Treat `pronto` as an optional final diff-scoped pass:
  - run it after direct lint/security checks
  - do not use it as a substitute for StandardRB/RuboCop or Brakeman

When cached runtime state is available:

- `STANDARDRB_AVAILABLE=true` → prefer `bundle exec standardrb`
- else `RUBOCOP_AVAILABLE=true` → prefer `bundle exec rubocop`
- `BRAKEMAN_AVAILABLE=true` → run `bundle exec brakeman`
- `PRONTO_AVAILABLE=true` → allow optional final `bundle exec pronto run -c <base>`
- `VERIFY_COMPOSITE_AVAILABLE=true` → treat that as a hint that a repo-native
  composite verifier may exist, then re-detect it from the working tree before
  running it
- `LEFTHOOK_*` booleans control whether Lefthook is an acceptable wrapper, not whether direct checks disappear

## Project-Native Composite Runners

Some Ruby repos already define a canonical verification entrypoint. When cached
runtime state exposes:

- `VERIFY_COMPOSITE_AVAILABLE=true`

re-detect the wrapper from the working tree before trying it. Do not execute a
raw command string taken from `.claude/.runtime_env`.

Examples:

- `./bin/check`
- `./bin/ci`
- `make ci`
- `make check`
- `bundle exec rake ci`

Fallback rule:

- if the wrapper fails because the wrapper itself is unavailable or broken
  locally (`command not found`, missing task, permission denied, missing
  dependency), log the fallback and run the direct checks below
- if the wrapper runs and surfaces real lint/test/security failures, stop there
  and fix them instead of hiding them behind fallback

## Verification Stack

```
┌─────────────────────────────────────────────────────────┐
│  VERIFICATION ORDER                                       │
├─────────────────────────────────────────────────────────┤
│  1. Zeitwerk Check     → File naming & autoloading      │
│  2. Lint               → StandardRB / RuboCop           │
│  3. Security           → Brakeman / static analysis     │
│  4. Tests              → RSpec/Minitest                 │
│  5. Type Check         → Sorbet/Steep (if present)      │
│  6. Database           → Pending migrations             │
│  7. Pronto (optional)  → Diff-scoped final pass         │
└─────────────────────────────────────────────────────────┘
```

### 1. Zeitwerk Check (full Rails apps)

Run `bundle exec rails zeitwerk:check`.

Run this only when cached runtime state shows `FULL_RAILS_APP=true` or the repo
clearly has a real Rails entrypoint (`bin/rails` or `script/rails`) or the
standard runnable app layout (`config/application.rb`, `config/environment.rb`,
`config/boot.rb`, `app/`, and `config/environments/`).

**Purpose**: Verify all files can be autoloaded correctly.

**Pass**: All files load successfully  
**Fail**: File naming mismatch, syntax errors, circular dependencies

**Common Failures**:

```
❌ app/services/user_creator.rb defines UserCreator
   Expected: UserCreator
   Found:    UserService::UserCreator
   
   Fix: Rename module or file to match

❌ app/models/concerns/validatable.rb not found
   Expected: Validatable concern
   
   Fix: Move to app/models/concerns/validatable.rb
```

**No generic auto-fix flag**: `zeitwerk:check` reports the mismatch, but you
need to fix the file name, constant name, or inflector configuration yourself
and rerun the check.

### 2. Linting

#### StandardRB (preferred when `STANDARDRB_AVAILABLE=true`)

- Check: `bundle exec standardrb`
- Auto-fix: `bundle exec standardrb --fix`
- Specific files: `bundle exec standardrb app/models/user.rb app/services/`

#### RuboCop (use when `STANDARDRB_AVAILABLE!=true` and `RUBOCOP_AVAILABLE=true`)

- Check: `bundle exec rubocop`
- Auto-fix safe: `bundle exec rubocop --autocorrect`
- Auto-fix all (including unsafe): `bundle exec rubocop --autocorrect-all`
- Specific files: `bundle exec rubocop app/models/user.rb`
- Specific cop: `bundle exec rubocop --only Layout/LineLength`

**Critical Cops** (never ignore):

- `Security/` - All security-related cops
- `Lint/` - Syntax and logic errors
- `Rails/` - Rails-specific issues

**Style Cops** (can defer):

- `Layout/` - Formatting (auto-fixable)
- `Style/` - Style preferences

If `LEFTHOOK_LINT_SECURITY_COVERED=true`, you may run the appropriate
`lefthook run <hook>` entrypoint instead of separate lint/security commands,
but only when the config clearly covers both categories.

### 3. Security Scan (Brakeman)

- Basic scan: `bundle exec brakeman`
- Quiet mode (errors only): `bundle exec brakeman -q`
- Skip informational: `bundle exec brakeman -w2`
- Output to file: `bundle exec brakeman -o brakeman-report.html`
- Ignore false positives: `bundle exec brakeman -I`

**Never ignore**:

- SQL Injection
- Cross-Site Scripting (XSS)
- Mass Assignment
- Remote Code Execution
- File Access vulnerabilities

If Lefthook is detected but only covers lint or only covers security/static
analysis, keep running the missing direct tool yourself.

### 4. Tests

#### RSpec

- Full suite: `bundle exec rspec`
- Fail fast: `bundle exec rspec --fail-fast`
- Specific files: `bundle exec rspec spec/models/user_spec.rb`
- Specific line: `bundle exec rspec spec/models/user_spec.rb:45`
- Parallel: `bundle exec parallel_rspec spec/`

#### Minitest

- Full suite: `bundle exec rails test`
- Fail fast: `bundle exec rails test --fail-fast`
- Specific files: `bundle exec rails test test/models/user_test.rb`
- Specific line: `bundle exec rails test test/models/user_test.rb:45`
- System tests: `bundle exec rails test:system`

#### Test Selection

Run tests based on what changed:

- Model changed → `bundle exec rspec spec/models/`
- Controller changed → `bundle exec rspec spec/controllers/ spec/requests/`
- Migration changed → `bundle exec rails db:migrate:status`
- Gem changed → `bundle exec rspec` (full suite)

### 5. Type Checking (if present)

#### Sorbet

- Check types: `bundle exec srb tc`
- With strictness suggestions: `bundle exec srb tc --suggest-typed`

#### Steep

Run `bundle exec steep check`.

#### RBS

Run `bundle exec rbs validate` to validate type signatures.

### 6. Database Verification

- Check pending: `bundle exec rails db:migrate:status`
- Verify schema: `bundle exec rails db:migrate RAILS_ENV=test` then `bundle exec rails db:schema:dump`
- Check conflicts: `git diff db/schema.rb`

### 7. Diff-Scoped Review (Optional Pronto)

Run this only after direct lint/security checks pass:

Resolve the base ref: run `eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref)"`
to get `$BASE_REF` (handles custom remotes, non-standard default branches,
fetches before resolving). Then run
`bundle exec pronto run -c "$(git merge-base HEAD "$BASE_REF")"`.

Use the first base ref that exists. Pronto is a last-step changed-files pass,
not a replacement for StandardRB/RuboCop or Brakeman.

## Verification Profiles

Use the canonical scripts in
`${CLAUDE_SKILL_DIR}/references/verification-profiles.md` instead of copying
stale snippets between repos.

Recommended split:

- `Quick Check (CI)`:
  - re-detect a project-native wrapper from the working tree
  - run Zeitwerk only for full Rails apps
  - run the strongest configured direct linter/security/test commands
  - treat Pronto as optional and non-blocking
- `Full Verification`:
  - everything from Quick Check
  - plus type checks, migration status, and fuller test output
- `Fast Feedback`:
  - a lightweight lint + targeted-test loop while iterating locally

Keep the heavy examples in the reference file so this skill stays focused on
tool policy and failure handling.

## Output Format

### Success

```
═══════════════════════════════════════════════════════════
                    VERIFICATION PASSED
═══════════════════════════════════════════════════════════

  ✅ Zeitwerk          All files load correctly
  ✅ StandardRB        No style violations
  ✅ Brakeman          No security issues
  ✅ RSpec             156 examples, 0 failures
  ⏭️  Sorbet           Not configured
  ✅ Database          No pending migrations

───────────────────────────────────────────────────────────
Time: 12.4 seconds
───────────────────────────────────────────────────────────
```

### Failure

```
═══════════════════════════════════════════════════════════
                    VERIFICATION FAILED
═══════════════════════════════════════════════════════════

  ✅ Zeitwerk          All files load correctly
  ❌ StandardRB        3 violations found
  ⏭️  Brakeman         Skipped (previous failure)
  ⏭️  RSpec            Skipped (previous failure)

───────────────────────────────────────────────────────────
StandardRB Failures:
───────────────────────────────────────────────────────────

app/models/user.rb:45:81: Layout/LineLength: Line is too long
app/services/order_creator.rb:12:3: Style/Documentation: Missing class comment  
app/controllers/orders_controller.rb:34:5: Rails/Output: Do not write to stdout

───────────────────────────────────────────────────────────
Next Step:
───────────────────────────────────────────────────────────
Run: bundle exec standardrb --fix

Or fix manually and re-run: /rb:verify
───────────────────────────────────────────────────────────
```

## Failure Handling

### Step 1: Identify the Issue

- Detailed output: `bundle exec rspec --format documentation spec/failing_spec.rb`
- With backtrace: `bundle exec rspec --backtrace spec/failing_spec.rb`

### Step 2: Fix Strategy

| Check | Common Fix |
|-------|-----------|
| Zeitwerk | Fix file naming or module nesting |
| Lint | Run auto-fix: `standardrb --fix` |
| Security | Address vulnerability or add to ignore list with reason |
| Tests | Fix failing test or implementation |
| Types | Add/update type signatures |
| Pronto | Fix the changed-file issue, then rerun direct lint/security if needed |

### Step 3: Re-verify

After fixing, re-run just that check (e.g., `bundle exec standardrb`), then run `/rb:verify` for full verification.

## CI Integration & Troubleshooting

See: [references/ci-cd-troubleshooting.md](references/ci-cd-troubleshooting.md) — GitHub Actions, GitLab CI, pre-commit hooks, and troubleshooting guides

## Best Practices

1. **Run verification before every commit** (use pre-commit hook)
2. **Never skip security scans** on production-bound code
3. **Fix linting issues immediately** - they're usually auto-fixable
4. **Keep tests fast** - aim for < 1 minute for unit tests
5. **Use parallel testing** for large suites
6. **Document ignored warnings** with reasons
7. **Update ignore lists** when fixing real issues
8. **Run full verification** before PR creation

## Commands Summary

| Command | Purpose |
|---------|---------|
| `/rb:verify` | Run full verification stack |
| `./bin/check` / `./bin/ci` / `make ci` / `bundle exec rake ci` | Prefer project-native composite verification when present |
| `bundle exec rails zeitwerk:check` | Verify autoloading for full Rails apps |
| `bundle exec standardrb` | Check style when StandardRB is configured |
| `bundle exec standardrb --fix` | Auto-fix style when StandardRB is configured |
| `bundle exec rubocop` | Check style when RuboCop is configured |
| `bundle exec brakeman` | Security scan when Brakeman is configured |
| `bundle exec pronto run -c <base>` | Diff-scoped final pass |
| `bundle exec rspec` | Run tests |
| `bundle exec rails test` | Run Minitest |
| `bundle exec rails db:migrate:status` | Check migrations |
