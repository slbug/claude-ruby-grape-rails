---
name: rb:triage
description: "Use when triaging review findings interactively. Use after /rb:review to decide what to fix now, skip, or defer in a Ruby/Rails project. Prioritizes BLOCKER findings (Iron Law violations, security risks, migration safety) and routes selected items into a fix plan for /rb:work."
when_to_use: "Triggers: \"triage\", \"which to fix\", \"prioritize findings\", \"after review\"."
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
Parse Findings (BLOCKER / WARNING / SUGGESTION)
    ↓
┌─────────────────┐
│ Auto-Categorize │
├─────────────────┤
│ • BLOCKER       │ → always include (auto, never optional)
│ • WARNING       │ → recommend (default selected; user may defer)
│ • SUGGESTION    │ → defer (default unselected; user may include)
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

Map review buckets (`BLOCKER | WARNING | SUGGESTION`) to triage
priorities:

### BLOCKER → Always Include

- **Iron Law violations**: transaction safety, after_commit discipline, JSON-safe args
- **Security issues**: SQL injection, XSS, mass assignment, hardcoded secrets
- **Data integrity**: missing constraints, race conditions, incorrect null handling
- **N+1 queries**: database performance killers
- **Transaction safety**: operations outside transactions that should be inside

### WARNING → Recommend Include

- **Error handling**: bare rescues, silent failures
- **Test coverage**: missing tests for critical paths
- **API contract**: breaking changes to public APIs
- **Documentation**: missing docs for public methods
- **Refactoring opportunities**: complex methods, Law of Demeter violations
- **Naming**: unclear variable/method names

### SUGGESTION → Defer by Default

- **Code style**: inconsistent formatting (if not auto-fixable)
- **Performance**: without profiling evidence
- **Micro-optimizations**: minor efficiency gains
- **Subjective preferences**: personal style differences
- **Future-proofing**: speculative abstractions
- **Comments**: missing or misleading comments

## Triage Process

5 steps. Each reads from review artifact, classifies via review bucket,
writes selected items to a fix plan.

### Step 1: Load Review File

Read the consolidated review markdown.

| Source section | Extract |
|---|---|
| Preamble | `**Date**:`, `**Complexity**:`, `**Files Changed**:`, `**Reviewers**:`, `**Verdict**:` (metadata) |
| `## Reviewer Coverage` | Per-reviewer recovery state + finding counts |
| `## Reviewer Verdicts` | Per-reviewer raw + canonical verdicts |
| `## At-a-Glance Finding Table` | Per-finding row: `# / Finding / Severity / Confidence / Reviewer / File / New?` |
| `## Blockers ({n})` / `## Warnings ({n})` / `## Suggestions ({n})` | Detailed finding bodies: `**File**:`, `**Reviewer**: ... \| **Confidence**:`, `**Issue**:`, `**Why it matters**:`, `**Current**:`, `**Suggested**:`, `**Recommendation**: \| Suggestion:` |
| `## Pre-existing Issues (unchanged code)` | Findings to surface in plan's `## Pre-existing Issues (informational)` only |

