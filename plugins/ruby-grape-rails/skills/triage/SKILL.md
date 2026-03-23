---
name: rb:triage
description: Interactive triage for review findings. Use after /rb:review when you want a human decision on what to fix now, skip, or defer. Prioritizes Iron Law violations and separates critical fixes from optional improvements.
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
Parse Findings
    ↓
┌─────────────────┐
│ Auto-Categorize │
├─────────────────┤
│ • Iron Law      │ → Critical (always include)
│ • Security      │ → High (always include)
│ • N+1           │ → High (always include)
│ • Style         │ → Low (ask user)
│ • Performance   │ → Low (needs evidence)
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

### Critical (Always Include)

- **Iron Law violations**: transaction safety, after_commit discipline, JSON-safe args
- **Security issues**: SQL injection, XSS, mass assignment, hardcoded secrets
- **Data integrity**: missing constraints, race conditions, incorrect null handling
- **N+1 queries**: database performance killers
- **Transaction safety**: operations outside transactions that should be inside

### High (Recommend Include)

- **Error handling**: bare rescues, silent failures
- **Test coverage**: missing tests for critical paths
- **API contract**: breaking changes to public APIs
- **Documentation**: missing docs for public methods

### Medium (Ask User)

- **Code style**: inconsistent formatting (if not auto-fixable)
- **Refactoring opportunities**: complex methods, Law of Demeter violations
- **Naming**: unclear variable/method names
- **Comments**: missing or misleading comments

### Low (Defer by Default)

- **Performance**: without profiling evidence
- **Micro-optimizations**: minor efficiency gains
- **Subjective preferences**: personal style differences
- **Future-proofing**: speculative abstractions

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

```ruby
def categorize_finding(finding)
  case finding[:type]
  when /iron.law|transaction|after_commit|json.safe/i
    :critical
  when /security|sql.injection|xss|vulnerability/i
    :critical
  when /n\+1|query.performance/i
    :critical
  when /error.handling|rescue|exception/i
    :high
  when /test.coverage|missing.test/i
    :high
  when /style|formatting|rubocop/i
    :low
  when /performance|optimization/i
    finding[:has_profiling_data] ? :medium : :low
  else
    :medium
  end
end
```

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
║  Source: .claude/reviews/fix-auth.md                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🔴 CRITICAL (Auto-selected)                                 ║
║  ─────────────────────────────────────────────────────────   ║
║  [✓] app/models/user.rb:45 - Missing transaction wrap        ║
║       Iron Law: Wrap related creates in transaction          ║
║                                                              ║
║  [✓] app/jobs/email_job.rb:12 - Passing AR object to job     ║
║       Iron Law: Pass IDs, not objects                        ║
║                                                              ║
║  [✓] app/controllers/orders_controller.rb:23 - N+1 Query     ║
║       50 queries where 2 would suffice                       ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║  3 critical issues (automatically included)                  ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🟠 HIGH (Recommended)                                       ║
║  ─────────────────────────────────────────────────────────   ║
║  [✓] app/services/payment.rb:34 - Bare rescue                ║
║       Catches broad exceptions                               ║
║                                                              ║
║  [ ] app/models/order.rb:89 - Missing test for edge case     ║
║       Refund logic has no regression coverage                ║
║                                                              ║
║  ─────────────────────────────────────────────────────────   ║
║  1 of 2 selected                                             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🟡 MEDIUM (Optional)                                        ║
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
║  🟢 LOW (Defer)                                              ║
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

- auto-include all Critical / Iron Law findings before asking
- offer severity shortcuts first
- then list individual findings
- if there are more than 6 selectable items, batch them into multiple `AskUserQuestion` screens
- each option description must include file, line, and a one-line reason

Example:

```yaml
AskUserQuestion:
  header: "Triage"
  multiSelect: true
  question: "Which non-critical findings do you want to fix now? Critical items are already included."
  options:
    - label: "All HIGH (2)"
      description: "Include all high-priority findings"
    - label: "All MEDIUM (2)"
      description: "Include all medium-priority findings"
    - label: "W1 Bare rescue"
      description: "app/services/payment.rb:34 — catches broad exceptions"
    - label: "W2 Missing edge-case test"
      description: "app/models/order.rb:89 — refund path lacks regression coverage"
    - label: "M1 Method too long"
      description: "app/helpers/formatting.rb:12 — 45 lines"
    - label: "M2 Could use delegate"
      description: "app/models/user.rb:23 — redundant wrapper method"
```

