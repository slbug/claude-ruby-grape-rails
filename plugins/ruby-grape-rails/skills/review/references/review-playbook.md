# Review Playbook

Use this reference when `/rb:review` needs deeper reviewer focus notes or
file-type-specific checklists without bloating the main routing surface.

## Reviewer Focus Areas

### `ruby-reviewer`

- Ruby correctness, idioms, readability
- `it` keyword opportunities for Ruby 3.4+
- pattern matching, extraction, naming, and control-flow clarity

### `security-analyzer`

- SQL injection vectors
- XSS in views and serializers
- mass assignment, auth bypasses, authorization holes, secrets exposure
- every finding carries `evidence_mode`: `static-signal | runtime-confirmed | configuration-risk | requires-human-validation`

### `testing-reviewer`

- missing cases, fragile tests, readability, coverage gaps, stub misuse

### `iron-law-judge`

- transaction safety
- commit-safe enqueue discipline for the active ORM
- N+1 prevention
- decimal-for-money rules
- safe HTML rendering
- JSON-safe Sidekiq arguments

### `sidekiq-specialist`

- idempotency
- retry safety
- argument serialization
- commit-safe enqueueing
- error handling and queue configuration

### `rails-architect`

- service-layer and Grape API boundaries
- cross-context coupling
- architectural consistency

### `ruby-runtime-advisor`

- N+1 queries
- missing indexes
- memory bloat
- algorithmic complexity
- caching opportunities

### `data-integrity-reviewer`

- foreign key and uniqueness constraints
- transaction boundaries
- validation gaps
- rollback safety

### `migration-safety-reviewer`

- large-table defaults
- missing NOT NULL constraints
- missing foreign-key indexes
- irreversible migrations
- data migration mixed into schema migrations

## File-Type Checklists

### Ruby Files

- [ ] `ruby -c` passes
- [ ] formatter is clean (`standardrb` or `rubocop`)
- [ ] no bare `rescue`
- [ ] names and control flow stay readable
- [ ] duplication is avoided

### Rails Controllers

- [ ] strong parameters exist
- [ ] authn/authz is explicit
- [ ] service objects handle complex work
- [ ] redirects/renders are explicit
- [ ] transaction boundaries are deliberate

### Active Record / Sequel Models

- [ ] validations are present and tested
- [ ] associations use correct dependent behavior
- [ ] callbacks are necessary and safe
- [ ] package ORM conventions match the owning code
- [ ] indexes exist for hot queries and foreign keys

### Sidekiq Jobs

- [ ] includes `Sidekiq::Job`
- [ ] arguments are JSON-safe
- [ ] implementation is idempotent
- [ ] enqueue-after-commit semantics are correct
- [ ] retry/dead-letter behavior is intentional

### Grape APIs

- [ ] params are typed
- [ ] auth middleware is applied
- [ ] error handling is present
- [ ] serialization/content-type behavior is correct
- [ ] docs stay current

### Tests

- [ ] tests assert behavior, not internals
- [ ] setup is minimal and legible
- [ ] edge cases are covered
- [ ] names describe the behavior under test

### Migrations

- [ ] migration framework is identified first
- [ ] migration is reversible
- [ ] foreign keys are indexed
- [ ] null constraints and defaults are safe
- [ ] change is production-safe for large tables

## Common Ruby Anti-Patterns

| Anti-pattern | Issue | Better approach |
|--------------|-------|-----------------|
| `rescue Exception => e` | Catches too broadly, including interrupts and exits | `rescue SpecificError => e` or a deliberate `rescue StandardError => e` boundary |
| `!user.nil?` | Double negative | `user.present?` |
| `if condition; return x; end` | Unnecessary control flow | `return x if condition` |
| `ary.map { |x| x.name }` | Redundant block param | `ary.map(&:name)` or `ary.map { it.name }` |
| `user && user.name` | Manual nil-guard | `user&.name` |
| `DateTime.now` | Wrong default in Rails apps | `Time.current` or `Time.now` |

## Diff Collection

`resolve-base-ref` invocation + diff-stat capture procedure lives in
`../SKILL.md` § "Collecting Changed Files". Skill body is canonical;
do NOT duplicate here.

### Diff strategy (reviewer-owned)

