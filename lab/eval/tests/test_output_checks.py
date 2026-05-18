
import unittest

from lab.eval import output_checks


class OutputChecksTests(unittest.TestCase):
    def test_has_h1_ignores_fenced_code_blocks(self) -> None:
        content = """```markdown
# Example heading in code
```

Paragraph first.
"""
        passed, _ = output_checks.has_h1(content)
        self.assertFalse(passed)

    def test_has_h1_requires_first_non_empty_line_to_be_h1(self) -> None:
        content = """
Intro first.

# Later heading
"""
        passed, _ = output_checks.has_h1(content)
        self.assertFalse(passed)

    def test_has_provenance_claim_entries_scopes_to_claim_log(self) -> None:
        content = """# Provenance: sample

## Summary

1. [VERIFIED] "status-like text outside claim log"

## Claim Log

No actual entries here.
"""
        passed, _ = output_checks.has_provenance_claim_entries(content, minimum=1)
        self.assertFalse(passed)

    def test_has_provenance_claim_entries_allows_single_entry_by_default(self) -> None:
        content = """# Provenance: sample

## Claim Log

1. [VERIFIED] "single supported claim"
   - Evidence: app/models/user.rb:14
   - Notes: Proven by local code.

## Required Fixes

- None.
"""
        passed, _ = output_checks.has_provenance_claim_entries(content)
        self.assertTrue(passed)

    def test_has_provenance_claim_entries_rejects_undocumented_statuses(self) -> None:
        content = """# Provenance: sample

## Claim Log

1. [OPINION] "not part of the shared contract"
   - Evidence: app/models/user.rb:14
   - Notes: This should not count.
"""
        passed, _ = output_checks.has_provenance_claim_entries(content)
        self.assertFalse(passed)

    def test_has_provenance_local_evidence_scopes_to_claim_log_and_requires_file_ref(self) -> None:
        content = """# Provenance: sample

## Claim Log

1. [VERIFIED] "bad local evidence"
   - Evidence: local note:12

## Required Fixes

- None.
"""
        passed, _ = output_checks.has_provenance_local_evidence(content)
        self.assertFalse(passed)

    def test_has_provenance_local_evidence_allows_extensionless_root_files(self) -> None:
        content = """# Provenance: sample

## Claim Log

1. [VERIFIED] "Gemfile proves the dependency change"
   - Evidence: Gemfile:12
   - Notes: Proven by local code.
"""
        passed, _ = output_checks.has_provenance_local_evidence(content)
        self.assertTrue(passed)

    def test_has_provenance_external_evidence_scopes_to_claim_log(self) -> None:
        content = """# Provenance: sample

## Notes

- Evidence: <https://example.com/doc> [T1]

## Claim Log

1. [UNSUPPORTED] "no external evidence in claim log"
   - Evidence: app/models/user.rb:14
"""
        passed, _ = output_checks.has_provenance_external_evidence(content)
        self.assertFalse(passed)

    def test_provenance_external_evidence_rejects_placeholder_urls(self) -> None:
        content = """# Provenance: sample

## Claim Log

1. [VERIFIED] "placeholder discussion link should not count as valid external evidence"
   - Evidence: <https://github.com/example/project/discussions/0000> [T1]
"""
        passed, _ = output_checks.provenance_external_evidence_is_non_placeholder(content)
        self.assertFalse(passed)

    def test_has_research_decision_section_accepts_executive_summary(self) -> None:
        content = """# Research: sample

## Executive Summary

Use the maintained upstream path.
"""
        passed, _ = output_checks.has_research_decision_section(content)
        self.assertTrue(passed)

    def test_has_sources_section_accepts_crlf_input(self) -> None:
        content = "# Research: sample\r\n\r\n## Sources\r\n\r\n- [T1] <https://example.com>\r\n"
        passed, _ = output_checks.has_sources_section(content)
        self.assertTrue(passed)

    def test_has_inline_tier_markers_accepts_crlf_sources_heading(self) -> None:
        content = (
            "# Research: sample\r\n"
            "\r\n"
            "Claim one [T1]\r\n"
            "Claim two [T2]\r\n"
            "\r\n"
            "## Sources\r\n"
            "\r\n"
            "- [T1] <https://example.com>\r\n"
        )
        passed, _ = output_checks.has_inline_tier_markers(content, minimum=2)
        self.assertTrue(passed)

    def test_reviewer_coverage_rejects_malformed_row_alongside_valid(self) -> None:
        # Mixed rows: one valid, one too-narrow. Must NOT pass — silent
        # skip would let the broken row sneak through.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| testing-reviewer | artifact |
"""
        passed, reason = output_checks.has_review_reviewer_coverage(content)
        self.assertFalse(passed)
        self.assertIn("contract requires exactly 3", reason)

    def test_reviewer_coverage_rejects_invalid_recovery_state(self) -> None:
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | unknown-state | 0 Blockers / 0 Warnings / 0 Suggestions |
"""
        passed, reason = output_checks.has_review_reviewer_coverage(content)
        self.assertFalse(passed)
        self.assertIn("invalid recovery state", reason)

    def test_reviewer_coverage_rejects_malformed_findings_cell(self) -> None:
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | none |
"""
        passed, reason = output_checks.has_review_reviewer_coverage(content)
        self.assertFalse(passed)
        self.assertIn("Blocker[s] / {n} Warning[s] / {n} Suggestion[s]", reason)

    def test_reviewer_verdicts_rejects_non_canonical_verdict(self) -> None:
        content = """# Review: x

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | LGTM | LGTM |
"""
        passed, reason = output_checks.has_review_reviewer_verdicts(content)
        self.assertFalse(passed)
        self.assertIn("not in 4-set", reason)

    def test_reviewer_completeness_rejects_missing_row_in_coverage(self) -> None:
        # Header lists 2 reviewers, Coverage only has 1, Verdicts has both.
        content = """# Review: x

