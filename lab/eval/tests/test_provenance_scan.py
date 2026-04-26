"""Subprocess-driven tests for the provenance-scan Ruby CLI.

Uses unittest.TestCase to match the rest of lab/eval/tests/. CI runs
`python3 -m unittest discover` via scripts/run-eval-tests.sh, so
pytest-only conventions (tmp_path, bare assert) would silently skip.
"""

import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "plugins" / "ruby-grape-rails" / "bin" / "provenance-scan"


CLEAN_SIDECAR = textwrap.dedent(
    """\
    ---
    claims:
      - id: c1
    sources:
      - kind: primary
        supports: [c1]
      - kind: primary
        supports: [c1]
    conflicts: []
    ---

    # Provenance: clean
    """
)


WEAK_SINGLE_SOURCE_SIDECAR = textwrap.dedent(
    """\
    ---
    claims:
      - id: c1
    sources:
      - kind: primary
        supports: [c1]
    conflicts: []
    ---

    # Provenance: weak
    """
)


WEAK_TOOL_ONLY_SIDECAR = textwrap.dedent(
    """\
    ---
    claims:
      - id: c1
    sources:
      - kind: tool-output
        supports: [c1]
      - kind: tool-output
        supports: [c1]
    conflicts: []
    ---

    # Provenance: weak (all tool-output)
    """
)


CONFLICTED_SIDECAR = textwrap.dedent(
    """\
    ---
    claims:
      - id: c1
    sources:
      - kind: primary
        supports: [c1]
      - kind: secondary
        supports: [c1]
    conflicts:
      - claim: c1
        sources: [primary, secondary]
    ---

    # Provenance: conflicted
    """
)


NO_FRONTMATTER_SIDECAR = "# Provenance: no frontmatter at all\n"


MALFORMED_YAML_SIDECAR = textwrap.dedent(
    """\
    ---
    claims:
      - id: c1
    sources:
      - kind: primary
        supports: [c1
    conflicts: []
    ---
    """
)