The resulting selection state should be summarized back to the user in a short confirmation such as:

- auto-included: `C1 C2 C3`
- selected: `W1`
- deferred: `W2 M1 M2`

### Step 5: Write Triage Output

The plan should be saved to `.claude/plans/{slug}/plan.md`:

```markdown
# Plan: Fix auth review findings

## Metadata
- Created: 2024-01-15T10:30:00Z
- Source Review: .claude/reviews/fix-auth.md
- Generated By: /rb:triage
- Triaged By: user

## Summary

| Category | Total | Selected | Deferred | Excluded |
|----------|-------|----------|----------|----------|
| Critical | 3 | 3 | 0 | 0 |
| High | 2 | 1 | 1 | 0 |
| Medium | 2 | 0 | 2 | 0 |
| Low | 1 | 0 | 0 | 1 |
| **Total** | **8** | **4** | **3** | **1** |

## Phase 1: Critical Fixes

- [ ] Fix transaction wrap in `app/models/user.rb:45`
  - Rule: Iron Law - Transaction Safety
  - Source: .claude/reviews/fix-auth.md
  - Estimated effort: 15 minutes

- [ ] Fix JSON-safe args in `app/jobs/email_job.rb:12`
  - Rule: Iron Law - JSON-Safe Arguments
  - Source: .claude/reviews/fix-auth.md
  - Estimated effort: 10 minutes

- [ ] Fix N+1 query in `app/controllers/orders_controller.rb:23`
  - Rule: Query Performance
  - Source: .claude/reviews/fix-auth.md
  - Estimated effort: 5 minutes

## Phase 2: High-Priority Fixes

- [ ] Replace bare rescue in `app/services/payment.rb:34`
  - Rule: Error Handling
  - Source: .claude/reviews/fix-auth.md
  - Estimated effort: 10 minutes

## Deferred Findings

### High (Deferred)

- app/models/order.rb:89 - Missing test for edge case
  - Reason: Requires clarification on expected behavior
  - Action: Schedule separate testing session

### Medium (Deferred)

- app/helpers/formatting.rb:12 - Method too long
- app/models/user.rb:23 - Could use delegate

### Low (Excluded)

- app/views/layouts/application.html.erb:5 - Quote style

## Next Steps

1. Run `/rb:work` to fix the 4 selected items
2. Estimated time: 40 minutes
3. Review deferred items in future sprint
```

## Decision Tree

```
Is finding an Iron Law violation?
├── YES → Include in Critical
│         └── Never optional
│
└── NO → Is it a security issue?
          ├── YES → Include in Critical
          │
          └── NO → Is it an N+1 or performance killer?
                    ├── YES → Include in Critical
                    │
                    └── NO → Does it affect data integrity?
                              ├── YES → Include in High
                              │
                              └── NO → Is it error handling?
                                        ├── YES → Include in High
                                        │
                                        └── NO → Is it test coverage?
                                                  ├── YES → Include in High
                                                  │
                                                  └── NO → Is it style/format?
                                                            ├── YES → Mark as Low
                                                            │
                                                            └── NO → Ask user
```

## Batch Operations

### Select All in Category

```
[Select All Critical]
[Select All High]  
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

```bash
# After review completes
/rb:review app/models/user.rb
# → Creates review file

# Then triage
/rb:triage .claude/reviews/fix-user-model.md
# → Creates .claude/plans/fix-user-model/plan.md

# Then work on selected items
/rb:work .claude/plans/fix-user-model/plan.md
```

### Direct to Work

If triage generated a plan with selected critical items:

```bash
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

### All Critical

If all findings are critical:

```
All 5 findings are critical and must be addressed.
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

1. **Always explain why** a finding is critical
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
| `select all critical` | Auto-select all critical findings |
| `group by file` | Reorganize display by file |
| `export` | Export triage to issue tracker |
| `skip all` | Exclude all findings |
