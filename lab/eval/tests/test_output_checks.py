from __future__ import annotations

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