**Reviewers**: ruby-reviewer, testing-reviewer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| testing-reviewer | PASS | PASS |
"""
        passed, reason = output_checks.has_review_reviewer_completeness(content)
        self.assertFalse(passed)
        self.assertIn("Coverage table missing reviewers", reason)

    def test_reviewer_coverage_rejects_extra_cells(self) -> None:
        # 4 cells violates exact-3 contract.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings | Extra |
|---|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions | junk |
"""
        passed, reason = output_checks.has_review_reviewer_coverage(content)
        self.assertFalse(passed)
        self.assertIn("4 cell", reason)

    def test_reviewer_verdicts_rejects_extra_cells(self) -> None:
        content = """# Review: x

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical | Extra |
|---|---|---|---|
| ruby-reviewer | PASS | PASS | junk |
"""
        passed, reason = output_checks.has_review_reviewer_verdicts(content)
        self.assertFalse(passed)
        self.assertIn("4 cell", reason)

    def test_reviewer_completeness_rejects_duplicate_coverage_row(self) -> None:
        content = """# Review: x

**Reviewers**: ruby-reviewer, testing-reviewer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| testing-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| testing-reviewer | PASS | PASS |
"""
        passed, reason = output_checks.has_review_reviewer_completeness(content)
        self.assertFalse(passed)
        self.assertIn("Coverage table has duplicate", reason)

    def test_reviewer_completeness_rejects_duplicate_header_slug(self) -> None:
        content = """# Review: x

**Reviewers**: ruby-reviewer, ruby-reviewer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
"""
        passed, reason = output_checks.has_review_reviewer_completeness(content)
        self.assertFalse(passed)
        self.assertIn("duplicate slug", reason)

    def test_reviewer_completeness_passes_when_header_matches_tables(self) -> None:
        content = """# Review: x

**Reviewers**: ruby-reviewer, testing-reviewer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| testing-reviewer | artifact | 0 Blockers / 1 Warning / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| testing-reviewer | PASS WITH WARNINGS | PASS WITH WARNINGS |
"""
        passed, _ = output_checks.has_review_reviewer_completeness(content)
        self.assertTrue(passed)

    def test_has_review_verdict_rejects_non_canonical_text(self) -> None:
        content = "# Review: x\n\n**Verdict**: LGTM\n"
        passed, reason = output_checks.has_review_verdict(content)
        self.assertFalse(passed)
        self.assertIn("not in canonical 4-set", reason)

    def test_has_review_verdict_rejects_non_canonical_when_canonical_appears_later(self) -> None:
        # Primary `**Verdict**:` line is non-canonical. A later
        # canonical-looking duplicate (e.g. inside an example block)
        # MUST NOT mask the primary violation.
        content = """# Review: x

**Verdict**: LGTM

## Example

`**Verdict**: PASS`

Another instance:

**Verdict**: PASS
"""
        passed, reason = output_checks.has_review_verdict(content)
        self.assertFalse(passed)
        self.assertIn("LGTM", reason)

    def test_reviewer_verdicts_rejects_no_output_placeholder_for_non_stub_reviewer(self) -> None:
        # Non-stub reviewer (Coverage state = artifact) uses `(no output)`
        # placeholder in raw cell. Placeholder is reserved for
        # stub-no-output rows only.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | (no output) | PASS |
"""
        passed, reason = output_checks.has_review_reviewer_verdicts(content)
        self.assertFalse(passed)
        self.assertIn("placeholder reserved", reason)

    def test_has_review_verdict_accepts_canonical_4_set(self) -> None:
        for verdict in ("PASS", "PASS WITH WARNINGS", "REQUIRES CHANGES", "BLOCKED"):
            content = f"# Review: x\n\n**Verdict**: {verdict}\n"
            passed, _ = output_checks.has_review_verdict(content)
            self.assertTrue(passed, f"canonical {verdict!r} should pass")

    def test_reviewer_verdicts_accepts_no_output_placeholder_for_stub_no_output(self) -> None:
        # Reviewer marked `stub-no-output` in Coverage → Verdicts row
        # uses literal `(no output)` in raw + canonical (no verdict
        # prose exists to preserve).
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| security-analyzer | stub-no-output | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| security-analyzer | (no output) | (no output) |
"""
        passed, _ = output_checks.has_review_reviewer_verdicts(content)
        self.assertTrue(passed)

    def test_reviewer_verdicts_rejects_no_output_in_both_cells_for_non_stub_reviewer(self) -> None:
        # Reviewer is `artifact` in Coverage but uses `(no output)`
        # placeholder in BOTH Verdicts cells → contract violation. The
        # placeholder is reserved for stub-no-output rows.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | (no output) | (no output) |
"""
        passed, reason = output_checks.has_review_reviewer_verdicts(content)
        self.assertFalse(passed)
        self.assertIn("placeholder reserved", reason)

    def test_reviewer_verdicts_rejects_blank_raw_cell(self) -> None:
        content = """# Review: x

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer |  | PASS |
"""
        passed, reason = output_checks.has_review_reviewer_verdicts(content)
        self.assertFalse(passed)
        self.assertIn("raw verdict cell empty", reason)

    def test_reviewer_completeness_passes_when_rows_reordered(self) -> None:
        # Manifest stores reviewers under an `agents` object (no natural
        # order). Cosmetic reorder of Coverage / Verdicts rows MUST NOT
        # fail — set membership + count is the contract.
        content = """# Review: x

