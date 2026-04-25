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
