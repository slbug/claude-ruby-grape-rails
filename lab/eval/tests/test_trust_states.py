import tempfile
import unittest
from pathlib import Path

from lab.eval import output_checks


class TrustStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_detects_clean(self) -> None:
        p = self.tmp_path / "a.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "clean")

    def test_detects_weak_single_source(self) -> None:
        p = self.tmp_path / "a.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "weak")

    def test_detects_conflicted(self) -> None:
        p = self.tmp_path / "a.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts:\n"
            "  - claim: c1\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "conflicted")

    def test_detects_missing(self) -> None:
        p = self.tmp_path / "does-not-exist.provenance.md"
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_no_frontmatter_maps_to_missing(self) -> None:
        p = self.tmp_path / "legacy.provenance.md"
        p.write_text("# Provenance: foo\n\n**Conflicts**: 0\n")
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_unterminated_frontmatter_maps_to_missing(self) -> None:
        p = self.tmp_path / "broken.provenance.md"
        p.write_text("---\nclaims:\n  - id: c1\n")  # no closing ---
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_malformed_yaml_maps_to_missing(self) -> None:
        p = self.tmp_path / "broken.provenance.md"
        p.write_text("---\nclaims: [unclosed\n---\n")
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_non_dict_frontmatter_maps_to_missing(self) -> None:
        p = self.tmp_path / "scalar.provenance.md"
        p.write_text("---\njust-a-string\n---\n")
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_empty_claims_or_sources_map_to_missing(self) -> None:
        p = self.tmp_path / "empty.provenance.md"
        p.write_text("---\nclaims: []\nsources: []\nconflicts: []\n---\n")
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_claims_as_dict_maps_to_missing(self) -> None:
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  c1: {}\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_claim_without_id_maps_to_missing(self) -> None:
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - description: missing id field\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_claim_id_non_string_maps_to_missing(self) -> None:
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: 1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [1]\n"
            "  - kind: primary\n"
            "    supports: [1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_conflicts_as_dict_maps_to_missing(self) -> None:
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts:\n"
            "  c1: disputed\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_conflicts_as_string_maps_to_missing(self) -> None:
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: nope\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_supports_as_string_maps_to_missing(self) -> None:
        """`supports: c1` (string instead of list) must NOT iterate
        character-by-character; it is malformed schema → missing."""
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: c1\n"
            "  - kind: primary\n"
            "    supports: c1\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_supports_with_non_string_entry_maps_to_missing(self) -> None:
        p = self.tmp_path / "shape.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_inline_triple_dash_in_value_does_not_split_frontmatter(self) -> None:
        """A `---` substring inside a YAML value (URL fragment, string)
        must not be treated as the closing delimiter."""
        p = self.tmp_path / "inline-dash.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    url: https://example.com/path---with-dashes\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    url: https://example.com/other\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "clean")

    def test_missing_conflicts_key_maps_to_missing(self) -> None:
        """`conflicts` is required schema; absence is malformed → missing."""
        p = self.tmp_path / "no-conflicts.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_missing_claims_key_maps_to_missing(self) -> None:
        p = self.tmp_path / "no-claims.provenance.md"
        p.write_text(
            "---\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_missing_sources_key_maps_to_missing(self) -> None:
        p = self.tmp_path / "no-sources.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_missing_kind_maps_to_missing(self) -> None:
        p = self.tmp_path / "no-kind.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - supports: [c1]\n"
            "  - supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_unknown_kind_maps_to_missing(self) -> None:
        p = self.tmp_path / "bad-kind.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: hearsay\n"
            "    supports: [c1]\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_missing_supports_key_maps_to_missing(self) -> None:
        p = self.tmp_path / "no-supports.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_empty_supports_list_maps_to_missing(self) -> None:
        p = self.tmp_path / "empty-supports.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: []\n"
            "  - kind: primary\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "missing")

    def test_duplicate_supports_in_one_source_does_not_satisfy_two_source_rule(self) -> None:
        """Single source listing `[c1, c1]` must not be counted as 2 supports."""
        p = self.tmp_path / "dup.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: primary\n"
            "    supports: [c1, c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "weak")

    def test_tool_only_sources_map_to_weak(self) -> None:
        p = self.tmp_path / "tool.provenance.md"
        p.write_text(
            "---\n"
            "claims:\n"
            "  - id: c1\n"
            "sources:\n"
            "  - kind: tool-output\n"
            "    supports: [c1]\n"
            "  - kind: tool-output\n"
            "    supports: [c1]\n"
            "conflicts: []\n"
            "---\n"
        )
        self.assertEqual(output_checks.compute_trust_state(p), "weak")


if __name__ == "__main__":
    unittest.main()