**Reviewers**: ruby-reviewer, testing-reviewer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| testing-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| testing-reviewer | PASS | PASS |
"""
        passed, _ = output_checks.has_review_reviewer_completeness(content)
        self.assertTrue(passed)

    def test_has_review_verdict_handles_4backtick_outer_with_3backtick_inner(self) -> None:
        # CommonMark: 4-backtick fence opens; only matching 4-backtick
        # closes. Inner 3-backtick samples must NOT close outer.
        content = """# Review: x

**Verdict**: PASS

## Suggestions (1)

### 1. Update example doc

````markdown
**Verdict**: LGTM

```ruby
puts "hello"
```

**Verdict**: BLOCK
````
"""
        passed, _ = output_checks.has_review_verdict(content)
        self.assertTrue(passed)

    def test_has_review_finding_confidence_skips_fenced_excerpts(self) -> None:
        # Reviewed Markdown excerpt inside outer 4-backtick fence
        # contains `**File**:` + `**Confidence**:` lines as DATA.
        # Validator must skip them; outer review has 1 real finding.
        content = """# Review: x

## Warnings (1)

### 1. Real Issue

**File**: `app/foo.rb:10`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: bad

**Current**:

````markdown
**File**: `quoted/example.md:5`
**Reviewer**: testing-reviewer
````

**Recommendation**: fix it
"""
        passed, _ = output_checks.has_review_finding_confidence(content)
        self.assertTrue(passed)

    def test_has_review_finding_confidence_anchors_to_each_finding(self) -> None:
        # Two confidence labels on finding 1, none on finding 2.
        # Global count matches but per-finding anchoring rejects.
        content = """# Review: x

## Warnings (2)

### 1. First Issue

**File**: `app/foo.rb:10`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Reviewer-note**: secondary | **Confidence**: MEDIUM

### 2. Second Issue

**File**: `app/bar.rb:20`
**Reviewer**: testing-reviewer
**Issue**: missing test
"""
        passed, reason = output_checks.has_review_finding_confidence(content)
        self.assertFalse(passed)
        self.assertIn("missing", reason)

    def test_has_review_verdict_rejects_multiple_verdict_lines(self) -> None:
        content = """# Review: x

**Verdict**: PASS WITH WARNINGS

Some prose.

**Verdict**: BLOCKED
"""
        passed, reason = output_checks.has_review_verdict(content)
        self.assertFalse(passed)
        self.assertIn("exactly one verdict", reason)

    def test_has_review_mandatory_table_rejects_old_6col_format(self) -> None:
        content = """# Review: x

## At-a-Glance Finding Table

