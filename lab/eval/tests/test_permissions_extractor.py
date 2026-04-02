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


def run_extractor(repo_root: Path, home_dir: Path, *args: str, env_updates: dict[str, str] | None = None) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home_dir)
    if env_updates:
        env.update(env_updates)
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


def transcript_dir_for(repo_root: Path, home_dir: Path) -> Path:
    return home_dir / ".claude" / "projects" / claude_project_slug(repo_root)


class PermissionsExtractorTests(unittest.TestCase):
    def test_dry_run_flag_is_accepted_for_skill_parity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle exec rails db:migrate")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only", "--dry-run")

        self.assertEqual(report["settings_scope"], "repo-only")
        self.assertEqual(report["uncovered_groups"][0]["group"], "bundle exec rails db:migrate")

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

    def test_trailing_star_permission_covers_bare_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text(
                json.dumps({"permissions": {"allow": ["Bash(git *)"]}}),
                encoding="utf-8",
            )
            write_transcript(repo, tmp, "git")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(report["uncovered_groups"], [])

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

    def test_multiline_bash_payload_records_each_command_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle exec rubocop\nbundle exec brakeman\n")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("bundle exec rubocop", groups)
        self.assertIn("bundle exec brakeman", groups)

    def test_shell_aware_split_preserves_quoted_semicolons(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "printf '%s;still-one-command' foo; bundle exec rubocop")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("printf", groups)
        self.assertIn("bundle exec rubocop", groups)
        self.assertEqual(len(groups), 2)

    def test_shell_aware_split_separates_and_or_chains(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle exec rubocop && bundle exec brakeman || echo fail")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("bundle exec rubocop", groups)
        self.assertIn("bundle exec brakeman", groups)
        self.assertIn("echo", groups)

    def test_python_module_commands_keep_module_name_in_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "python3 -m pytest spec/models")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("python3 -m pytest", groups)

    def test_shell_aware_split_separates_background_operator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle install & rake db:migrate")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("bundle", groups)
        self.assertIn("rake db:migrate", groups)

    def test_shell_aware_split_does_not_break_redirection_ampersands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle exec rspec spec/models/user_spec.rb 2>&1")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = [entry["group"] for entry in report["uncovered_groups"]]
        self.assertEqual(groups, ["bundle exec rspec"])

    def test_shell_aware_split_treats_heredoc_body_as_single_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(
                repo,
                tmp,
                "cat <<'EOF'\nfoo;bar\nEOF\n",
            )

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = [entry["group"] for entry in report["uncovered_groups"]]
        self.assertEqual(groups, ["cat"])

    def test_shell_aware_split_ignores_comment_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "echo ok # this ; is comment")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = [entry["group"] for entry in report["uncovered_groups"]]
        self.assertEqual(groups, ["echo"])

    def test_shell_aware_split_separates_single_pipelines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "ps aux | grep sidekiq")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("ps", groups)
        self.assertIn("grep", groups)

    def test_git_grouping_skips_leading_git_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "git -C services/payments status")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        groups = [entry["group"] for entry in report["uncovered_groups"]]
        self.assertEqual(groups, ["git status"])

    def test_dot_slash_binstub_commands_normalize_for_grouping_and_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text(
                json.dumps({"permissions": {"allow": ["Bash(bin/rails *)"]}}),
                encoding="utf-8",
            )
            write_transcript(repo, tmp, "./bin/rails db:migrate")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(report["uncovered_groups"], [])

    def test_project_slug_with_glob_metacharacters_still_discovers_transcripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo[abc]"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle exec rubocop")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(report["scanned_sessions"], 1)
        self.assertEqual(report["uncovered_groups"][0]["group"], "bundle exec rubocop")

    def test_symlinked_transcript_files_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            transcript_dir = transcript_dir_for(repo, tmp)
            transcript_dir.mkdir(parents=True, exist_ok=True)
            external = tmp / "external.jsonl"
            external.write_text(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "Bash",
                                    "input": {"command": "bundle exec rubocop"},
                                }
                            ]
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            os.symlink(external, transcript_dir / "link.jsonl")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(report["scanned_sessions"], 0)
        self.assertEqual(report["uncovered_groups"], [])

    def test_malformed_transcript_lines_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            write_transcript(repo, tmp, "bundle exec rubocop", "good.jsonl")
            transcript_dir = transcript_dir_for(repo, tmp)
            (transcript_dir / "bad.jsonl").write_text("{not-json}\n", encoding="utf-8")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(report["malformed_lines"], 1)
        groups = {entry["group"] for entry in report["uncovered_groups"]}
        self.assertIn("bundle exec rubocop", groups)

    def test_invalid_settings_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text("{not-json}\n", encoding="utf-8")
            write_transcript(repo, tmp, "bundle exec rubocop")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(
            [Path(path).resolve() for path in report["invalid_settings_files"]],
            [(repo / ".claude" / "settings.json").resolve()],
        )
        self.assertEqual(report["uncovered_groups"][0]["group"], "bundle exec rubocop")

    def test_unreadable_settings_files_are_reported_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            settings = repo / ".claude" / "settings.json"
            settings.write_text(json.dumps({"permissions": {"allow": ["Bash(bundle *)"]}}), encoding="utf-8")
            settings.chmod(0)
            write_transcript(repo, tmp, "bundle exec rubocop")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertEqual(
            [Path(path).resolve() for path in report["invalid_settings_files"]],
            [settings.resolve()],
        )
        self.assertEqual(report["uncovered_groups"][0]["group"], "bundle exec rubocop")

    def test_deny_patterns_participate_in_deprecated_pattern_reporting(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = tmp / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".claude").mkdir()
            (repo / ".claude" / "settings.json").write_text(
                json.dumps({"permissions": {"deny": ["Bash(git:*)"]}}),
                encoding="utf-8",
            )
            write_transcript(repo, tmp, "bundle exec rubocop")

            report = run_extractor(repo, tmp, "--days", "30", "--repo-only")

        self.assertIn("Bash(git:*)", report["deprecated_patterns"])


if __name__ == "__main__":
    unittest.main()