Triage with the captured DIFF_STAT value first to identify high-noise
paths (cassettes, fixtures, schema dumps, lockfiles, generated files)
before running any `git diff`.

## Worker Briefing Template

Every reviewer `Agent(subagent_type:)` call from `/rb:review` skill body
includes this prompt template:

```text
Task: review {file list} for {scope}.

Scope: $CHANGED_FILES (from main session diff collection)
Base ref: <BASE_REF>
Merge base: <MERGE_BASE>
Diff stat (preview):
$DIFF_STAT

Artifact path (ABSOLUTE, computed by manifest-update prepare-run —
use exactly as given by the spawning skill body):
  <absolute-path-read-from-manifest-update-spawn-paths>

Diff strategy: triage with $DIFF_STAT first to skip high-noise paths
(cassettes, fixtures, schema dumps, lockfiles, generated files)
before running any git diff.

Required output:
1. Write artifact to the EXACT absolute path above.
   - Do NOT invent, modify, or shorten the filename.
   - Path always points at a non-existing target.
2. Return summary in Agent return text (used as artifact-recovery fallback).
   - Always write the artifact (even if findings are empty — write PASS
     with files reviewed).
3. Artifact MUST include a verdict line VERBATIM from the canonical
   4-set: `**Verdict**: PASS` | `**Verdict**: PASS WITH WARNINGS` |
   `**Verdict**: REQUIRES CHANGES` | `**Verdict**: BLOCKED`. No other
   wording. Do NOT emit `LGTM`, `BLOCK`, `Needs fixes`,
   `CONDITIONAL PASS`, or any abbreviation.

Findings format:
- file:line — Title
- Severity: Blocker | Warning | Suggestion
- Confidence: HIGH | MEDIUM | LOW
- Description, current code, suggested code, why it matters

Stop after returning. Do NOT call Agent() — this is a leaf review.
```

## Confidence Levels

Every finding MUST carry a confidence label.

| Level | Meaning | Example |
|---|---|---|
| `HIGH` | Direct code evidence — specific line, test failure, static analysis finding | "Line 42: `params[:id]` interpolated into SQL string" |
| `MEDIUM` | Pattern match — known anti-pattern or convention violation, no direct proof of bug | "Service object bypasses transaction boundary (common data-loss pattern)" |
| `LOW` | Subjective — style preference, naming opinion, architecture suggestion | "Consider extracting this into a form object" |

Consolidate duplicates: keep highest confidence among them. Sort
findings within each severity bucket: `HIGH` → `MEDIUM` → `LOW`.

## Synthesis Procedure

Five steps, in order. Do NOT skip.

### STEP 1: Read each agent artifact (post-recovery)

For each manifest entry: STAT the expected path; apply the recovery
state machine in
`plugins/ruby-grape-rails/references/artifact-recovery.md`
(coverage-noun `Reviewer`).

### STEP 2: Normalize each agent's verdict text

Scan each per-agent artifact for verdict prose. Map non-canonical
forms to the canonical 4-set BEFORE writing the consolidated header:

Use ONLY the worker artifact's verdict prose + the worker's own
finding-counts (bucket form `Blocker | Warning | Suggestion` per §
"Worker Briefing Template"). Diff-status filter (new vs pre-existing)
applies in STEP 3.

| Non-canonical form (preserve verbatim in metadata) | Canonical mapping rule |
|---|---|
| `CONDITIONAL PASS`, `PASS WITH CAVEATS`, `PASS-WITH-WARNS` | infer from worker counts: any `Blocker` → `BLOCKED`; else any `Warning` → `PASS WITH WARNINGS`; else `PASS` |
| `Approved`, `LGTM`, `looks good` | `PASS` if worker reports zero `Blocker` and zero `Warning`; else map per worker counts |
| `Needs fixes`, `fix before merge`, `not ready` | infer from worker counts: any `Blocker` → `BLOCKED`; else any `Warning` → `PASS WITH WARNINGS`; else `PASS`. Do NOT auto-route to `REQUIRES CHANGES` — that verdict is reserved for missing test coverage on NEW public behavior (per § "Verdict Decision Rules"). Only emit `REQUIRES CHANGES` when the worker explicitly flagged a `New public behavior without tests` finding. |
| `BLOCK`, `BLOCKER` (verdict, not severity tag) | `BLOCKED` |