Match each At-a-Glance row to its detailed finding by `File` cell.
The Iron Law label for the plan's task line comes from the issue
text + `iron-laws.yml` registry (e.g., "Multi-step operations
without transaction wrap" → Iron Law 5). The plan's `[agent]`
annotation comes from the finding's reviewer slug or Iron Law
category. Emit annotation in space form per
`${CLAUDE_PLUGIN_ROOT}/skills/work/references/file-formats.md`:
`active record`, `sidekiq`, `security`, `ruby`, `hotwire`,
`direct`. Do NOT use the underscore form from `iron-laws.yml`
`category:` field — `/rb:work` parser routes on space form.

### Step 2: Auto-Categorize via Review Bucket

Read each finding's bucket (`BLOCKER | WARNING | SUGGESTION`) AND
its `New?` column. Apply this filter FIRST:

- `New? = Pre-existing` → informational only; never auto-include,
  never offer in selection UI. List under a separate "Pre-existing
  Issues" section in the fix plan for context.
- `New? = Yes` → proceed to bucket-based categorization below.

For NEW findings:

- BLOCKER → always include (auto-selected, never optional)
- WARNING → recommend (default selected; user may defer)
- SUGGESTION → defer (default unselected; user may include)

### Step 3: Group Findings

Group NEW findings by `[file, bucket]` so batch-fixable items appear
together in the selection UI. The review artifact does NOT carry a
stable `rule_id`; do not invent one.

### Step 4: Present Multi-Select UI

Use `AskUserQuestion` with `multiSelect: true`. Auto-include all
NEW BLOCKERs before asking; ask only about NEW WARNING + NEW
SUGGESTION items. Pre-existing findings are NOT presented for
selection.
Offer bucket shortcuts first (`All WARNING`, `All SUGGESTION`), then
individual items. Each option label uses prefix `B<n>` / `W<n>` /
`S<n>`; description includes file, line, one-line reason. Batch into
multiple screens when more than 6 selectable items exist. Do NOT ask
the user to type freeform selection commands.

Summarize state back: `auto-included: B1 B2 B3 | selected: W1 |
deferred: W2 S1 S2`.

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
5. `## Phase 1: Blockers [PENDING]` — task lines `- [ ] [P1-Tn][agent] ...`.
6. `## Phase 2: Warnings (selected) [PENDING]` — task lines `- [ ] [P2-Tn][agent] ...`.
7. `## Deferred Findings` (Warnings deferred + Suggestions excluded).
8. `## Pre-existing Issues (informational)` — every `New? = Pre-existing`
   finding from Step 1, file + line + reviewer + one-line note. NEVER
   emit as `- [ ]` task lines.
9. `## Next Steps` — `/rb:work` invocation, time estimate, deferred-review note.

## Decision Tree

Read the review's existing bucket per finding. Override only when
the bucket is missing or ambiguous:

```
Review bucket = BLOCKER?
├── YES → always include
│         └── never optional
│
└── NO → bucket = WARNING?
          ├── YES → recommend (default selected; user can defer)
          │
          └── NO → bucket = SUGGESTION?
                    ├── YES → defer (default unselected; user can include)
                    │
                    └── NO → bucket missing / ambiguous → ask user
```

## Batch Operations

### Select All in Bucket

BLOCKERs are auto-included by Step 4; do NOT surface a "Select All
BLOCKER" shortcut in the selection UI. Offer only WARNING /
SUGGESTION + cross-cutting filters:

```
[Select All WARNING]
[Select All SUGGESTION]
[Select All in File: app/models/user.rb]
[Select All of Type: N+1]
```

### Smart Grouping

```ruby
# Group findings that should be fixed together
def suggest_groups(findings)
  groups = []
  
  # Group by file + rule
  by_rule = findings.group_by { |f| [f[:file], f[:rule_id]] }
  by_rule.each do |(file, rule), items|
    if items.size > 1
      groups << {
        name: "#{file}: #{rule} (#{items.size} occurrences)",
        items: items,
        recommendation: :fix_together
      }
    end
  end
  
  # Group related files
  model_files = findings.select { |f| f[:file].include?('models') }
  if model_files.size > 1
    groups << {
      name: "Model Layer Improvements",
      items: model_files,
      recommendation: :fix_sequentially
    }
  end
  
  groups
end
```

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

If triage generated a plan with selected BLOCKER items:

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

### All BLOCKER

If all findings are BLOCKER:

```
All 5 findings are BLOCKERs and must be addressed.
Estimated time: 2 hours

[Start Work] [Schedule for Later] [Export to Issue Tracker]
```

### Contradictory Findings

If findings conflict:

```
⚠️ Warning: Contradictory findings detected

Finding A: "Extract method to reduce complexity"
Finding B: "Inline method for clarity"

These may conflict. Review together?
[Review Both] [Skip Both] [Ask Reviewer]
```

## Output Formats

### For Plan

```markdown
# Creates `.claude/plans/{slug}/plan.md` with selected findings as tasks

- [ ] Fix transaction wrap in User.create_with_profile
- [ ] Fix JSON-safe args in EmailJob
- [ ] Fix N+1 in OrdersController#index
- [ ] Fix bare rescue in PaymentService
```

### For Compound

```yaml
# If root cause analysis is needed
# Some findings may point to same root cause
type: compound_analysis
findings: [1, 3]
potential_root_cause: "Missing includes pattern across controllers"
```

## Best Practices

1. **Always explain why** a finding is BLOCKER
2. **Show estimated effort** for each item
3. **Group by location** when possible for efficient fixing
4. **Preserve excluded items** for future reference
5. **Link to documentation** for Iron Law violations
6. **Suggest alternatives** for deferred items (e.g., "Use RuboCop auto-fix")

## Commands

| Command | Description |
|---------|-------------|
| `/rb:triage` | Triage most recent review |
| `/rb:triage <file>` | Triage specific review file |
| `select all warnings` | Select all WARNING findings (BLOCKERs auto-included by Step 4) |
| `select all suggestions` | Select all SUGGESTION findings |
| `group by file` | Reorganize display by file |
| `export` | Export triage to issue tracker |
| `skip all warnings` | Defer all non-BLOCKER findings |

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
