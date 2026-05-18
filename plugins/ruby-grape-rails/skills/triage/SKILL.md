---
name: rb:triage
description: "Triaging review findings: pick fix now, skip, or defer. Prioritizes Blocker (Iron Law violations, security). Triggers: \"triage\", \"which to fix\", \"prioritize findings\"."
argument-hint: "[path to review file]"
effort: low
---
# Triage Review Findings

Batch-select findings from the review before creating follow-up work.

## Iron Laws

1. **Auto-include all Iron Law violations** - these are never optional
2. **Separate safety fixes from style preferences** - prioritize data integrity
3. **Group related findings** - fix together what belongs together
4. **Defer performance optimizations** without profiling data
5. **Use structured multi-select, not freeform chat prompts** — when asking the user which findings to keep, use a checkbox-style selection UI

## Workflow

```
Review File
    ↓
Parse Findings (Blocker / Warning / Suggestion)
    ↓
┌─────────────────┐
│ Auto-Categorize │
├─────────────────┤
│ • Blocker       │ → always include (auto, never optional)
│ • Warning       │ → recommend (default selected; user may defer)
│ • Suggestion    │ → defer (default unselected; user may include)
└─────────────────┘
    ↓
Present Grouped Findings
    ↓
User Selects Items
    ↓
Write Triage Output
    ↓
Next Action
```

## Severity Classification

Map review buckets (`Blocker | Warning | Suggestion`) to triage
priorities. Within each bucket, order **security findings only** by
`evidence_mode` (defined in
`${CLAUDE_PLUGIN_ROOT}/skills/security/SKILL.md` § "Evidence Mode" and
`${CLAUDE_PLUGIN_ROOT}/agents/security-analyzer.md` § "Evidence Mode (mandatory)"):

1. `runtime-confirmed` — act first
2. `configuration-risk`
3. `static-signal`
4. `requires-human-validation` — surface to user for decision

Non-security findings carry no `evidence_mode`. Retain agent-emitted
order within the bucket.

### Blocker → Always Include

- **Iron Law violations**: transaction safety, after_commit discipline, JSON-safe args
- **Security issues**: SQL injection, XSS, mass assignment, hardcoded secrets
- **Data integrity**: missing constraints, race conditions, incorrect null handling
- **N+1 queries**: database performance killers
- **Transaction safety**: operations outside transactions that should be inside

### Warning → Recommend Include

- **Error handling (non-Iron-Law)**: missing error handling on external API calls (bare `rescue` / `rescue Exception` is Iron Law 18 → Blocker, not Warning)
- **Test coverage**: missing tests for critical paths
- **API contract**: breaking changes to public APIs
- **Documentation**: missing docs for public methods
- **Refactoring opportunities**: complex methods, Law of Demeter violations
- **Naming**: unclear variable/method names

### Suggestion → Defer by Default

- **Code style**: inconsistent formatting (if not auto-fixable)
- **Performance**: without profiling evidence
- **Micro-optimizations**: minor efficiency gains
- **Subjective preferences**: personal style differences
- **Future-proofing**: speculative abstractions
- **Comments**: missing or misleading comments

## Triage Process

Follow these 5 steps. Each reads from the review artifact, classifies
via review bucket, writes selected items to a fix plan.

### Step 1: Load Review File

Argument resolution FIRST. Triage operates ONLY on a consolidated
review artifact (no plain description / no feature input):

| `$ARGUMENTS` shape | Action |
|---|---|
| empty / absent | Resolve newest consolidated review: glob `.claude/reviews/*-*.md`, EXCLUDE `.provenance.md` sidecars (suffix `-{datesuffix}.provenance.md`) — accept only files whose basename ends in `-{datesuffix}.md` with no `.provenance` segment. Direct children of `reviews/` only (no per-reviewer subdirectory). Pick the file with the most recent mtime. If none found, STOP. Print: `No consolidated review artifact found under .claude/reviews/. Run /rb:review first.` |
| `.claude/reviews/{review-slug}-{datesuffix}.md` (direct child of `reviews/`) | proceed |
| `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md` (per-reviewer artifact under subdirectory) | STOP. Print: `Path is a per-reviewer artifact, not the consolidated review. Run with the consolidated path: .claude/reviews/{review-slug}-{datesuffix}.md` |
| `.claude/reviews/{review-slug}/RUN-CURRENT.json` (manifest) | STOP. Print: `Path is the manifest, not the consolidated review.` |
| anything else (plain text, non-review path) | STOP. Print: `/rb:triage operates on a consolidated review artifact. Run /rb:plan {description} for feature planning, or /rb:review first to produce a review artifact.` |