| # | Finding | Severity | Reviewer | File | New? |
|---|---------|----------|----------|------|------|
| 1 | Issue | Warning | r | f.rb:1 | Yes |
"""
        passed, reason = output_checks.has_review_mandatory_table(content)
        self.assertFalse(passed)
        self.assertIn("Confidence", reason)

    def test_has_review_mandatory_table_accepts_7col_with_confidence(self) -> None:
        content = """# Review: x

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Warning | HIGH | r | f.rb:1 | Yes |
"""
        passed, _ = output_checks.has_review_mandatory_table(content)
        self.assertTrue(passed)

    def test_section_skips_fenced_quoted_headings(self) -> None:
        # `## Reviewer Coverage` heading inside a fenced markdown
        # excerpt is a quoted template, not a live section. Validator
        # MUST not pick up its body.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Suggestions (1)

### 1. Update doc

````markdown
## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| fake-reviewer | invalid-state | bogus |
````
"""
        passed, _ = output_checks.has_review_reviewer_coverage(content)
        # Live Coverage section has 1 valid row; fenced excerpt with
        # invalid state must NOT leak into validation.
        self.assertTrue(passed)

    def test_has_review_metadata_fields_skips_fenced_excerpts(self) -> None:
        # Real artifact missing Complexity. Fenced excerpt contains
        # all 4 fields — must NOT count.
        content = """# Review: x

**Date**: 2026-05-05
**Files Changed**: app/foo.rb
**Reviewers**: ruby-reviewer

## Suggestions (1)

### 1. Update doc

````markdown
**Date**: 2024-01-01
**Complexity**: Simple (1 file)
**Files Changed**: example.rb
**Reviewers**: ruby-reviewer
````
"""
        passed, reason = output_checks.has_review_metadata_fields(content)
        self.assertFalse(passed)
        self.assertIn("Complexity", reason)

    def test_has_review_metadata_fields_rejects_missing_complexity(self) -> None:
        content = """# Review: x

**Date**: 2026-05-05
**Files Changed**: app/foo.rb
**Reviewers**: ruby-reviewer
"""
        passed, reason = output_checks.has_review_metadata_fields(content)
        self.assertFalse(passed)
        self.assertIn("Complexity", reason)

    def test_has_review_metadata_fields_accepts_all_four(self) -> None:
        content = """# Review: x

**Date**: 2026-05-05
**Complexity**: Simple (1 file)
**Files Changed**: app/foo.rb
**Reviewers**: ruby-reviewer
"""
        passed, _ = output_checks.has_review_metadata_fields(content)
        self.assertTrue(passed)

    def test_has_review_mandatory_table_requires_section_heading(self) -> None:
        # Table with correct schema but no `## At-a-Glance Finding Table`
        # heading should fail.
        content = """# Review: x

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Warning | HIGH | r | f.rb:1 | Yes |
"""
        passed, reason = output_checks.has_review_mandatory_table(content)
        self.assertFalse(passed)
        self.assertIn("At-a-Glance Finding Table", reason)

    def test_has_review_mandatory_table_skips_fenced_excerpt(self) -> None:
        # Mandatory table header inside a fenced Markdown excerpt is
        # data, not the live consolidated artifact. Validator must NOT
        # accept it as the real table.
        content = """# Review: x

## Suggestions (1)

### 1. Update playbook example

````markdown
| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Example | Warning | LOW | r | f.rb:1 | Yes |
````
"""
        passed, _ = output_checks.has_review_mandatory_table(content)
        self.assertFalse(passed)

    def test_has_provenance_artifact_pointer_rejects_undated_review_path(self) -> None:
        content = """# Provenance: x

**Artifact**: `.claude/reviews/fix-auth-review.md`
"""
        passed, reason = output_checks.has_provenance_artifact_pointer(content)
        self.assertFalse(passed)
        self.assertIn("datesuffix", reason)

    def test_has_provenance_artifact_pointer_accepts_dated_review_path(self) -> None:
        content = """# Provenance: x

**Artifact**: `.claude/reviews/fix-auth-review-20260505-123000.md`
"""
        passed, _ = output_checks.has_provenance_artifact_pointer(content)
        self.assertTrue(passed)

    def test_has_provenance_artifact_pointer_accepts_dated_per_agent_review_path(self) -> None:
        content = """# Provenance: x

**Artifact**: `.claude/reviews/ruby-reviewer/fix-auth-review-20260505-123000.md`
"""
        passed, _ = output_checks.has_provenance_artifact_pointer(content)
        self.assertTrue(passed)

    def test_has_provenance_artifact_pointer_accepts_non_review_paths(self) -> None:
        content = """# Provenance: x

**Artifact**: `.claude/research/topic.md`
"""
        passed, _ = output_checks.has_provenance_artifact_pointer(content)
        self.assertTrue(passed)

    def test_has_review_verdict_skips_fenced_blocks(self) -> None:
        # `**Verdict**: LGTM` inside a fenced Markdown excerpt under a
        # Suggested/Current section is a reviewed snippet, not the
        # consolidated verdict — must NOT trip the canonical check.
        content = """# Review: x

**Verdict**: PASS

## Suggestions (1)

### 1. Update example doc

````markdown
**Verdict**: LGTM
````
"""
        passed, _ = output_checks.has_review_verdict(content)
        self.assertTrue(passed)

    def test_has_review_finding_confidence_rejects_missing_label(self) -> None:
        content = """# Review: x

## Warnings (1)

### 1. Issue

**File**: `app/foo.rb:10`
**Reviewer**: ruby-reviewer
**Issue**: bad
**Recommendation**: fix
"""
        passed, reason = output_checks.has_review_finding_confidence(content)
        self.assertFalse(passed)
        self.assertIn("Confidence", reason)

    def test_has_review_finding_confidence_accepts_inline_confidence(self) -> None:
        content = """# Review: x

## Warnings (1)

### 1. Issue

**File**: `app/foo.rb:10`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: bad
"""
        passed, _ = output_checks.has_review_finding_confidence(content)
        self.assertTrue(passed)

    def test_verdict_matches_summary_rejects_pass_with_blockers(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 2 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("blocker(s)", reason)
        self.assertIn("BLOCKED", reason)

    def test_verdict_matches_summary_rejects_pass_with_warnings(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 3 |
| Suggestions | 0 |

**Verdict**: PASS
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("PASS WITH WARNINGS", reason)

    def test_verdict_matches_summary_rejects_blocked_with_warnings_only(self) -> None:
        # Per playbook STEP 4: BLOCKED requires blockers > 0.
        # warnings > 0 + blockers == 0 + verdict == BLOCKED is invalid;
        # expected PASS WITH WARNINGS or REQUIRES CHANGES.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 3 |
| Suggestions | 0 |

**Verdict**: BLOCKED
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("0 blockers", reason)
        self.assertIn("BLOCKED", reason)
        self.assertIn("blockers > 0", reason)

    def test_verdict_matches_summary_rejects_blocked_with_zero_counts(self) -> None:
        # Zero blockers + verdict=BLOCKED is rejected by the
        # blockers-required gate (BLOCKED requires blockers > 0).
        # Earlier wording cited "PASS or REQUIRES CHANGES"; the
        # blockers-required rule now fires first and is more precise.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: BLOCKED
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("blockers > 0", reason)
        self.assertIn("BLOCKED", reason)

    def test_verdict_matches_summary_rejects_pass_with_warnings_no_warnings(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS WITH WARNINGS
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("PASS or REQUIRES CHANGES", reason)

    def test_verdict_matches_summary_accepts_consistent_pass_with_warnings(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 1 |
| Suggestions | 0 |

**Verdict**: PASS WITH WARNINGS
"""
        passed, _ = output_checks.has_review_verdict_matches_summary(content)
        self.assertTrue(passed)

    def test_reviewer_completeness_rejects_fenced_only_reviewers_header(self) -> None:
        # Real artifact has NO `**Reviewers**:` header. Fenced excerpt
        # contains one — must NOT satisfy the completeness gate.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |

## Suggestions (1)

### 1. Update example doc

````markdown
**Reviewers**: ruby-reviewer, testing-reviewer
````
"""
        passed, reason = output_checks.has_review_reviewer_completeness(content)
        self.assertFalse(passed)
        self.assertIn("Missing `**Reviewers**:` header", reason)

    def test_reviewer_coverage_rejects_stub_no_output_with_nonzero_findings(self) -> None:
        # `stub-no-output` means synthesis recovered no usable output;
        # the reviewer cannot have contributed findings. A non-zero
        # findings cell is semantically impossible.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| security-analyzer | stub-no-output | 1 Blocker / 0 Warnings / 0 Suggestions |
"""
        passed, reason = output_checks.has_review_reviewer_coverage(content)
        self.assertFalse(passed)
        self.assertIn("stub-no-output", reason)
        self.assertIn("0 Blockers / 0 Warnings / 0 Suggestions", reason)

    def test_reviewer_coverage_accepts_stub_no_output_with_all_zero_findings(self) -> None:
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| security-analyzer | stub-no-output | 0 Blockers / 0 Warnings / 0 Suggestions |
"""
        passed, _ = output_checks.has_review_reviewer_coverage(content)
        self.assertTrue(passed)

    def test_has_review_metadata_fields_rejects_fields_in_footer_prose(self) -> None:
        # All four fields appear, but only AFTER the first `## ` section
        # heading (i.e., in body / footer prose, not the preamble).
        # Playbook requires header placement.
        content = """# Review: x

## Summary

Some prose.

**Date**: 2026-05-05
**Complexity**: Simple (1 file)
**Files Changed**: app/foo.rb
**Reviewers**: ruby-reviewer
"""
        passed, reason = output_checks.has_review_metadata_fields(content)
        self.assertFalse(passed)
        self.assertIn("preamble", reason)

    def test_summary_excludes_preexisting_rejects_preexisting_counted_in_summary(self) -> None:
        # At-a-Glance shows 1 Blocker row marked Pre-existing and 0 NEW
        # blocker rows. Summary counts the pre-existing one → contract
        # violation per playbook STEP 3 + § "Pre-existing Issues".
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 1 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: BLOCKED

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Old issue | Blocker | HIGH | r | f.rb:1 | Pre-existing |
"""
        passed, reason = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("Blockers", reason)
        self.assertIn("pre-existing", reason)

    def test_summary_excludes_preexisting_accepts_matching_new_counts(self) -> None:
        # Summary counts equal NEW (Yes) rows; pre-existing rows present
        # in At-a-Glance but excluded from Summary.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 1 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: BLOCKED

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | New issue | Blocker | HIGH | r | f.rb:1 | Yes |
| 2 | Old issue | Blocker | HIGH | r | f.rb:9 | Pre-existing |
"""
        passed, _ = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertTrue(passed)

    def test_summary_excludes_preexisting_skips_when_at_a_glance_missing(self) -> None:
        # No At-a-Glance section → cross-check skipped (mandatory-table
        # validator surfaces the gap separately).
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS
"""
        passed, _ = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertTrue(passed)

    def test_coverage_excludes_preexisting_rejects_preexisting_counted_in_coverage(self) -> None:
        # ruby-reviewer's Coverage row reports 1 Blocker. At-a-Glance
        # shows 0 NEW Blocker rows for ruby-reviewer (only a Pre-existing
        # one). Coverage MUST exclude pre-existing per playbook STEP 3.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 1 Blocker / 0 Warnings / 0 Suggestions |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Old issue | Blocker | HIGH | ruby-reviewer | f.rb:1 | Pre-existing |
"""
        passed, reason = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("ruby-reviewer", reason)
        self.assertIn("Blocker", reason)
        self.assertIn("pre-existing", reason)

    def test_coverage_excludes_preexisting_accepts_matching_per_reviewer_new_counts(self) -> None:
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 1 Blocker / 0 Warnings / 0 Suggestions |
| testing-reviewer | artifact | 0 Blockers / 1 Warning / 0 Suggestions |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | New issue | Blocker | HIGH | ruby-reviewer | f.rb:1 | Yes |
| 2 | Old issue | Blocker | HIGH | ruby-reviewer | f.rb:9 | Pre-existing |
| 3 | Test gap | Warning | MEDIUM | testing-reviewer | spec.rb:5 | Yes |
"""
        passed, _ = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertTrue(passed)

    def test_coverage_excludes_preexisting_rejects_stub_no_output_with_attributions(self) -> None:
        # stub-no-output reviewer means no usable output; ANY
        # At-a-Glance row attributing a finding to that reviewer is
        # impossible per `review-playbook.md` § "Artifact Recovery".
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| security-analyzer | stub-no-output | 0 Blockers / 0 Warnings / 0 Suggestions |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Blocker | HIGH | security-analyzer | f.rb:1 | Yes |
"""
        passed, reason = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("security-analyzer", reason)
        self.assertIn("stub-no-output", reason)

    def test_coverage_excludes_preexisting_rejects_stub_no_output_with_preexisting_attribution(self) -> None:
        # Same gate fires when a stub-no-output reviewer is
        # attributed a Pre-existing finding too — they produced NO
        # usable output, period.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| security-analyzer | stub-no-output | 0 Blockers / 0 Warnings / 0 Suggestions |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Old issue | Blocker | HIGH | security-analyzer | f.rb:9 | Pre-existing |
"""
        passed, reason = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("stub-no-output", reason)

    def test_coverage_excludes_preexisting_skips_stub_no_output_rows(self) -> None:
        # stub-no-output rows already enforce all-zero counts via
        # `has_review_reviewer_coverage`; cross-check skips them so a
        # legitimate stub-no-output reviewer with no At-a-Glance rows
        # does not produce a false count mismatch.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
| security-analyzer | stub-no-output | 0 Blockers / 0 Warnings / 0 Suggestions |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
"""
        passed, _ = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertTrue(passed)

    def test_coverage_excludes_preexisting_skips_when_at_a_glance_missing(self) -> None:
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |
"""
        passed, _ = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertTrue(passed)

    def test_reviewer_coverage_accepts_stub_no_output_with_extra_inner_whitespace(self) -> None:
        # Whitespace-tolerant zero-counts gate for stub-no-output —
        # extra inner spaces around `/` MUST NOT trip the gate when
        # counts are still 0/0/0.
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| security-analyzer | stub-no-output | 0 Blockers / 0 Warnings / 0 Suggestions |
"""
        passed, _ = output_checks.has_review_reviewer_coverage(content)
        self.assertTrue(passed)

    def test_summary_excludes_preexisting_rejects_malformed_new_enum(self) -> None:
        # A `New?` cell of `No` is not in the {Yes, Pre-existing} enum.
        # Validator MUST reject rather than silently dropping the row
        # from the NEW tally — silent drop would let pre-existing
        # leakage pass.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 1 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: BLOCKED

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Blocker | HIGH | r | f.rb:1 | No |
"""
        passed, reason = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("malformed enum", reason)
        self.assertIn("'No'", reason)

    def test_summary_excludes_preexisting_rejects_blank_new_cell(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Blocker | HIGH | r | f.rb:1 |  |
"""
        passed, reason = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("malformed enum", reason)

    def test_coverage_excludes_preexisting_rejects_malformed_new_enum(self) -> None:
        content = """# Review: x

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blockers / 0 Warnings / 0 Suggestions |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Blocker | HIGH | ruby-reviewer | f.rb:1 | maybe |
"""
        passed, reason = output_checks.has_review_coverage_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("malformed enum", reason)
        self.assertIn("'maybe'", reason)

    def test_has_review_mandatory_table_rejects_row_missing_new_cell(self) -> None:
        # Row carries 6 cells (no `New?`). Without explicit row-width
        # validation, summary/coverage cross-checks silently skip the
        # row → pre-existing leakage hides. Fail fast on bad shape.
        content = """# Review: x

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Blocker | HIGH | r | f.rb:1 |
"""
        passed, reason = output_checks.has_review_mandatory_table(content)
        self.assertFalse(passed)
        self.assertIn("contract requires exactly 7", reason)

    def test_has_review_mandatory_table_accepts_valid_7cell_rows(self) -> None:
        content = """# Review: x

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | Blocker | HIGH | r | f.rb:1 | Yes |
| 2 | Other | Warning | MEDIUM | r | g.rb:5 | Pre-existing |
"""
        passed, reason = output_checks.has_review_mandatory_table(content)
        self.assertTrue(passed)
        self.assertIn("2 row(s)", reason)

    def test_has_review_file_refs_skips_fenced_excerpts(self) -> None:
        # Real artifact has zero out-of-fence `**File**:` lines. A
        # fenced Markdown excerpt under `**Current**` contains a
        # `**File**:` line as DATA — must NOT count.
        content = """# Review: x

## Suggestions (1)

### 1. Update example

````markdown
**File**: `quoted/example.md:5`
**Reviewer**: ruby-reviewer
````
"""
        passed, reason = output_checks.has_review_file_refs(content, minimum=1)
        self.assertFalse(passed)
        self.assertIn("0 finding file ref(s)", reason)

    def test_review_has_no_task_lists_skips_fenced_excerpts(self) -> None:
        # Fenced markdown excerpt with a task list is quoted DATA,
        # not a live review task list. Must NOT trip the gate.
        content = """# Review: x

## Warnings (1)

### 1. Doc has stale checklist

**File**: `docs/old.md:1`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: Stale `- [ ]` checkbox in doc.

**Current**:

````markdown
- [ ] An old doc TODO
- [x] Already done
````
"""
        passed, _ = output_checks.review_has_no_task_lists(content)
        self.assertTrue(passed)

    def test_review_has_no_followup_sections_skips_fenced_excerpts(self) -> None:
        # Reviewing a doc that itself has `## Next Steps` — quoted
        # under fenced `**Current**`/`**Suggested**`. Live review has
        # no such section. Must NOT trip the gate.
        content = """# Review: x

## Warnings (1)

### 1. Reviewing a doc that plans follow-ups

**File**: `docs/plan.md:1`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH

**Current**:

````markdown
## Next Steps

1. Do thing.
````
"""
        passed, _ = output_checks.review_has_no_followup_sections(content)
        self.assertTrue(passed)

    def test_has_review_file_refs_rejects_path_only_under_blockers(self) -> None:
        # Per playbook template: Blockers MUST carry `:line`.
        # Path-only is only valid under `## Suggestions`.
        content = """# Review: x

## Blockers (1)

### 1. Issue

**File**: `app/models/user.rb`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: bad
"""
        passed, reason = output_checks.has_review_file_refs(content, minimum=1)
        self.assertFalse(passed)
        self.assertIn("Blockers", reason)
        self.assertIn(":line", reason)

    def test_has_review_file_refs_rejects_path_only_under_warnings(self) -> None:
        content = """# Review: x

## Warnings (1)

### 1. Issue

**File**: `app/models/user.rb`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: bad
"""
        passed, reason = output_checks.has_review_file_refs(content, minimum=1)
        self.assertFalse(passed)
        self.assertIn("Warnings", reason)

    def test_has_review_file_refs_accepts_path_only_for_suggestions(self) -> None:
        # Suggestions section template allows `**File**: path/to/file.rb`
        # without `:line` (whole-file scope). Validator MUST accept.
        content = """# Review: x

## Suggestions (1)

### 1. Extract constant

**File**: `app/models/magic_token.rb`
**Reviewer**: ruby-reviewer | **Confidence**: LOW
**Suggestion**: Extract TTL literal.
"""
        passed, reason = output_checks.has_review_file_refs(content, minimum=1)
        self.assertTrue(passed)
        self.assertIn("1 finding file ref", reason)

    def test_has_review_file_refs_accepts_path_with_line(self) -> None:
        content = """# Review: x

## Blockers (1)

### 1. Issue

**File**: `app/models/user.rb:45`
**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: bad
"""
        passed, _ = output_checks.has_review_file_refs(content, minimum=1)
        self.assertTrue(passed)

    def test_summary_excludes_preexisting_rejects_missing_suggestions_row(self) -> None:
        # Per `review-playbook.md` § "Summary" template: all 3 rows
        # required. Missing `Suggestions` row was previously skipped
        # silently → fail it now.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |

**Verdict**: PASS

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Idea | Suggestion | LOW | r | f.rb:1 | Yes |
"""
        passed, reason = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("Suggestions", reason)
        self.assertIn("row missing", reason)

    def test_finding_confidence_rejects_finding_missing_file_line(self) -> None:
        # Finding has Confidence but NO **File**: line.
        # Validator anchored on `### N.` heading detects it.
        content = """# Review: x

## Warnings (1)

### 1. Issue without file ref

**Reviewer**: ruby-reviewer | **Confidence**: HIGH
**Issue**: bad
"""
        passed, reason = output_checks.has_review_finding_confidence(content)
        self.assertFalse(passed)
        self.assertIn("**File**:", reason)

    def test_finding_confidence_rejects_two_findings_one_missing_file(self) -> None:
        # Two findings: first complete, second missing **File**.
        # Old `**File**:`-anchored loop missed the second finding;
        # new `### N.` anchor catches it.
        content = """# Review: x

## Warnings (2)

### 1. First

**File**: `app/foo.rb:1`
**Reviewer**: r | **Confidence**: HIGH
**Issue**: a

### 2. Second (missing File line)

**Reviewer**: r | **Confidence**: MEDIUM
**Issue**: b
"""
        passed, reason = output_checks.has_review_finding_confidence(content)
        self.assertFalse(passed)
        self.assertIn("Second", reason)
        self.assertIn("**File**:", reason)

    def test_mandatory_table_accepts_zero_data_rows_for_empty_pass(self) -> None:
        # Per `review-playbook.md` line 187-188: empty-findings PASS
        # writes the artifact with zero data rows under the section
        # header. Validator MUST accept this shape;
        # Summary↔At-a-Glance cross-check enforces consistency.
        content = """# Review: x

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
"""
        passed, reason = output_checks.has_review_mandatory_table(content)
        self.assertTrue(passed)
        self.assertIn("0 row(s)", reason)

    def test_summary_excludes_preexisting_rejects_off_list_severity(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Issue | CRITICAL | HIGH | r | f.rb:1 | Yes |
"""
        passed, reason = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertFalse(passed)
        self.assertIn("Severity", reason)
        self.assertIn("CRITICAL", reason)

    def test_empty_findings_pass_artifact_passes_validators(self) -> None:
        # Per `review-playbook.md` line 187-188: PASS reviews with
        # zero findings MUST still write the artifact. Validators
        # MUST allow this shape — At-a-Glance with 0 data rows,
        # `has_review_file_refs` vacuously satisfied.
        content = """# Review: Empty Clean Diff

**Date**: 2026-05-05
**Complexity**: Simple (1 file)
**Files Changed**: app/models/user.rb
**Reviewers**: ruby-reviewer

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
"""
        # mandatory_table accepts 0 data rows.
        passed, _ = output_checks.has_review_mandatory_table(content)
        self.assertTrue(passed)
        # file_refs vacuously satisfied (no `### N.` headings inside buckets).
        passed, reason = output_checks.has_review_file_refs(content, minimum=1)
        self.assertTrue(passed)
        self.assertIn("No findings present", reason)
        # finding_confidence vacuously satisfied (no findings).
        passed, _ = output_checks.has_review_finding_confidence(content)
        self.assertTrue(passed)
        # summary_excludes_preexisting passes (Summary 0/0/0 == empty At-a-Glance).
        passed, _ = output_checks.has_review_summary_excludes_preexisting(content)
        self.assertTrue(passed)

    def test_fence_walker_treats_info_string_line_as_open_not_close(self) -> None:
        # Per CommonMark: a closing fence carries NO info string. A
        # line like ` ```ruby ` with same backtick count opens a NEW
        # fence inside the outer one — must NOT close the outer.
        # Outer 4-backtick `markdown` excerpt with inner 3-backtick
        # `ruby` block: outer must remain OPEN for the inner block,
        # then the closing 3-backtick line closes inner, then the
        # final 4-backtick line closes outer. Lines INSIDE outer
        # must NOT yield outside-fence.
        content = """before

````markdown
**Verdict**: LGTM

```ruby
puts "hello"
```

**Verdict**: BLOCK
````

after
"""
        # Verdict-line walker should see 0 verdict lines outside
        # fences (outer covers all interior).
        verdicts = output_checks._verdict_lines_outside_fences(content)
        self.assertEqual(verdicts, [])

    def test_verdict_matches_summary_rejects_requires_changes_without_gaps_section(self) -> None:
        # REQUIRES CHANGES verdict requires `## Test Coverage Gaps`
        # section with at least one row. Missing section → fail.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: REQUIRES CHANGES
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("Test Coverage Gaps", reason)
        self.assertIn("missing", reason)

    def test_verdict_matches_summary_rejects_requires_changes_empty_gaps(self) -> None:
        # Section present but 0 rows → fail.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: REQUIRES CHANGES

## Test Coverage Gaps (0)

| # | Surface | File | Why uncovered | Suggested test |
|---|---------|------|---------------|----------------|
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("0 data rows", reason)

    def test_verdict_matches_summary_accepts_requires_changes_with_gaps(self) -> None:
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: REQUIRES CHANGES

## Test Coverage Gaps (1)

| # | Surface | File | Why uncovered | Suggested test |
|---|---------|------|---------------|----------------|
| 1 | `Foo#bar` | `app/foo.rb:1` | new public method | `spec/foo_spec.rb` — assert bar |
"""
        passed, _ = output_checks.has_review_verdict_matches_summary(content)
        self.assertTrue(passed)

    def test_verdict_matches_summary_rejects_test_coverage_gaps_with_pass(self) -> None:
        # Test Coverage Gaps section is exclusive to REQUIRES CHANGES.
        # PASS verdict + section present → reject.
        content = """# Review: x

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: PASS

## Test Coverage Gaps (1)

| # | Surface | File | Why uncovered | Suggested test |
|---|---------|------|---------------|----------------|
| 1 | `Foo#bar` | `app/foo.rb:1` | new | `spec/foo_spec.rb` |
"""
        passed, reason = output_checks.has_review_verdict_matches_summary(content)
        self.assertFalse(passed)
        self.assertIn("Test Coverage Gaps", reason)
        self.assertIn("PASS", reason)

    def test_test_coverage_gaps_schema_rejects_4col_row(self) -> None:
        content = """# Review: x

## Test Coverage Gaps (1)

| # | Surface | File | Why uncovered |
|---|---------|------|---------------|
| 1 | `Foo#bar` | `app/foo.rb:1` | new |
"""
        passed, reason = output_checks.has_review_test_coverage_gaps_schema(content)
        self.assertFalse(passed)
        self.assertIn("contract requires exactly 5", reason)

    def test_test_coverage_gaps_schema_rejects_empty_surface_cell(self) -> None:
        content = """# Review: x

## Test Coverage Gaps (1)

| # | Surface | File | Why uncovered | Suggested test |
|---|---------|------|---------------|----------------|
| 1 |  | `app/foo.rb:1` | new | `spec/foo_spec.rb` |
"""
        passed, reason = output_checks.has_review_test_coverage_gaps_schema(content)
        self.assertFalse(passed)
        self.assertIn("Surface", reason)

    def test_test_coverage_gaps_schema_skips_when_section_absent(self) -> None:
        content = """# Review: x

## Summary

PASS
"""
        passed, _ = output_checks.has_review_test_coverage_gaps_schema(content)
        self.assertTrue(passed)

    def test_finding_titles_match_glance_rejects_paraphrased_title(self) -> None:
        # Detail heading uses one phrasing; At-a-Glance uses paraphrase.
        # Triage row-to-detail lookup fails → reject.
        content = """# Review: x

## Warnings (1)

### 1. Retry policy change is not covered by a focused spec

**File**: `app/foo.rb:1`
**Reviewer**: r | **Confidence**: HIGH

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Retry policy lacks spec coverage | Warning | HIGH | r | app/foo.rb:1 | Yes |
"""
        passed, reason = output_checks.has_review_finding_titles_match_glance(content)
        self.assertFalse(passed)
        self.assertIn("Retry policy lacks spec coverage", reason)

    def test_finding_titles_match_glance_accepts_verbatim(self) -> None:
        content = """# Review: x

## Warnings (1)

### 1. Retry policy change is not covered by a focused spec

**File**: `app/foo.rb:1`
**Reviewer**: r | **Confidence**: HIGH

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Retry policy change is not covered by a focused spec | Warning | HIGH | r | app/foo.rb:1 | Yes |
"""
        passed, _ = output_checks.has_review_finding_titles_match_glance(content)
        self.assertTrue(passed)

    def test_finding_titles_match_glance_skips_pre_existing_rows(self) -> None:
        # Pre-existing rows have no `### N.` heading. Skip.
        content = """# Review: x

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | Old issue summary | Blocker | HIGH | r | app/foo.rb:1 | Pre-existing |
"""
        passed, _ = output_checks.has_review_finding_titles_match_glance(content)
        self.assertTrue(passed)

    def test_has_review_file_refs_ignores_stray_outside_bucket(self) -> None:
        # `**File**:` line in preamble/footer (NOT under
        # ## Blockers / ## Warnings / ## Suggestions) MUST NOT count
        # toward the minimum. With a real finding inside `## Warnings`
        # missing its `**File**:` line, the only ref is the stray
        # preamble one; validator must not credit it.
        content = """# Review: x

**File**: `header/preamble.rb:1`

## Warnings (1)

### 1. Issue

**Reviewer**: r | **Confidence**: HIGH
**Issue**: bad
"""
        passed, reason = output_checks.has_review_file_refs(content, minimum=1)
        self.assertFalse(passed)
        self.assertIn("0 finding file ref", reason)

    def test_review_has_no_followup_sections_rejects_next_steps(self) -> None:
        content = """# Review: sample

## Summary

- Clean enough.

## Next Steps

Use /rb:triage next.
"""
        passed, _ = output_checks.review_has_no_followup_sections(content)
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
