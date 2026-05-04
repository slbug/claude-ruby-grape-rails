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

`/rb:review` skill body resolves the base ref and captures the file
list + stat ONCE. Reviewers own the diff strategy from there.

```bash
eval "$(${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref)"
MERGE_BASE=$(git merge-base HEAD "$BASE_REF")
CHANGED_FILES=$(git diff --name-only --diff-filter=ACMR "$MERGE_BASE"...HEAD)
DIFF_STAT=$(git diff --stat "$MERGE_BASE"...HEAD)
```

Pass `$CHANGED_FILES`, `$BASE_REF`, `$MERGE_BASE`, and `$DIFF_STAT` to
every spawned reviewer Agent() call. Reviewers scope all
reads/grep/analysis to `$CHANGED_FILES` and NEVER scan unchanged files.

### Diff strategy (reviewer-owned)

Triage with `$DIFF_STAT` first to identify high-noise paths
(cassettes, fixtures, schema dumps, lockfiles, generated files)
before running any `git diff`.

## Worker Briefing Template

Every reviewer `Agent(subagent_type:)` call from `/rb:review` skill body
includes this prompt template:

```text
Task: review {file list} for {scope}.

Scope: $CHANGED_FILES (from main session diff collection)
Base ref: $BASE_REF
Merge base: $MERGE_BASE
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
3. Artifact MUST include a verdict line emitted VERBATIM from the
   canonical 4-set: `**Verdict**: PASS` | `**Verdict**: PASS WITH WARNINGS`
   | `**Verdict**: REQUIRES CHANGES` | `**Verdict**: BLOCKED`. No other
   wording. Do NOT emit `LGTM`, `BLOCK`, `Needs fixes`, `CONDITIONAL PASS`,
   or any abbreviation. Synthesis preserves the verbatim string in the
   consolidated `## Reviewer Verdicts` table; STEP 2 normalization is
   defense-in-depth for legacy artifacts only — current workers MUST
   emit canonical strings directly.

Findings format:
- file:line — Title
- Severity: Critical | Warning | Info
- Confidence: HIGH | MEDIUM | LOW
- Description, current code, suggested code, why it matters

Stop after returning. Do NOT call Agent() — this is a leaf review.
```

## Confidence Levels

Every finding MUST include a confidence label. This tells the user
which findings are backed by evidence vs. pattern-based hunches.

| Level | Meaning | Example |
|---|---|---|
| `HIGH` | Direct code evidence — specific line, test failure, static analysis finding | "Line 42: `params[:id]` interpolated into SQL string" |
| `MEDIUM` | Pattern match — known anti-pattern or convention violation, no direct proof of bug | "Service object bypasses transaction boundary (common data-loss pattern)" |
| `LOW` | Subjective — style preference, naming opinion, architecture suggestion | "Consider extracting this into a form object" |

When consolidating findings from multiple agents, keep the highest
confidence level among duplicates. Sort findings by confidence
(`HIGH` first) within each severity bucket.

## Synthesis Procedure

Five steps, in order. Skipping any step causes the recurring drift
modes (non-canonical verdict pass-through, worker-form severity
leak in consolidated artifact, soft verdict despite blockers).

### STEP 1: Read each agent artifact (post-recovery)

For each manifest entry: STAT the expected path; apply the recovery
state machine in § "Artifact Recovery" below.

### STEP 2: Normalize each agent's verdict text

Scan each per-agent artifact for verdict prose. Map non-canonical
forms to the canonical 4-set BEFORE writing the consolidated header:

| Non-canonical form (preserve verbatim in metadata) | Canonical mapping rule |
|---|---|
| `CONDITIONAL PASS`, `PASS WITH CAVEATS`, `PASS-WITH-WARNS` | infer from finding count; bucket-form severity → canonical |
| `Approved`, `LGTM`, `looks good` | `PASS` if no warnings/blockers; else map per finding count |
| `Needs fixes`, `fix before merge`, `not ready` | `REQUIRES CHANGES` if no blockers; else `BLOCKED` |
| `Critical`, `BLOCK`, `BLOCKER` (verdict, not severity) | `BLOCKED` |

Preserve the agent's raw verdict text in a `Reviewer Verdicts`
metadata table at top of the consolidated artifact. Do NOT erase
their wording — only normalize the consolidated header.

### STEP 3: Map worker severity to bucket form

Reviewer Coverage row counts MUST use bucket form
(`BLOCKER | WARNING | SUGGESTION`), NOT worker form
(`Critical | Warning | Info`). Per § "Worker Severity Mapping":

- worker `Critical` introduced by this diff → `BLOCKER`
- worker `Critical` on unchanged code → `Pre-existing BLOCKER` (counted; no verdict effect)
- worker `Warning` → `WARNING`
- worker `Info` → `SUGGESTION`

Per-agent artifacts retain their original wording. The consolidated
artifact uses bucket form throughout — Reviewer Coverage row,
Summary table, At-a-Glance Finding Table, section headers.

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

Do NOT override with author judgment. If 4 BLOCKERs are present,
the verdict is `BLOCKED` — even when each individual blocker looks
"fixable in one PR". Preserve author-side nuance in per-finding
prose, not the verdict tag.

### STEP 5: Write the consolidated review

- Header MUST include `## Reviewer Coverage` with one row per
  spawned reviewer + recovery state.