After argument resolution passes, read the consolidated review markdown.

| Source section | Extract |
|---|---|
| Preamble | `**Date**:`, `**Complexity**:`, `**Files Changed**:`, `**Reviewers**:` (metadata) |
| `## Reviewer Coverage` | Per-reviewer recovery state + finding counts |
| `## Reviewer Verdicts` | Per-reviewer raw + canonical verdicts |
| `## Summary` (then `**Verdict**:` line immediately AFTER the Summary table per `${CLAUDE_PLUGIN_ROOT}/skills/review/references/review-playbook.md` § "Consolidated Review Format") | Severity counts + consolidated verdict |
| `## At-a-Glance Finding Table` | Per-finding row: `# / Finding / Severity / Confidence / Reviewer / File / New?` |
| `## Blockers ({n})` / `## Warnings ({n})` / `## Suggestions ({n})` | Detailed finding bodies: `**File**:`, `**Reviewer**: ... \| **Confidence**:`, `**Issue**:`, `**Why it matters**:` (Blockers only), `**Current**:` + `**Suggested**:` (Blockers code blocks), `**Recommendation**:` (Warnings) or `**Suggestion**:` (Suggestions) |
| `## Pre-existing Issues (unchanged code)` | Findings to surface in plan's `## Pre-existing Issues (informational)` only |
| `## Test Coverage Gaps ({n})` (REQUIRES CHANGES verdict only) | One row per uncovered NEW public surface; columns `# / Surface / File / Why uncovered / Suggested test`. Step 2b + Step 5 auto-include each row as a Phase 1 `[test]` task. |