Preserve the agent's raw verdict text VERBATIM in the
`Reviewer Verdicts` metadata table at top of the consolidated
artifact. Normalize only the consolidated header.

### STEP 3: Filter diff-introduced vs pre-existing

Coverage row counts + Summary table counts use NEW findings only
(diff-introduced). Pre-existing findings appear in `## Pre-existing
Issues` section and the At-a-Glance Finding Table with
`New? = Pre-existing`. They never affect the consolidated verdict.

Per § "Worker Severity Mapping":

- worker `Blocker` introduced by this diff → counted Blocker
- worker `Blocker` on unchanged code → Pre-existing Blocker (reported only)
- worker `Warning` introduced by this diff → counted Warning
- worker `Suggestion` introduced by this diff → counted Suggestion

Casing rule (title case for severity; UPPERCASE only for verdict
4-set). Count-aware grammar enforced by `output_checks.py`: singular
form ONLY when count == 1; plural form for count != 1 (including 0).

| Surface | Form | Example |
|---|---|---|
| Per-finding `Severity:` tag (one finding per line) | always singular | `Severity: Blocker` |
| At-a-Glance Severity column (one finding per row) | always singular | `\| 1 \| {title} \| Warning \| HIGH \| {agent} \| {file}:{line} \| Yes \|` |
| Counts mandatory prefix | count-aware | `**Counts:** 5 findings (1 Blocker, 3 Warnings, 1 Suggestion); 2 notes` |
| Reviewer Coverage row count | count-aware, parser-locked | `0 Blockers / 1 Warning / 0 Suggestions` |
| Summary table category column | always plural | `\| Blockers \| 0 \|` / `\| Warnings \| 1 \|` |
| Consolidated section headers | always plural | `## Blockers (3)` / `## Warnings (1)` / `## Suggestions (0)` |
| Verdict 4-set | UPPERCASE strict | `PASS \| PASS WITH WARNINGS \| REQUIRES CHANGES \| BLOCKED` |

Invalid forms rejected by parser:
`1 Blockers` (singular required for 1), `0 Blocker` (plural required for 0).

### STEP 4: Compute consolidated verdict deterministically

Apply the algorithm from § "Verdict Decision Rules":

```
if blockers_introduced_by_diff > 0:
    verdict = BLOCKED
elif new_public_behavior_lacks_test_coverage:
    verdict = REQUIRES CHANGES
elif warnings > 0:
    verdict = PASS WITH WARNINGS
else:
    verdict = PASS
```

Apply the algorithm verbatim. Do NOT override with author judgment.
Preserve nuance in per-finding prose, not in the verdict tag.