- Header MUST include `## Reviewer Verdicts` preserving each agent's
  raw verdict text alongside the normalized canonical form.
- Preserve blockers / must-fix items VERBATIM in body.
- Preserve decision options + rationale, unresolved disagreements,
  file paths, concrete evidence.
- Dedupe overlapping findings across agents; cite all sources.
- Keep highest confidence among duplicates.
- Sort findings: BLOCKER → WARNING → SUGGESTION;
  HIGH → MEDIUM → LOW within bucket.
- Preserve "Pre-existing Issues" section.

## Artifact Recovery

For each reviewer in the manifest, stat the expected path:

| State | Action | Manifest agent status |
|---|---|---|
| Exists, `size_bytes >= 1000` | Trust. Do NOT overwrite. | `artifact` |
| Exists, `size_bytes < 1000`, return text substantially larger AND parses as findings (severity tags, `file:line` refs) | Replace stub with extracted findings. Add header `recovery: stub replaced from inline return`. | `stub-replaced` |
| Exists, `size_bytes < 1000`, return text empty/unusable | Keep stub. Add header `recovery: stub kept — return text unusable`. Treat as coverage gap. | `stub-no-output` |
| Missing, return text usable | Extract findings from return text and write. Add header `recovery: recovered from inline return — Write failed`. | `recovered-from-return` |
| Missing, return text empty/unusable | Write stub with heading `# {agent-slug} — recovery stub` and body `Run produced no artifact and no usable return text. Reviewer coverage gap.` Add header `recovery: stub written — agent produced nothing`. | `stub-no-output` |

Rules:

- Decide from the filesystem, not Agent return text claims.
- NEVER copy or symlink prior-run artifacts to the current-run path.
  Each run owns a per-second-unique path. If current run produced
  nothing, write a stub — never pull bytes from sibling runs.
- Never re-spawn.
- After each agent's recovery decision, patch its `status` via
  `printf '{"agents":{"%s":{"status":"%s"}}}\n' "$AGENT_SLUG" "$STATE" |
  ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch "$MANIFEST"`. NEVER
  edit `RUN-CURRENT.json` directly.
- Synthesis runs on the verified manifest.

## Resume Protocol

Single helper call at fanout entry:

```bash
MANIFEST=$(${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run \
  --skill=rb:review --slug="$REVIEW_SLUG" \
  --base-ref="$BASE_REF" \
  --agents="$AGENTS_CSV")
```

`$AGENTS_CSV` is the comma-separated list of reviewer slugs computed
by the skill body from the Reviewer Selection Matrix above. Not a
fixed default.

Helper computes manifest path, datesuffix, agent paths, consolidated
path, git pins. Archives any prior manifest. Outputs absolute
manifest path on stdout.

Schema + per-skill staleness rules:
`${CLAUDE_PLUGIN_ROOT}/references/run-manifest.md`.

## Severity Levels

| Severity | Description | Action |
|----------|-------------|--------|
| **BLOCKER** | Must fix before merge — Iron Law violations, security vulnerabilities, data-loss risks, production-outage risks, critical correctness | Surface in chat with one-line impact |
| **WARNING** | Should fix — performance issues, maintainability problems, potential bugs | Note in review with recommendation |
| **REQUIRES CHANGES** (verdict only) | Code works but new public behavior lacks test coverage | List affected methods/endpoints/jobs |
| **SUGGESTION** | Style, refactor, or doc improvements | Brief note, no action required |

