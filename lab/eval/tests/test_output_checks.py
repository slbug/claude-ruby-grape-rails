
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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
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
| ruby-reviewer | unknown-state | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
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
        self.assertIn("BLOCKER / {n} WARNING / {n} SUGGESTION", reason)

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION | junk |
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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
| testing-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
| testing-reviewer | artifact | 0 BLOCKER / 1 WARNING / 0 SUGGESTION |

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
| security-analyzer | stub-no-output | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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
| testing-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 0 SUGGESTION |

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

    def test_verdict_matches_summary_rejects_blocked_with_zero_counts(self) -> None:
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
