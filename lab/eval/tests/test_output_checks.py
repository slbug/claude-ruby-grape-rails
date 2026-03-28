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


if __name__ == "__main__":
    unittest.main()
