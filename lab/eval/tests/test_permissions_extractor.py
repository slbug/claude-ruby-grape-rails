from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACT_PERMISSIONS = REPO_ROOT / "plugins/ruby-grape-rails/skills/permissions/scripts/extract_permissions.rb"


def claude_project_slug(repo_root: Path) -> str:
    resolved = repo_root.resolve()
    return str(resolved).replace("/", "-").replace(":", "-").replace("\\", "-")


def run_extractor(repo_root: Path, home_dir: Path, *args: str) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home_dir)
    result = subprocess.run(
        ["ruby", str(EXTRACT_PERMISSIONS), "--json", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def write_transcript(repo_root: Path, home_dir: Path, command: str, name: str = "session.jsonl") -> None:
    slug = claude_project_slug(repo_root)
    transcript_dir = home_dir / ".claude" / "projects" / slug
    transcript_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "Bash",
                    "input": {"command": command},
                }
            ]
        },
    }
    (transcript_dir / name).write_text(json.dumps(payload) + "\n", encoding="utf-8")


class PermissionsExtractorTests(unittest.TestCase):
    def test_repo_only_ignores_global_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            (tmp / ".claude").mkdir()
            (tmp / ".claude" / "settings.json").write_text(
                json.dumps({"permissions": {"allow": ["Bash(bundle exec rails db:migrate)"]}}),
                encoding="utf-8",
            )
            write_transcript(repo, tmp, "env RAILS_ENV=test bundle exec rails db:migrate")

            mixed = run_extractor(repo, tmp, "--days", "30")
            repo_only = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(mixed["settings_scope"], "repo+global")
        self.assertEqual(repo_only["settings_scope"], "repo-only")
        self.assertEqual(mixed["uncovered_groups"], [])
        self.assertEqual(repo_only["uncovered_groups"][0]["group"], "bundle exec rails db:migrate")

    def test_interpreter_grouping_keeps_script_targets_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "ruby script/a.rb", "a.jsonl")
            write_transcript(repo, tmp, "ruby script/b.rb", "b.jsonl")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("ruby script/a.rb", groups)
        self.assertIn("ruby script/b.rb", groups)
        self.assertEqual(len(groups), 2)


if __name__ == "__main__":
    unittest.main()