For NEW At-a-Glance rows (`New? = Yes`), match each row to its
detailed finding by the `Finding` column text — the At-a-Glance
`Finding` cell MUST equal the `### N. {Title}` heading under the
appropriate `## Blockers` / `## Warnings` / `## Suggestions`
section verbatim. Use `(File, Reviewer, Severity)` as a
corroboration tuple. Title text disambiguates the case where one
reviewer reports two findings of the same bucket against the same
path; the tuple alone is ambiguous in that case. The Iron Law
label for THIS NEW row's plan task line comes from the issue text
combined with the `iron-laws.yml` registry (e.g., "Multi-step
operations without transaction wrap" → Iron Law 5).

Pre-existing At-a-Glance rows (`New? = Pre-existing`) have NO
backing `### N. {Title}` heading — `## Pre-existing Issues
(unchanged code)` lists them as bullets, not headings. The
`Finding` cell carries a concise description of the unchanged-code
issue. Surface them in the plan's `## Pre-existing Issues
(informational)` section unchanged; do NOT attempt the
title-verbatim match. Pre-existing findings NEVER produce a plan
task line, so NO Iron Law label / `[annotation]` / `[Pn-Tm]` is
derived for them — Step 5 emits them as bullets, not as `- [ ]`
checkboxes (per Step 2 + Step 5 contract).

The plan's `[annotation]` value MUST be one of the canonical Set A
entries per `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/planning-workflow.md`
§ "Plan Generation":

| Annotation | Use for |
|---|---|
| `[direct]` | most common — generic Ruby work, refactors, glue |
| `[active record]` | models, migrations, ORM-touching findings |
| `[hotwire]` | Turbo Streams, Frames, Stimulus, broadcasts |
| `[sidekiq]` | jobs, queues, Sidekiq-specific findings |
| `[concurrency]` | threads, fibers, async, race conditions |
| `[security]` | auth, SQL injection, XSS, secrets, authorization |
| `[test]` | spec / test additions or fixes |

Do NOT emit `[ruby]`, `[testing]`, `[grape]`, `[ar]`, `[sequel]`,
`[perf]`, or `[general-purpose]` — those are descriptive narrative
labels (or subagent type names), not plan-task annotations, per
`planning-workflow.md` § "Plan-Task Annotations Cross-Reference".
Do NOT use the underscore form from `iron-laws.yml` `category:`
field. `/rb:work` parser routes on the canonical Set A only.

### Step 2: Auto-Categorize via Review Bucket

Read each finding's bucket (`Blocker | Warning | Suggestion`) AND
its `New?` column. Apply this filter FIRST:

- `New? = Pre-existing` → informational only; never auto-include,
  never offer in selection UI. List under a separate "Pre-existing
  Issues" section in the fix plan for context.
- `New? = Yes` → proceed to bucket-based categorization below.

For NEW findings:

- Blocker → always include (auto-selected, never optional)
- Warning → recommend (default selected; user may defer)
- Suggestion → defer (default unselected; user may include)

### Step 2b: Verdict gate + Phase 1 auto-include source

| Consolidated `**Verdict**:` | Phase 1 source (auto-include) |
|---|---|
| `BLOCKED` | every NEW Blocker row from At-a-Glance + matched `## Blockers` detail |
| `REQUIRES CHANGES` | every row from `## Test Coverage Gaps ({n})` |
| `PASS WITH WARNINGS` / `PASS` | none — Phase 1 heading omitted entirely |

BLOCKED + REQUIRES CHANGES are mutually exclusive per playbook
STEP 4 (BLOCKED requires blockers > 0; REQUIRES CHANGES requires
blockers == 0). One source populates Phase 1, never both.

Gap row → Phase 1 task line shape (REQUIRES CHANGES only):

```text
- [ ] [P1-T{n}][test] Add spec for {Surface} — test-coverage gap
  (REQUIRES CHANGES); source {review-path}
```

`/rb:plan {review-path}` is the gaps-only entrypoint (no selection
UI). `/rb:triage` is the default; covers all mixed cases.

### Step 3: Group Findings

Group NEW findings by `[file, bucket]` so batch-fixable items appear
together in the selection UI. The review artifact does NOT carry a
stable `rule_id`; do not invent one.

### Step 4: Present Multi-Select UI

Use `AskUserQuestion` with `multiSelect: true`. Auto-include rules
per Step 2b verdict gate:

| Verdict | Auto-include (no UI) | Present in selection UI |
|---|---|---|
| `BLOCKED` | every NEW Blocker (`B<n>`) | NEW Warnings (`W<n>`), NEW Suggestions (`S<n>`) |
| `REQUIRES CHANGES` | every Test Coverage Gap row (`G<n>`) | NEW Warnings (`W<n>`), NEW Suggestions (`S<n>`) |
| `PASS WITH WARNINGS` / `PASS` | none | NEW Warnings (`W<n>`), NEW Suggestions (`S<n>`) |

Never surface pre-existing findings in the selection UI. Drive
selection entirely through `AskUserQuestion` options; never accept
freeform-typed commands. Present this option set in the multi-select
prompt, bucket shortcuts first then individual items:

| Option label | Effect |
|---|---|
| `All Warnings` | Select every NEW Warning finding. Leave Suggestions selections untouched. |
| `All Suggestions` | Select every NEW Suggestion finding. Leave Warnings selections untouched. |
| `Skip all Warnings` | Defer every NEW Warning finding. Leave Suggestions selections untouched. |
| `Skip all Suggestions` | Defer every NEW Suggestion finding. Leave Warnings selections untouched. |
| `Group by file` | Re-render the option list grouped by file. Do NOT change selection state. |
| `W<n>` / `S<n>` (one row per finding) | Select the individual NEW Warning / Suggestion. Description: file, line, one-line reason. |

Accept combinations of shortcuts and individual picks in one
response (e.g., `All Warnings` + `S2` + `S5`). Resolve combinations
in selection order: cancel an earlier `All Warnings` when a later
`Skip all Warnings` follows; let individual `W<n>` / `S<n>` picks
override their bucket-level skip. Split into multiple screens when
> 6 selectable items.

Summarize state back, e.g.:
`auto-included: B1 B2 B3 | selected: W1 | deferred: W2 S1 S2`
or for REQUIRES CHANGES:
`auto-included: G1 G2 | selected: W1 | deferred: W2 S1`.

### Step 5: Write Triage Output

Save the plan to `.claude/plans/{slug}/plan.md` using the canonical
template at
`${CLAUDE_SKILL_DIR}/references/triage-plan-template.md`. Emit the
template's full surface in this order:

1. `# Plan: {slug}` heading.
2. `**Status**: IN_PROGRESS` / `**Created**` / `**Last Updated**`
   preamble (per `${CLAUDE_PLUGIN_ROOT}/skills/work/references/file-formats.md`
   so `/rb:work` parses + resumes correctly).
3. `## Metadata` (Source Review, Generated By, Triaged By).
4. `## Summary` table (Bucket / Total / Selected / Deferred / Excluded).
5. Phase 1 (auto-include; heading per Step 2b verdict gate):
   - `## Phase 1: Blockers [PENDING]` (BLOCKED verdict) — task lines `- [ ] [P1-Tn][annotation] ...` per NEW Blocker.
   - `## Phase 1: Test Coverage Gaps [PENDING]` (REQUIRES CHANGES verdict) — task lines `- [ ] [P1-Tn][test] ...` per gap row.
   - Phase 1 heading OMITTED entirely for PASS / PASS WITH WARNINGS verdicts (no auto-include source).
6. `## Phase 2: Warnings (selected) [PENDING]` — task lines `- [ ] [P2-Tn][annotation] ...` (only NEW Warnings the user selected at Step 4). Omit the heading when zero warnings selected.
7. `## Phase 3: Suggestions (selected) [PENDING]` — task lines
   `- [ ] [P3-Tn][annotation] ...` (only NEW Suggestions the user
   selected via `S<n>` at Step 4). Omit the entire phase heading
   when zero suggestions selected.
8. `## Deferred Findings` (NEW Warnings + Suggestions the user did NOT select; excluded entirely from any Phase).
9. `## Pre-existing Issues (informational)` — every `New? = Pre-existing`
   finding from Step 1, file + line + reviewer + one-line note. NEVER
   emit as `- [ ]` task lines.
10. `## Next Steps` — `/rb:work` invocation, time estimate, deferred-review note.

## Decision Tree

Read the review's existing bucket per finding. Override only when
the bucket is missing or ambiguous:

```
Review bucket = Blocker?
├── YES → always include
│         └── never optional
│
└── NO → bucket = Warning?
          ├── YES → recommend (default selected; user can defer)
          │
          └── NO → bucket = Suggestion?
                    ├── YES → defer (default unselected; user can include)
                    │
                    └── NO → bucket missing / ambiguous → ask user
```

## Batch Operations

### Select All in Bucket

Blockers are auto-included by Step 4; do NOT surface a "Select All
Blocker" shortcut in the selection UI. Offer only Warning /
Suggestion + cross-cutting filters:

```
[Select All Warnings]
[Select All Suggestions]
[Select All in File: app/models/user.rb]
[Select All of Type: N+1]
```

### Smart Grouping

Bucketize findings via reasoning, not by running code. Step 3
already pins the primary key: group NEW findings by
`(file, bucket)`. Review artifacts carry no stable identifier
beyond that tuple — do NOT invent one.

| Grouping rule | Effect on selection UI |
|---|---|
| Same `(file, bucket)` with ≥ 2 occurrences | Surface together; recommend `fix_together` |
| Findings touching the same domain layer (e.g., 2+ in `app/models/*`) | Optional cross-cutting shortcut (e.g., "Select All in app/models/"); recommend `fix_sequentially` |
| Different buckets in same file | Keep separate — auto-include / recommend / defer follows the bucket, not the file |

## Integration with Workflow

### From Review

```
# After review completes
/rb:review app/models/user.rb
# → Creates `.claude/reviews/{review-slug}-{datesuffix}.md`

# Then triage
/rb:triage .claude/reviews/fix-user-model-20260505-123000.md
# → Creates .claude/plans/fix-user-model/plan.md

# Then work on selected items
/rb:work .claude/plans/fix-user-model/plan.md
```

### Direct to Work

If triage generated a plan with selected Blocker items:

```
/rb:work .claude/plans/fix-user-model/plan.md
# → Works on the selected findings as normal plan tasks
```

## Edge Cases

### Empty Selection

If user selects nothing:

```
No findings selected. Options:
[Review All Findings Again]
[Create Note: "Reviewed, no action needed"]
[Cancel]
```

### All Blockers

If all findings are Blockers:

```
All 5 findings are Blockers and must be addressed.
Estimated time: 2 hours

[Start Work]
```

`[Start Work]` invokes `/rb:work` against the generated plan.

### Contradictory Findings

If findings conflict:

```
⚠️ Warning: Contradictory findings detected

Finding A: "Extract method to reduce complexity"
Finding B: "Inline method for clarity"

These may conflict. Review together?
[Review Both] [Skip Both]
```

## Output Format

Sole output: `.claude/plans/{slug}/plan.md`. Tasks MUST use the
canonical `- [ ] [Pn-Tm][annotation] ...` format from
`${CLAUDE_PLUGIN_ROOT}/skills/work/references/file-formats.md` +
canonical Set A annotations from
`${CLAUDE_PLUGIN_ROOT}/skills/plan/references/planning-workflow.md`
§ "Plan Generation". `/rb:work` parser routes on this format and
resumes via `--from Pn-Tm`.

Example for BLOCKED verdict (Phase 1 = Blockers):

```markdown
# Creates `.claude/plans/{slug}/plan.md` with selected findings as tasks

## Phase 1: Blockers [PENDING]

- [ ] [P1-T1][active record] Fix transaction wrap in `User.create_with_profile` — Iron Law 5
- [ ] [P1-T2][sidekiq] Fix JSON-safe args in `EmailJob#perform` — Iron Law 9
- [ ] [P1-T3][active record] Fix N+1 in `OrdersController#index` — Iron Law 3

## Phase 2: Warnings (selected) [PENDING]

- [ ] [P2-T1][test] Add edge-case spec for `PaymentService` refund branch

## Phase 3: Suggestions (selected) [PENDING]

- [ ] [P3-T1][direct] Extract `RETRY_LIMIT` constant in `SyncService`
```

Example for REQUIRES CHANGES verdict (Phase 1 = Test Coverage Gaps):

```markdown
# Creates `.claude/plans/{slug}/plan.md` with selected findings as tasks

## Phase 1: Test Coverage Gaps [PENDING]

- [ ] [P1-T1][test] Add spec for `PasswordsController#create` — test-coverage gap (REQUIRES CHANGES); source .claude/reviews/...md
- [ ] [P1-T2][test] Add spec for `PasswordsController#create` 429 throttle branch — test-coverage gap (REQUIRES CHANGES); source .claude/reviews/...md
```

Phase 1 heading is OMITTED entirely for PASS / PASS WITH WARNINGS
verdicts. Phase 2 + Phase 3 headings are OMITTED when zero items
selected at Step 4.

## Best Practices

1. **Always explain why** a finding is Blocker
2. **Show estimated effort** for each item
3. **Group by location** when possible for efficient fixing
4. **Preserve excluded items** for future reference
5. **Link to documentation** for Iron Law violations
6. **Suggest alternatives** for deferred items (e.g., "Use RuboCop auto-fix")

## Commands

| Command | Description |
|---------|-------------|
| `/rb:triage` | Triage most recent consolidated review |
| `/rb:triage <file>` | Triage specific review file |

For in-UI bucket shortcuts (`All Warnings`, `Skip all Warnings`,
`Group by file`, …), surface them as `AskUserQuestion` option labels
per § "Step 4: Present Multi-Select UI"; never prompt the user to
type them as commands.

## References

| Need | Reference |
|---|---|
| auto-approve / usually-fix / often-skip rules + severity reclassification | `${CLAUDE_SKILL_DIR}/references/triage-patterns.md` |
| canonical fix-plan output template (Step 5 destination format) | `${CLAUDE_SKILL_DIR}/references/triage-plan-template.md` |

## Trust States

When triaging a review with a provenance sidecar, read the sidecar's
`trust_state` (see
`${CLAUDE_PLUGIN_ROOT}/references/output-verification/trust-states.md`):

- `conflicted`: surface findings in a dedicated section labeled
  "Conflicted evidence — resolve before triage".
- `missing`: tag each finding `[unverified]`; treat as hint, not
  decision.
- `weak`: include findings but sort after `runtime-confirmed`
  evidence.
- `clean`: proceed with normal triage.

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Adversarial review needed → `/rb:challenge` (adversarial-mode review)
- PR review comments to address → `/rb:pr-review` (PR review-comment handling)
<!-- END-GENERATED related-footer -->
