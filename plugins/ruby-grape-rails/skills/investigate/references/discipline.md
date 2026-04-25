# Investigation Discipline

Practical rules for root-cause analysis. Not general debugging theory.

## Before proposing any fix

1. **Read the full backtrace.** Top-to-bottom. Identify where control leaves app code and enters a gem / framework.
2. **Read the full error message.** Not just the class — the message often contains the key (`PG::UniqueViolation: ... constraint "idx_..."`).
3. **Identify the call chain** from the user's request to the failure:
   - Controller / endpoint → service → model → DB / external
   - Job enqueue site → perform → model / external
   Write it into the active plan scratchpad
   (`.claude/plans/<slug>/scratchpad.md`) before touching code. If a
   scratchpad already exists for the area you are touching, read the
   `## Ruled Out` notes first — do not retry anything those notes
   already eliminated.

## While investigating

1. **Narrow the repro first.** Full test suite fails? Find the single failing spec. Single spec fails? Find the single `it` block.
2. **Print, don't speculate.** When you need to know a value, print it. Don't guess.
3. **One hypothesis at a time.** Write down the ruled-out list (goes in `.claude/plans/<slug>/scratchpad.md` under `## Ruled Out`).

## When you have a candidate fix

1. **Regression test first.** Write a test that fails with the bug present and passes with the fix. Write it BEFORE writing the fix.
2. **Minimal diff.** Change only what's needed to make the red test green. No adjacent "improvements".
3. **Verify in runtime** — Tidewave / `rails runner` / `bin/rails console` — confirm the production-shaped path.
4. **Check for similar bugs.** Same pattern elsewhere? Add coverage.

## References

- Parent skill: `/rb:investigate`
