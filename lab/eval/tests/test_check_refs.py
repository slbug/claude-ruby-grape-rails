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

    def test_resolves_skill_name(self) -> None:
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\nSee /rb:bar\n"
        )
        (plugin_root / "skills" / "bar").mkdir()
        (plugin_root / "skills" / "bar" / "SKILL.md").write_text(
            "---\nname: bar\n---\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(result.broken, [])

    def test_flags_missing_skill(self) -> None:
        plugin_root = _make_plugin(self.tmp_path)
        (plugin_root / "skills" / "foo").mkdir()
        (plugin_root / "skills" / "foo" / "SKILL.md").write_text(
            "---\nname: foo\n---\nSee /rb:nonexistent\n"
        )
        result = check_refs.scan(plugin_root)
        self.assertEqual(len(result.broken), 1)
        self.assertEqual(result.broken[0].target, "nonexistent")
        self.assertIn("foo/SKILL.md", result.broken[0].source)

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


if __name__ == "__main__":
    unittest.main()