## Worker Severity Mapping

Reviewer agents emit `Critical | Warning | Info`. Synthesis maps each
finding into a consolidated bucket using this rule table:

| Worker output | Diff status | Consolidated bucket |
|---|---|---|
| Critical | introduced by this diff | BLOCKER |
| Critical | unchanged code | Pre-existing BLOCKER (report; do not affect verdict) |
| Warning | any | WARNING |
| Info | any | SUGGESTION |
| New public behavior without tests | any | REQUIRES CHANGES verdict trigger (not a per-finding bucket) |

Worker prompts keep `Critical | Warning | Info` for backward
compatibility. Consolidated artifacts use `BLOCKER | WARNING |
SUGGESTION` and the verdict-only `REQUIRES CHANGES`.

## Review Scope

Review is **findings-only**. Do NOT:

- Create task lists (`- [ ]`)
- Add fix phases to plan files
- Modify any files outside `.claude/reviews/`
- Start fixing issues

Task creation and planning happen in `/rb:triage` after the user decides.

## Pre-existing Issues

Findings on code NOT changed in this diff are marked **Pre-existing**. They
appear in the report and summary table but do NOT affect the verdict. A PASS
verdict is possible with pre-existing blockers as long as no NEW blockers
were introduced by this diff.

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
| {agent-slug} | artifact \| stub-replaced \| recovered-from-return \| stub-no-output | {n} BLOCKER / {n} WARNING / {n} SUGGESTION |

Findings column uses bucket form (BLOCKER / WARNING / SUGGESTION),
zero-padded when the reviewer produced none in a bucket. State
definitions: `artifact` = on-disk file ≥ 1000 bytes, trusted as-is.
`stub-replaced` = on-disk stub overwritten with substantially larger
findings from agent return text. `recovered-from-return` = no on-disk
artifact; findings extracted from agent return text. `stub-no-output` =
no usable reviewer output; reviewer coverage gap.

## Reviewer Verdicts

| Reviewer | Raw verdict | Canonical |
|---|---|---|
| {agent-slug} | {agent's verbatim verdict text} | PASS \| PASS WITH WARNINGS \| REQUIRES CHANGES \| BLOCKED |

Raw verdict preserves the agent's wording exactly. Canonical column
normalizes it via the table in § "STEP 2" so reviewers reading the
artifact see one vocabulary. The consolidated verdict in § "STEP 4"
is computed from blocker / warning / test-coverage counts, NOT from
this column — Reviewer Verdicts is transparency metadata, not
algorithm input.

## Summary

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
**Confidence**: HIGH | MEDIUM | LOW
**Suggestion**: {improvement}

## Pre-existing Issues (unchanged code)

- {issue} (not introduced by this change)

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | {title} | BLOCKER \| WARNING \| SUGGESTION | HIGH \| MEDIUM \| LOW | {agent} | {path}:{line} | Yes \| Pre-existing |
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
Review complete. No blockers found.
Ready for: /rb:learn (capture lessons) or /rb:compound (capture solution).
```

**PASS WITH WARNINGS:**

```text
Review complete. {n} warnings noted.
Warnings logged but not blocking.
Ready for: /rb:learn or /rb:compound.
```

**REQUIRES CHANGES:**

```text
Review found {n} test-coverage gaps:

1. {Method/endpoint/job} in {file} — no test coverage
2. {Method/endpoint/job} in {file} — no test coverage

How would you like to proceed?

- /rb:plan — Plan tests for these
- /rb:work — Write tests directly
- I'll handle it myself
```

**BLOCKED:**

```text
Review found {n} blockers ({n} warnings):

1. {Blocker title} — {one-line impact}
2. {Blocker title} — {one-line impact}

How would you like to proceed?

- /rb:triage .claude/reviews/{review-slug}-{datesuffix}.md — Select findings, create fix plan
- /rb:work — Fix directly (best for simple, isolated fixes)
- I'll handle it myself
```

Always enumerate actual findings — never just show a count.

## Deduplication Strategy

When multiple agents find the same issue:

1. Merge into single finding
2. Cite all agents who found it
3. Use most specific description
4. Keep highest severity
5. List all affected lines
