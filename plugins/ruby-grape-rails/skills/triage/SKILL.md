---
name: rb:triage
description: "Use when triaging review findings interactively. Use after /rb:review when you want a human decision on what to fix now, skip, or defer. Prioritizes Iron Law violations and separates critical fixes from optional improvements."
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
│ • BLOCKER       │ → always include
│ • WARNING       │ → recommend (ask user)
│ • SUGGESTION    │ → defer (ask user)
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

### Step 1: Load Review File

```ruby
# Parse the review markdown file
def load_review(path)
  content = File.read(path)
  findings = parse_findings(content)
  
  {
    file: path,
    findings: findings,
    metadata: extract_metadata(content)
  }
end
```

### Step 2: Auto-Categorize

Read the review's existing severity bucket
(`BLOCKER | WARNING | SUGGESTION`) and map to triage priority:

```ruby
def categorize_finding(finding)
  case finding[:severity]
  when "BLOCKER"
    :always_include
  when "WARNING"
    if finding[:type] =~ /style|formatting|rubocop/i
      :defer
    else
      :recommend
    end
  when "SUGGESTION"
    :defer
  else
    :recommend
  end
end
```

Pre-existing BLOCKERs (per `New?` column) stay informational — do NOT
auto-include them in the fix plan.

### Step 3: Group Findings

```ruby
def group_findings(findings)
  findings.group_by do |f|
    # Group by file and type for batch fixing
    [
      f[:file],
      f[:category],
      f[:rule_id]
    ]
  end
end
```

### Step 4: Present to User with Structured Multi-Select

Illustrative expected UI:

```
╔══════════════════════════════════════════════════════════════╗
║  TRIAGE: Review Findings                                     ║
║  Source: .claude/reviews/fix-auth-20260505-103000.md                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🔴 BLOCKER (Auto-selected)                                  ║
║  ─────────────────────────────────────────────────────────   ║
║  [✓] app/models/user.rb:45 - Missing transaction wrap        ║
║       Iron Law 5: Transaction Boundaries                     ║
║                                                              ║
║  [✓] app/jobs/email_job.rb:12 - Passing AR object to job     ║
║       Iron Law 10: Pass IDs, not records                     ║
║                                                              ║
║  [✓] app/controllers/orders_controller.rb:23 - N+1 Query     ║
║       Iron Law 3: Use includes/preload                       ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║  3 BLOCKERs (automatically included)                         ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🟠 WARNING (Recommended)                                    ║
║  ─────────────────────────────────────────────────────────   ║
║  [✓] app/services/payment.rb:34 - Bare rescue                ║
║       Iron Law 18: Rescue StandardError, not Exception       ║
║                                                              ║
║  [ ] app/models/order.rb:89 - Missing test for edge case     ║
║       Refund logic has no regression coverage                ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║  1 of 2 selected                                             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🟡 WARNING (Optional)                                       ║
║  ─────────────────────────────────────────────────────────   ║
║  [ ] app/helpers/formatting.rb:12 - Method too long          ║
║       45 lines                                               ║
║                                                              ║
║  [ ] app/models/user.rb:23 - Could use delegate              ║
║       Redundant wrapper method                               ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║  0 of 2 selected                                             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🟢 SUGGESTION (Defer)                                       ║
║  ─────────────────────────────────────────────────────────   ║
║  [ ] app/views/layouts/application.html.erb:5 - Quotes       ║
║       Single vs double quotes                                ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║  0 of 1 selected (will be excluded)                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

Use `AskUserQuestion` with `multiSelect: true`.

Do **not** ask the user to type `confirm`, `drop W2`, or other freeform selection commands if structured selection is available.

Rules:

- auto-include all BLOCKER findings before asking
- offer bucket shortcuts first (BLOCKER / WARNING / SUGGESTION)
- then list individual findings
- if there are more than 6 selectable items, batch them into multiple `AskUserQuestion` screens
- each option description must include file, line, and a one-line reason

Example:

```yaml
AskUserQuestion:
  header: "Triage"
  multiSelect: true
  question: "Which non-BLOCKER findings do you want to fix now? BLOCKERs are already included."
  options:
    - label: "All WARNING (2)"
      description: "Include all WARNING findings"
    - label: "All SUGGESTION (2)"
      description: "Include all SUGGESTION findings"
    - label: "W1 Bare rescue"
      description: "app/services/payment.rb:34 — catches broad exceptions"
    - label: "W2 Missing edge-case test"
      description: "app/models/order.rb:89 — refund path lacks regression coverage"
    - label: "S1 Method too long"
      description: "app/helpers/formatting.rb:12 — 45 lines"
    - label: "S2 Could use delegate"
      description: "app/models/user.rb:23 — redundant wrapper method"
```

Summarize selection state back to the user:

- auto-included: `B1 B2 B3` (BLOCKERs)
- selected: `W1`
- deferred: `W2 S1 S2`

### Step 5: Write Triage Output

The plan should be saved to `.claude/plans/{slug}/plan.md`:

```markdown
# Plan: Fix auth review findings

## Metadata
- Created: 2024-01-15T10:30:00Z
- Source Review: .claude/reviews/fix-auth-20260505-103000.md
- Generated By: /rb:triage
- Triaged By: user

## Summary

| Bucket | Total | Selected | Deferred | Excluded |
|---|---|---|---|---|
| BLOCKER | 3 | 3 | 0 | 0 |
| WARNING | 4 | 1 | 3 | 0 |
| SUGGESTION | 1 | 0 | 0 | 1 |
| **Total** | **8** | **4** | **3** | **1** |

## Phase 1: Blockers

- [ ] Fix transaction wrap in `app/models/user.rb:45`
  - Rule: Iron Law - Transaction Safety
  - Source: .claude/reviews/fix-auth-20260505-103000.md
  - Estimated effort: 15 minutes

- [ ] Fix JSON-safe args in `app/jobs/email_job.rb:12`
  - Rule: Iron Law - JSON-Safe Arguments
  - Source: .claude/reviews/fix-auth-20260505-103000.md
  - Estimated effort: 10 minutes

- [ ] Fix N+1 query in `app/controllers/orders_controller.rb:23`
  - Rule: Query Performance
  - Source: .claude/reviews/fix-auth-20260505-103000.md
  - Estimated effort: 5 minutes

## Phase 2: Warnings (selected)

- [ ] Replace bare rescue in `app/services/payment.rb:34`
  - Rule: Error Handling
  - Source: .claude/reviews/fix-auth-20260505-103000.md
  - Estimated effort: 10 minutes

## Deferred Findings

### Warnings (Deferred)

- app/models/order.rb:89 - Missing test for edge case
  - Reason: Requires clarification on expected behavior
  - Action: Schedule separate testing session
- app/helpers/formatting.rb:12 - Method too long
- app/models/user.rb:23 - Could use delegate

### Suggestions (Excluded)

- app/views/layouts/application.html.erb:5 - Quote style

## Next Steps

1. Run `/rb:work` to fix the 4 selected items
2. Estimated time: 40 minutes
3. Review deferred items in future sprint
```

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

```
[Select All BLOCKER]
[Select All WARNING]
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
| `select all blockers` | Auto-select all BLOCKER findings |
| `group by file` | Reorganize display by file |
| `export` | Export triage to issue tracker |
| `skip all` | Exclude all findings |

## References

| Need | Reference |
|---|---|
| auto-approve / usually-fix / often-skip rules + severity reclassification | `${CLAUDE_SKILL_DIR}/references/triage-patterns.md` |

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