def run_scan(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ruby", str(CLI), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def parse_summary(stdout: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in stdout.splitlines():
        match = re.match(r"^\s+(clean|weak|conflicted|missing):\s+(\d+)$", line)
        if match:
            counts[match.group(1)] = int(match.group(2))
    return counts


def write_sidecar(root: Path, relative: str, body: str) -> Path:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


class ProvenanceScanEmptyTreeTests(unittest.TestCase):
    def test_empty_tree_writes_zero_distribution_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            result = run_scan(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scanned 0 sidecar(s).", result.stdout)
            self.assertEqual(
                parse_summary(result.stdout),
                {"clean": 0, "weak": 0, "conflicted": 0, "missing": 0},
            )
            reports = list((tmp / ".claude" / "provenance-scan").glob("report-*.md"))
            self.assertEqual(len(reports), 1)
            report_text = reports[0].read_text(encoding="utf-8")
            self.assertIn("## Distribution", report_text)
            self.assertIn("- clean: 0", report_text)
            self.assertIn("## Per-file", report_text)
            self.assertIn("No `*.provenance.md` sidecars found", report_text)


class ProvenanceScanStateClassificationTests(unittest.TestCase):
    """One test per state. Each writes a single sidecar matching that
    state and asserts the distribution reports exactly one occurrence
    in the matching bucket and zero in the others."""

    def _scan_with_single_sidecar(
        self, body: str, expected_state: str
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            write_sidecar(tmp, ".claude/research/topic.provenance.md", body)
            result = run_scan(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            counts = parse_summary(result.stdout)
            self.assertEqual(counts[expected_state], 1, result.stdout)
            for other in ("clean", "weak", "conflicted", "missing"):
                if other == expected_state:
                    continue
                self.assertEqual(counts[other], 0, f"{other}: {result.stdout}")

    def test_clean_sidecar(self) -> None:
        self._scan_with_single_sidecar(CLEAN_SIDECAR, "clean")

    def test_weak_single_source(self) -> None:
        self._scan_with_single_sidecar(WEAK_SINGLE_SOURCE_SIDECAR, "weak")

    def test_weak_tool_output_only(self) -> None:
        self._scan_with_single_sidecar(WEAK_TOOL_ONLY_SIDECAR, "weak")

    def test_conflicted_sidecar(self) -> None:
        self._scan_with_single_sidecar(CONFLICTED_SIDECAR, "conflicted")

    def test_missing_no_frontmatter(self) -> None:
        self._scan_with_single_sidecar(NO_FRONTMATTER_SIDECAR, "missing")

    def test_missing_malformed_yaml(self) -> None:
        self._scan_with_single_sidecar(MALFORMED_YAML_SIDECAR, "missing")


class ProvenanceScanScannedRootsTests(unittest.TestCase):
    def test_walks_all_documented_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            write_sidecar(tmp, ".claude/research/r.provenance.md", CLEAN_SIDECAR)
            write_sidecar(tmp, ".claude/reviews/v.provenance.md", CLEAN_SIDECAR)
            write_sidecar(tmp, ".claude/audit/a.provenance.md", CLEAN_SIDECAR)
            write_sidecar(
                tmp,
                ".claude/plans/feature-x/research/s.provenance.md",
                CLEAN_SIDECAR,
            )
            write_sidecar(
                tmp,
                ".claude/plans/feature-x/reviews/t.provenance.md",
                CLEAN_SIDECAR,
            )
            result = run_scan(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scanned 5 sidecar(s).", result.stdout)
            counts = parse_summary(result.stdout)
            self.assertEqual(counts["clean"], 5)

    def test_ignores_non_provenance_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            write_sidecar(tmp, ".claude/research/note.md", "# not a sidecar\n")
            write_sidecar(
                tmp, ".claude/research/topic.provenance.md", CLEAN_SIDECAR
            )
            result = run_scan(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scanned 1 sidecar(s).", result.stdout)


class ProvenanceScanReportOrderingTests(unittest.TestCase):
    def test_per_file_section_orders_by_urgency(self) -> None:
        # Most urgent first: conflicted → missing → weak → clean. Within a
        # state, alphabetical by relative path. The report's per-file
        # section matters for triage — surface the items that need
        # attention before the noise.
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            write_sidecar(
                tmp, ".claude/research/a-clean.provenance.md", CLEAN_SIDECAR
            )
            write_sidecar(
                tmp,
                ".claude/research/b-conflicted.provenance.md",
                CONFLICTED_SIDECAR,
            )
            write_sidecar(
                tmp,
                ".claude/research/c-missing.provenance.md",
                NO_FRONTMATTER_SIDECAR,
            )
            write_sidecar(
                tmp, ".claude/research/d-weak.provenance.md", WEAK_SINGLE_SOURCE_SIDECAR
            )
            result = run_scan(tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = next(
                (tmp / ".claude" / "provenance-scan").glob("report-*.md")
            )
            text = report.read_text(encoding="utf-8")
            per_file = text.split("## Per-file", 1)[1]
            order = [
                line.split("—", 1)[1].strip()
                for line in per_file.splitlines()
                if line.startswith("- `")
            ]
            self.assertEqual(order, ["conflicted", "missing", "weak", "clean"])


class ProvenanceScanExitCodeTests(unittest.TestCase):
    def test_exit_code_is_zero_regardless_of_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            write_sidecar(
                tmp, ".claude/research/x.provenance.md", CONFLICTED_SIDECAR
            )
            result = run_scan(tmp)
            # The CLI is deterministic — distribution drives the report,
            # not the exit code. Callers chain it without bash branching.
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_nonexistent_root_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_root = Path(tmpdir) / "does-not-exist"
            result = subprocess.run(
                ["ruby", str(CLI), "--root", str(missing_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("root not a directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