`new_public_behavior_lacks_test_coverage`: derive at synthesis time
from per-agent findings tagged as test-coverage gaps (per § "Worker
Severity Mapping"). When fired, populate `## Test Coverage Gaps
({n})` in the consolidated artifact (see § "Consolidated Review
Format"). REQUIRES CHANGES chat script reads that section verbatim.

### STEP 5: Write the consolidated review

- Header MUST include `## Reviewer Coverage` with one row per
  spawned reviewer + recovery state.
- Header MUST include `## Reviewer Verdicts` with each agent's raw
  verdict text + normalized canonical form. For `stub-no-output`
  reviewers, emit `(no output)` literal in both cells.
- Preserve blockers / must-fix items VERBATIM in body.
- Preserve decision options + rationale, unresolved disagreements,
  file paths, concrete evidence.
- Dedupe overlapping findings across agents; cite all sources.
- Keep highest confidence among duplicates.
- Sort findings: Blockers → Warnings → Suggestions;
  HIGH → MEDIUM → LOW within bucket.
- Preserve "Pre-existing Issues" section.

## Resume Protocol

Single helper call at fanout entry:

```bash
MANIFEST=$(${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run \
  --skill=rb:review --slug="$REVIEW_SLUG" \
  --base-ref=<BASE_REF> \
  --agents="$AGENTS_CSV")
```

`$AGENTS_CSV` is the comma-separated list of reviewer slugs computed
by the skill body from the Reviewer Selection Matrix above. Not a
fixed default.

Helper computes manifest path, datesuffix, agent paths, consolidated
path, git pins. Archives any prior manifest. Outputs absolute
manifest path on stdout.

Schema + per-skill staleness rules:
`plugins/ruby-grape-rails/references/run-manifest.md`.

## Severity Levels

| Severity | Description | Action |
|----------|-------------|--------|
| **Blocker** | Must fix before merge — Iron Law violations, security vulnerabilities, data-loss risks, production-outage risks, critical correctness | Surface in chat with one-line impact |
| **Warning** | Should fix — performance issues, maintainability problems, potential bugs | Note in review with recommendation |
| **REQUIRES CHANGES** (verdict only) | Code works but new public behavior lacks test coverage | List affected methods/endpoints/jobs |
| **Suggestion** | Style, refactor, or doc improvements | Brief note, no action required |

## Worker Severity Mapping

Reviewer agents emit `Blocker | Warning | Suggestion` (title case
singular). Synthesis applies diff-status filter only — no vocabulary
translation:

| Worker output | Diff status | Counted into Summary? |
|---|---|---|
| Blocker | introduced by this diff | yes — Blocker |
| Blocker | unchanged code | no — Pre-existing Blocker (reported only) |
| Warning | introduced by this diff | yes — Warning |
| Warning | unchanged code | no — Pre-existing Warning (reported only) |
| Suggestion | introduced by this diff | yes — Suggestion |
| Suggestion | unchanged code | no — Pre-existing Suggestion (reported only) |
| New public behavior without tests | any | REQUIRES CHANGES verdict trigger (not a per-finding bucket) |

Casing canon — title case throughout severity. See STEP 3 casing rule
above for per-surface form. Verdict 4-set stays UPPERCASE.

## Review Scope

Review is **findings-only**. Do NOT:

- Create task lists (`- [ ]`)
- Add fix phases to plan files
- Modify any files outside `.claude/reviews/`
- Start fixing issues

Task creation and planning happen in `/rb:triage` after the user decides.

## Pre-existing Issues

Findings on code NOT changed in this diff carry `New? = Pre-existing`
in the At-a-Glance Finding Table and appear in the dedicated
`## Pre-existing Issues (unchanged code)` section. They are NOT
counted in `## Summary` or in `## Reviewer Coverage` row counts —
both reflect NEW findings only (diff-introduced). They never affect
the consolidated verdict; PASS is possible with pre-existing blockers
as long as no NEW blockers were introduced.

## Research Requirement for Infrastructure

When reviewing CI/CD, deployment, or external service configuration:

- ALWAYS verify how the specific service works before making claims
- Use Context7 / WebFetch to verify CI runner, service-container, matrix,
  cache, or deployment semantics
- Do NOT rely on general memory — CI platforms change
- Example: GitHub Actions matrix jobs each get their own service containers,
  not a shared one. Verify, do not assume.

## Verdict Decision Rules

| Verdict | Conditions |
|---------|-----------|
| **PASS** | No new blockers, no warnings (pre-existing blockers OK) |
| **PASS WITH WARNINGS** | No new blockers; warnings present but not test-coverage gaps |
| **REQUIRES CHANGES** | No blockers, but new public behavior lacks test coverage |
| **BLOCKED** | Iron Law violation, security issue, data-loss risk, production-outage risk, or critical correctness bug introduced by this diff |

REQUIRES CHANGES triggers:

- New public methods with zero tests
- Removed tests without replacement coverage
- New controller actions without tests
- New Sidekiq jobs without `perform` tests
- New Turbo Stream routes without basic render tests

## Consolidated Review Format

Write the synthesized review to the path read via
`manifest-update field "$MANIFEST" consolidated_path`:

````markdown
# Review: {track}

**Date**: {timestamp}
**Complexity**: {Simple|Medium|Complex} ({N} files{, escalated: reason})
**Files Changed**: {list}
**Reviewers**: {comma-separated reviewer slugs from manifest `agents` map}

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| {agent-slug} | artifact \| stub-replaced \| recovered-from-return \| stub-no-output | 0 Blockers / 1 Warning / 0 Suggestions |

Findings column uses title case + count-aware grammar (singular
when count == 1, plural otherwise — including 0). Form examples:
`0 Blockers / 1 Warning / 0 Suggestions`,
`3 Blockers / 0 Warnings / 0 Suggestions`,
`1 Blocker / 2 Warnings / 1 Suggestion`. Counts NEW findings only
(diff-introduced). Pre-existing findings attributed to the
reviewer appear in `## Pre-existing Issues` and the at-a-glance
table with `New? = Pre-existing`. State definitions:

- `artifact` — on-disk file ≥ 1000 bytes; trust as-is
- `stub-replaced` — on-disk stub overwritten with larger findings from agent return text
- `recovered-from-return` — no on-disk artifact; findings extracted from return text
- `stub-no-output` — no usable reviewer output; coverage gap

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| {agent-slug} | {agent's verbatim verdict text} | PASS \| PASS WITH WARNINGS \| REQUIRES CHANGES \| BLOCKED |
| {stub-no-output-agent-slug} | (no output) | (no output) |

Raw Verdict: VERBATIM agent wording. Canonical: map per § "STEP 2".
The consolidated `**Verdict**:` line comes from § "STEP 4"
(blocker / warning / test-coverage counts), not from this column.

For rows whose Coverage state is `stub-no-output`: emit
`(no output)` literal in BOTH cells. Reserve the placeholder for
`stub-no-output` rows only.

## Summary

Counts NEW findings only (diff-introduced). Pre-existing issues are
NOT counted here — see `## Pre-existing Issues` + at-a-glance
`New? = Pre-existing`.

| Severity | Count |
|----------|-------|
| Blockers | {n} |
| Warnings | {n} |
| Suggestions | {n} |

**Verdict**: PASS | PASS WITH WARNINGS | REQUIRES CHANGES | BLOCKED

## Blockers ({n})

### 1. {Issue Title}

**File**: `path/to/file.rb:{line}`
**Reviewer**: {agent} | **Confidence**: HIGH | MEDIUM | LOW
**Issue**: {description}
**Why it matters**: {impact}

**Current**:

```ruby
{bad code}
```

**Suggested**:

```ruby
{good code}
```

## Warnings ({n})

### 1. {Issue Title}

**File**: `path/to/file.rb:{line}`
**Reviewer**: {agent} | **Confidence**: HIGH | MEDIUM | LOW
**Issue**: {description}
**Recommendation**: {what to do}

## Suggestions ({n})

### 1. {Suggestion Title}

**File**: `path/to/file.rb`
**Reviewer**: {agent} | **Confidence**: HIGH | MEDIUM | LOW
**Suggestion**: {improvement}

## Pre-existing Issues (unchanged code)

- {issue} (not introduced by this change)

## Test Coverage Gaps ({n})

Emit ONLY when consolidated `**Verdict**: REQUIRES CHANGES`. Omit
section entirely on other verdicts. One row per NEW public surface
(method / controller action / Sidekiq job / Turbo Stream route)
introduced by this diff with no test coverage.

| # | Surface | File | Why uncovered | Suggested test |
|---|---------|------|---------------|----------------|
| 1 | `Class#method` / `Controller#action` / `JobClass#perform` | `path/to/file.rb:{line}` | new diff-introduced public behavior; no spec exercises it | `spec/path/to/file_spec.rb` — assert `{behavior}` |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | {title} | Blocker \| Warning \| Suggestion | HIGH \| MEDIUM \| LOW | {agent} | {path}:{line} | Yes \| Pre-existing |
````

Every consolidated review MUST include the at-a-glance table, even for one
finding. `New?` = `Yes` for findings on changed lines (this diff);
`Pre-existing` for unchanged code (does NOT affect verdict).

The consolidated review is findings-only — NO task lists, NO fix phases,
NO `## Next Steps`. Task routing happens in `/rb:triage`.

## Review Outcomes (chat scripts)

After writing the consolidated artifact, present the verdict in chat.

**PASS:**

```text
Review complete. No NEW blockers introduced by this diff.
(Pre-existing blockers, if any, are tracked separately in
`## Pre-existing Issues` and do NOT affect verdict per
§ "Pre-existing Issues".)

How would you like to proceed?

- /rb:compound — Capture solution (default).
- /rb:learn — Capture lessons.
- /rb:triage .claude/reviews/{review-slug}-{datesuffix}.md
    — Opt in to suggestions (NEW Suggestions only; no warnings or blockers to handle).
- I'll handle it myself
```

**PASS WITH WARNINGS:**

```text
Review complete. {n} warnings noted (full list in
`.claude/reviews/{review-slug}-{datesuffix}.md` § "At-a-Glance Finding Table").
Warnings are non-blocking.

How would you like to proceed?

- /rb:triage .claude/reviews/{review-slug}-{datesuffix}.md
    — Default. Select which warnings to fix; defer the rest.
- /rb:learn — Capture lessons without fixing.
- /rb:compound — Capture solution without fixing.
- I'll handle it myself
```

Do NOT suggest bare `/rb:work` here — it would resume any active
plan from `.claude/ACTIVE_PLAN`, not address these warnings.
`/rb:triage {review-path}` generates the right plan first.

**REQUIRES CHANGES:**

```text
Review found {n} test-coverage gaps (full list in
`.claude/reviews/{review-slug}-{datesuffix}.md` § "Test Coverage Gaps"):

1. {Surface} in {file} — no test coverage
2. {Surface} in {file} — no test coverage

How would you like to proceed?

- /rb:triage .claude/reviews/{review-slug}-{datesuffix}.md
    — Default. Auto-includes gaps + lets you select any warnings.
- /rb:plan .claude/reviews/{review-slug}-{datesuffix}.md
    — Gaps-only plan, no triage UI.
- /rb:quick — Inline test addition (single uncovered surface, simple case)
- I'll handle it myself
```

Do NOT suggest bare `/rb:work` here — it would resume any active
plan from `.claude/ACTIVE_PLAN`, not address these gaps. Both
review-path flows (`/rb:triage` / `/rb:plan` with the review path)
generate the right plan first. `/rb:quick` is plan-free and fits
single-surface coverage additions only.

**BLOCKED:**

```text
Review found {n} blockers ({n} warnings):

1. {Blocker title} — {one-line impact}
2. {Blocker title} — {one-line impact}

How would you like to proceed?

- /rb:triage .claude/reviews/{review-slug}-{datesuffix}.md — Select findings, create fix plan
- /rb:quick — Inline fix (single isolated change, <~20 lines)
- I'll handle it myself
```

Do NOT suggest bare `/rb:work` here — it would resume any active
plan from `.claude/ACTIVE_PLAN`, not address these blockers.
`/rb:triage {review-path}` generates the right plan first.
`/rb:quick` is plan-free and fits single isolated fixes only.

Always enumerate actual findings — never just show a count.

## Deduplication Strategy

When multiple agents find the same issue:

1. Merge into single finding
2. Cite all agents who found it
3. Use most specific description
4. Keep highest severity
5. List all affected lines

## Size-Tier Dispatch

Tier = `max(file_tier, loc_tier)` per `Complexity Classification` in
parent SKILL.md.

| Tier | Diff LOC | Agents | Rationale |
|---|---|---|---|
| Simple | ≤ 200 | ruby-reviewer + security-analyzer | Tight diffs rarely need full panel |
| Medium | 201-1000 | + testing-reviewer + verification-runner + conditionals | Standard panel |
| Complex | > 1000 | full xhigh fanout | Architectural scope |

### Compute diff LOC

```
DIFF_LOC=$(git diff --shortstat <MERGE_BASE>...HEAD | awk '{n=$4+$6} END{print n+0}')
```

Columns 4 + 6 are insertions + deletions. `END{print n+0}` emits `0`
on empty diff. Range matches `$DIFF_STAT` + `$CHANGED_FILES` (Diff
Collection step).

On `DIFF_LOC=0` (legitimate via pure rename / mode change / binary diff):

- Run `git diff --numstat <MERGE_BASE>...HEAD`
- File count > 0 → tier by file count (Simple minimum)
- File count = 0 AND zero `--numstat` entries → reject; require `all`
  argument (per `argument-hint:`)

### Boundary cases

| Diff LOC | File count | Tier |
|---|---|---|
| 199 | 2 | Simple |
| 200 | 2 | Simple (≤ 200, inclusive) |
| 201 | 2 | Medium |
| 50 | 11 | Complex (file count override) |
| 1500 | 3 | Complex (LOC override) |
