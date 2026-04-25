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
