from __future__ import annotations

import unittest

from lab.eval import artifact_scorer


class ArtifactScorerTests(unittest.TestCase):
    def test_research_suite_matches_fixture_expectations(self) -> None:
        result = artifact_scorer.score_suite("research")
        self.assertEqual(result["summary"]["matched"], result["summary"]["total"])
        self.assertEqual(result["summary"]["composite"], 1.0)

    def test_review_suite_matches_fixture_expectations(self) -> None:
        result = artifact_scorer.score_suite("review")
        self.assertEqual(result["summary"]["matched"], result["summary"]["total"])
        self.assertEqual(result["summary"]["composite"], 1.0)

    def test_research_bad_fixture_fails_expected_checks(self) -> None:
        fixture = next(spec for spec in artifact_scorer.FIXTURES["research"] if spec.name == "research-bad")
        result = artifact_scorer.score_fixture(fixture)
        self.assertEqual(
            set(result["actual_failures"]),
            {
                "research_metadata",
                "research_tiered_sources",
                "research_inline_tiers",
                "research_decision_section",
                "research_non_placeholder_sources",
                "research_provenance_external_evidence",
                "provenance_tier_summary",
                "provenance_required_fixes",
            },
        )

    def test_review_bad_fixture_fails_expected_checks(self) -> None:
        fixture = next(spec for spec in artifact_scorer.FIXTURES["review"] if spec.name == "review-bad")
        result = artifact_scorer.score_fixture(fixture)
        self.assertEqual(
            set(result["actual_failures"]),
            {
                "review_verdict",
                "review_file_refs",
                "review_mandatory_table",
                "review_no_task_lists",
                "review_no_followup_sections",
                "review_provenance_local_evidence",
                "provenance_claim_entries",
                "provenance_required_fixes",
            },
        )


if __name__ == "__main__":
    unittest.main()
