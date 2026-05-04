import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from lab.eval import check_refs


def _make_plugin(tmp_root: Path) -> Path:
    root = tmp_root / "plugins" / "ruby-grape-rails"
    (root / "skills").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    return root


class CheckRefsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_resolves_slash_command(self) -> None:
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: rb:foo\n---\nSee /rb:bar\n"
        )
        (plugin_root / "skills" / "bar").mkdir()
        (plugin_root / "skills" / "bar" / "SKILL.md").write_text(
            "---\nname: rb:bar\n---\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(result.broken, [])

    def test_flags_missing_slash_command(self) -> None:
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: rb:foo\n---\nSee /rb:nonexistent\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(len(result.broken), 1)
        self.assertEqual(result.broken[0].target, "nonexistent")
        self.assertIn("foo/SKILL.md", result.broken[0].source)

    def test_non_command_skill_does_not_resolve_slash(self) -> None:
        """`/rb:active-record-patterns` must NOT resolve when the skill's
        frontmatter `name:` lacks the `rb:` prefix (auto-loading skill,
        not a user-invocable command)."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "active-record-patterns").mkdir()
        (plugin_root / "skills" / "active-record-patterns" / "SKILL.md").write_text(
            "---\nname: active-record-patterns\n---\n"
        )
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: rb:caller\n---\nSee /rb:active-record-patterns\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(len(result.broken), 1)
        self.assertEqual(result.broken[0].target, "active-record-patterns")

    def test_resolves_slash_alias_when_dir_name_differs(self) -> None:
        """`/rb:trace` resolves through frontmatter alias when dir is `rb-trace`."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "rb-trace").mkdir()
        (plugin_root / "skills" / "rb-trace" / "SKILL.md").write_text(
            "---\nname: rb:trace\n---\n"
        )
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: caller\n---\nSee /rb:trace\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(result.broken, [])

    def test_path_skill_ref_resolves_only_via_dir_name(self) -> None:
        """`skills/foo` reference must match dir, not frontmatter alias."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "rb-trace").mkdir()
        (plugin_root / "skills" / "rb-trace" / "SKILL.md").write_text(
            "---\nname: rb:trace\n---\n"
        )
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: caller\n---\nSee skills/trace\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(len(result.broken), 1)
        self.assertEqual(result.broken[0].target, "trace")

    def test_resolves_agent_by_filename(self) -> None:
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "agents" / "deep-bug-investigator.md").write_text(
            "---\nname: ruby-grape-rails:deep-bug-investigator\n---\n"
        )
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: caller\n---\nSee agents/deep-bug-investigator\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(result.broken, [])

    def test_flags_missing_agent(self) -> None:
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "agents" / "real-agent.md").write_text(
            "---\nname: real-agent\n---\n"
        )
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: caller\n---\nSee agents/ghost-agent\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(len(result.broken), 1)
        self.assertEqual(result.broken[0].target, "ghost-agent")

    def test_skips_4_backtick_fenced_block(self) -> None:
        """4-backtick fences (wrapping 3-backtick samples) must be respected
        end-to-end; inner 3-backtick lines must NOT close the outer fence."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: rb:caller\n---\n"
            "Real ref: /rb:nope\n"
            "\n"
            "````markdown\n"
            "Embedded sample:\n"
            "```ruby\n"
            "/rb:fake-inside-inner-fence\n"
            "```\n"
            "More body — /rb:also-fake-still-fenced\n"
            "````\n"
            "After fence: /rb:also-nope\n"
        )
        result = check_refs.scan(plugin_root)
        broken = sorted(r.target for r in result.broken)
        self.assertEqual(broken, ["also-nope", "nope"])

    def test_inner_info_string_line_does_not_close_outer_fence(self) -> None:
        """A line like `````ruby` is a NEW open per CommonMark, not a
        close. Inside a 3-backtick fence it must not terminate the fence
        and let inner refs leak as broken."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: rb:caller\n---\n"
            "```\n"
            "```ruby\n"
            "/rb:fake-still-inside\n"
            "```\n"
            "Real ref after fence: /rb:nope\n"
        )
        result = check_refs.scan(plugin_root)
        broken = sorted(r.target for r in result.broken)
        self.assertEqual(broken, ["nope"])

    def test_unterminated_fence_yields_buffered_lines_for_scanning(self) -> None:
        """If a file ends inside an open fence (missing close delimiter),
        the scanner must NOT silently skip the buffered tail — it falls
        back to scanning those lines so accidental references are still
        flagged instead of disappearing into a never-closed fence."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: rb:caller\n---\n"
            "Real ref before fence: /rb:before-nope\n"
            "```\n"
            "tail body — /rb:tail-nope\n"
            "more — /rb:also-tail-nope\n"
            # NO closing fence
        )
        result = check_refs.scan(plugin_root)
        broken = sorted(r.target for r in result.broken)
        self.assertEqual(
            broken,
            ["also-tail-nope", "before-nope", "tail-nope"],
        )

    def test_skips_fenced_code_blocks(self) -> None:
        """References inside fenced code blocks are not flagged."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: caller\n---\n"
            "Real ref: /rb:nope\n"
            "\n"
            "```bash\n"
            "# example only — /rb:fictional should NOT flag\n"
            "```\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(len(result.broken), 1)
        self.assertEqual(result.broken[0].target, "nope")

    def test_orphan_chain_both_flagged(self) -> None:
        """Orphan reference docs that link only to each other must BOTH
        be flagged. Detector must not let an unreached doc count as a
        source for its peer — otherwise a self-supporting orphan chain
        hides itself. Regression guard for the under-reporting bug."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "a.md").write_text(
            "# A\nSee `references/b.md`.\n"
        )
        (plugin_root / "skills" / "foo" / "references" / "b.md").write_text(
            "# B\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        result = check_refs.scan(plugin_root)
        orphan_paths = sorted(o.path for o in result.orphans)
        self.assertEqual(
            orphan_paths,
            [
                "skills/foo/references/a.md",
                "skills/foo/references/b.md",
            ],
        )

    def test_reachable_chain_flags_neither(self) -> None:
        """Conversely, when a SKILL.md references doc A and A references
        doc B, both are reachable via transitive closure — neither
        should be flagged."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\nSee `${CLAUDE_SKILL_DIR}/references/a.md`.\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "a.md").write_text(
            "# A\nSee `references/b.md`.\n"
        )
        (plugin_root / "skills" / "foo" / "references" / "b.md").write_text(
            "# B\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(result.orphans, [])

    def test_orphan_ref_only_mentioned_inside_code_fence(self) -> None:
        """Reference path appearing ONLY inside a fenced code block must
        NOT count as a real reference. Otherwise an illustrative example
        in SKILL.md would shield the target from orphan detection.
        Regression guard for the fence-bypass false negative in
        `_extract_refs`."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "# Foo\n"
            "\n"
            "```\n"
            "See `references/a.md` for an example.\n"
            "```\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "a.md").write_text(
            "# A\n"
        )
        result = check_refs.scan(plugin_root)
        orphan_paths = sorted(o.path for o in result.orphans)
        self.assertEqual(orphan_paths, ["skills/foo/references/a.md"])


    def test_main_exits_nonzero_on_orphan_only(self) -> None:
        """Orphan-only result must fail CI (exit 1) — no env-var bypass.

        Captures stdout with ``redirect_stdout`` so the failure
        diagnostic does not leak into the test runner output AND so we
        can assert the nonzero exit was caused by the orphan branch
        (rather than a different unrelated failure).
        """
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "orphan.md").write_text(
            "# Orphan\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = check_refs.main(["check_refs", str(plugin_root)])
        out = buf.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("ORPHAN_REFERENCE_FILE", out)
        self.assertIn("skills/foo/references/orphan.md", out)
        # No other failure class should fire here.
        self.assertNotIn("BROKEN_REFERENCE_PATH", out)
        self.assertNotIn("BROKEN_REGISTRY_REFERENCE", out)
        self.assertNotIn("TRAVERSAL_REFERENCE", out)

    def test_traversal_reference_flagged(self) -> None:
        """`${CLAUDE_SKILL_DIR}/../<other>` should be flagged as
        TraversalRef — cross-skill paths must use `${CLAUDE_PLUGIN_ROOT}`.
        """
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "See `${CLAUDE_SKILL_DIR}/../bar/references/x.md`.\n"
        )
        (plugin_root / "skills" / "bar").mkdir()
        (plugin_root / "skills" / "bar" / "references").mkdir()
        (plugin_root / "skills" / "bar" / "references" / "x.md").write_text(
            "# X\n"
        )
        result = check_refs.scan(plugin_root)
        targets = sorted(t.target for t in result.traversal)
        self.assertIn("../bar/references/x.md", targets)

    def test_plain_broken_reference_via_skill_dir_var(self) -> None:
        """``${CLAUDE_SKILL_DIR}/references/<missing>.md`` resolves
        through the skill-local var path; missing target flagged as
        BROKEN_REFERENCE_PATH."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "See `${CLAUDE_SKILL_DIR}/references/missing.md`.\n"
        )
        result = check_refs.scan(plugin_root)
        targets = sorted(b.target for b in result.plain_broken)
        self.assertIn("skills/foo/references/missing.md", targets)

    def test_plain_broken_reference_via_bare_path(self) -> None:
        """Bare ``references/<missing>.md`` (no var prefix) at a
        token-start position resolves against the owning skill dir.
        Exercises the bare-path branch of ``_extract_ref_sites`` —
        distinct from the ``${CLAUDE_SKILL_DIR}/...`` branch — and
        confirms a missing target is flagged."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "See references/missing.md for details.\n"
        )
        result = check_refs.scan(plugin_root)
        targets = sorted(b.target for b in result.plain_broken)
        self.assertIn("skills/foo/references/missing.md", targets)

    def test_non_md_reference_asset_orphan_detection(self) -> None:
        """A `.py` reference asset under `references/` with no consumer
        should be flagged as orphan."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "helper.py").write_text(
            "# helper\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        result = check_refs.scan(plugin_root)
        orphan_paths = sorted(o.path for o in result.orphans)
        self.assertIn("skills/foo/references/helper.py", orphan_paths)

    def _run_main(
        self, plugin_root: Path
    ) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = check_refs.main(["check_refs", str(plugin_root)])
        return rc, buf.getvalue()

    def _empty_registries(self, plugin_root: Path) -> None:
        (plugin_root / "references").mkdir(exist_ok=True)
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )

    def test_main_exits_nonzero_on_broken_slash_reference(self) -> None:
        """Broken `/rb:<name>` invocation must fail CLI with the broken-ref
        diagnostic in stdout."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "caller").mkdir()
        (plugin_root / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: rb:caller\n---\nSee /rb:nonexistent.\n"
        )
        self._empty_registries(plugin_root)
        rc, out = self._run_main(plugin_root)
        self.assertEqual(rc, 1)
        self.assertIn("broken references", out)
        self.assertIn("nonexistent", out)
        self.assertNotIn("ORPHAN_REFERENCE_FILE", out)
        self.assertNotIn("BROKEN_REGISTRY_REFERENCE", out)
        self.assertNotIn("TRAVERSAL_REFERENCE", out)

    def test_main_exits_nonzero_on_broken_registry_reference(self) -> None:
        """`reference_files` entry pointing at a missing file must fail
        CLI with BROKEN_REGISTRY_REFERENCE in stdout."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 1\n"
            "categories:\n"
            "  - id: cat\n"
            "    name: cat\n"
            "    law_count: 1\n"
            "laws:\n"
            "  - id: 1\n"
            "    category: cat\n"
            "    title: t\n"
            "    rule: r\n"
            "    summary_text: s\n"
            "    rationale: rat\n"
            "    subagent_text: sub\n"
            "    reference_files:\n"
            "      - skills/foo/references/missing.md\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        rc, out = self._run_main(plugin_root)
        self.assertEqual(rc, 1)
        self.assertIn("BROKEN_REGISTRY_REFERENCE", out)
        self.assertIn("skills/foo/references/missing.md", out)

    def test_main_exits_nonzero_on_traversal_reference(self) -> None:
        """`${CLAUDE_SKILL_DIR}/../<other>` must fail CLI with
        TRAVERSAL_REFERENCE in stdout."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "See `${CLAUDE_SKILL_DIR}/../bar/references/x.md`.\n"
        )
        (plugin_root / "skills" / "bar").mkdir()
        (plugin_root / "skills" / "bar" / "references").mkdir()
        (plugin_root / "skills" / "bar" / "references" / "x.md").write_text(
            "# X\n"
        )
        self._empty_registries(plugin_root)
        rc, out = self._run_main(plugin_root)
        self.assertEqual(rc, 1)
        self.assertIn("TRAVERSAL_REFERENCE", out)
        self.assertIn("../bar/references/x.md", out)

    def test_main_exits_nonzero_on_plain_broken_reference(self) -> None:
        """Missing prose-extracted reference path must fail CLI with
        BROKEN_REFERENCE_PATH in stdout."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "See `${CLAUDE_SKILL_DIR}/references/missing.md`.\n"
        )
        self._empty_registries(plugin_root)
        rc, out = self._run_main(plugin_root)
        self.assertEqual(rc, 1)
        self.assertIn("BROKEN_REFERENCE_PATH", out)
        self.assertIn("skills/foo/references/missing.md", out)

    def test_dotslash_reference_resolves_skill_local(self) -> None:
        """``./references/foo.md`` from a SKILL.md is markdown shorthand
        for "current directory" — must resolve against the owning skill
        dir, NOT against plugin root. Regression guard for the
        false-broken/false-orphan bug on common dot-slash markdown link
        style."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\nSee [doc](./references/local.md).\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "local.md").write_text(
            "# local\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        result = check_refs.scan(plugin_root)
        # The dot-slash link must NOT produce a broken-path or orphan.
        self.assertEqual(
            [],
            result.plain_broken,
            f"unexpected broken: {[b.target for b in result.plain_broken]}",
        )
        self.assertEqual(
            [],
            result.orphans,
            f"unexpected orphans: {[o.path for o in result.orphans]}",
        )

    def test_dotdotslash_reference_NOT_treated_as_skill_local(self) -> None:
        """``../references/foo.md`` is upward traversal, NOT skill-local.
        Detector must not be fooled by the trailing ``./`` substring.
        The captured suffix ``references/foo.md`` is treated as
        plugin-root-relative; mismatch is reported as plain broken."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\nSee [doc](../references/sibling.md).\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        # Note: file lives under the foo skill dir; the ``..`` traversal
        # in prose targets a NON-EXISTENT plugin-root location.
        (plugin_root / "skills" / "foo" / "references" / "sibling.md").write_text(
            "# sibling\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        result = check_refs.scan(plugin_root)
        broken_targets = [b.target for b in result.plain_broken]
        # Captured suffix is plugin-root-relative, not skill-local.
        self.assertIn("references/sibling.md", broken_targets)

    def test_non_md_reference_asset_consumed_by_skill_md(self) -> None:
        """A `.py` reference asset is reachable when SKILL.md mentions
        the path. Consumer reachability via prose must include the
        non-md asset extension."""
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\n"
            "Run `${CLAUDE_SKILL_DIR}/references/helper.py` to compute.\n"
        )
        (plugin_root / "skills" / "foo" / "references").mkdir()
        (plugin_root / "skills" / "foo" / "references" / "helper.py").write_text(
            "# helper\n"
        )
        (plugin_root / "references").mkdir()
        (plugin_root / "references" / "iron-laws.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_laws: 0\ncategories: []\nlaws: []\n"
        )
        (plugin_root / "references" / "preferences.yml").write_text(
            "version: 1.0.0\nlast_updated: 2026-05-04\n"
            "total_preferences: 0\ncategories: []\npreferences: []\n"
        )
        result = check_refs.scan(plugin_root)
        orphan_paths = sorted(o.path for o in result.orphans)
        self.assertNotIn("skills/foo/references/helper.py", orphan_paths)


if __name__ == "__main__":
    unittest.main()
