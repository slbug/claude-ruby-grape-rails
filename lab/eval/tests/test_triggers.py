"""Contributor tests for trigger-matcher CLI (Ruby runtime).

Uses `unittest.TestCase` to match the rest of `lab/eval/tests/`; CI runs
`python3 -m unittest discover` via `scripts/run-eval-tests.sh`, so
pytest-only conventions (`tmp_path`, bare `assert`) would be skipped.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "lab" / "eval" / "bin" / "match-trigger"
TRIGGERS = REPO / "plugins" / "ruby-grape-rails" / "references" / "compression" / "triggers.yml"


def _matches(cmd: str, triggers: Path = TRIGGERS) -> bool:
    proc = subprocess.run(
        [str(CLI), "--triggers", str(triggers), "--cmd", cmd],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


class TriggerMatcherTests(unittest.TestCase):
    def test_matches_rspec(self) -> None:
        self.assertTrue(_matches("rspec spec/models/user_spec.rb"))

    def test_matches_bundle_exec_brakeman(self) -> None:
        self.assertTrue(_matches("bundle exec brakeman"))

    def test_matches_rails_db_migrate(self) -> None:
        self.assertTrue(_matches("bundle exec rails db:migrate"))

    def test_does_not_match_rake_routes(self) -> None:
        self.assertFalse(_matches("bundle exec rake routes"))

    def test_rake_excluded_wins_over_trigger(self) -> None:
        # rake db:drop must NEVER trigger compression even if rake_verify_only had overlap
        self.assertFalse(_matches("bundle exec rake db:drop"))

    def test_unrelated_command(self) -> None:
        self.assertFalse(_matches("ls -la"))

    def test_matches_env_prefix_rspec(self) -> None:
        self.assertTrue(_matches("RAILS_ENV=test rspec spec/models/user_spec.rb"))

    def test_matches_multi_env_prefix_bundle_exec(self) -> None:
        self.assertTrue(_matches("RAILS_ENV=test BUNDLE_GEMFILE=Gemfile bundle exec rspec"))

    def test_matches_env_prefix_rails_db_migrate(self) -> None:
        self.assertTrue(_matches("RAILS_ENV=production bundle exec rails db:migrate"))

    def test_env_prefix_does_not_bypass_rake_excluded(self) -> None:
        self.assertFalse(_matches("RAILS_ENV=test bundle exec rake db:drop"))

    def test_does_not_match_rtk_rspec(self) -> None:
        # rtk's PreToolUse rewrite produces `rtk rspec` — must NOT compress.
        self.assertFalse(_matches("rtk rspec spec/foo_spec.rb"))

    def test_matches_binstub_rspec(self) -> None:
        self.assertTrue(_matches("bin/rspec spec/models/user_spec.rb"))

    def test_matches_dot_slash_binstub_rspec(self) -> None:
        self.assertTrue(_matches("./bin/rspec spec/models/user_spec.rb"))

    def test_matches_env_prefix_binstub_rspec(self) -> None:
        self.assertTrue(_matches("RAILS_ENV=test bin/rspec spec/models/user_spec.rb"))

    def test_matches_binstub_rake_verify(self) -> None:
        self.assertTrue(_matches("bin/rake test"))

    def test_binstub_rake_excluded_still_wins(self) -> None:
        self.assertFalse(_matches("bin/rake routes"))

    def test_does_not_match_system_bin_rspec(self) -> None:
        # `/bin/rspec` (absolute system path) must NOT match — only the
        # in-repo binstub forms `bin/rspec` and `./bin/rspec` count.
        self.assertFalse(_matches("/bin/rspec spec/foo"))

    def test_does_not_match_dot_bin_directory(self) -> None:
        # A literal `.bin/` directory (typo of `./bin/`) must not match.
        self.assertFalse(_matches(".bin/rspec spec/foo"))

    def test_matches_rails_test(self) -> None:
        # Rails 5+ canonical: `rails test` replaces `rake test`.
        self.assertTrue(_matches("rails test"))

    def test_matches_rails_test_with_path(self) -> None:
        self.assertTrue(_matches("rails test test/models/user_test.rb"))

    def test_matches_rails_test_system(self) -> None:
        self.assertTrue(_matches("rails test:system"))

    def test_matches_binstub_rails_test(self) -> None:
        self.assertTrue(_matches("bin/rails test"))

    def test_matches_bundle_exec_rails_test(self) -> None:
        self.assertTrue(_matches("bundle exec rails test"))

    def test_does_not_match_rails_routes(self) -> None:
        # `rails routes` mirrors `rake routes` — uncompressable table output,
        # excluded by rake_excluded.
        self.assertFalse(_matches("rails routes"))

    def test_does_not_match_rails_db_drop(self) -> None:
        self.assertFalse(_matches("rails db:drop"))

    def test_does_not_match_rails_db_create(self) -> None:
        self.assertFalse(_matches("rails db:create"))

    def test_does_not_match_rails_version(self) -> None:
        # `--version` is a static banner — exclusion applies across the whole
        # verify-tool family.
        self.assertFalse(_matches("rails --version"))

    def test_does_not_match_rspec_version(self) -> None:
        self.assertFalse(_matches("rspec --version"))

    def test_does_not_match_bundle_exec_rspec_version(self) -> None:
        self.assertFalse(_matches("bundle exec rspec --version"))

    def test_does_not_match_rubocop_version(self) -> None:
        self.assertFalse(_matches("rubocop --version"))

    def test_does_not_match_rake_version(self) -> None:
        self.assertFalse(_matches("rake --version"))

    def test_binstub_rails_routes_still_excluded(self) -> None:
        self.assertFalse(_matches("bin/rails routes"))


class TriggerMatcherFailOpenTests(unittest.TestCase):
    """Malformed triggers.yml must not crash the matcher (fail-open contract)."""

    def test_non_string_pattern_does_not_crash(self) -> None:
        # A malformed triggers.yml entry (nil / numeric / list-of-list)
        # used to raise TypeError out of Regexp.new, taking down the whole
        # matcher. The compile() helper must skip non-string entries and
        # keep evaluating the rest of the file.
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "triggers.yml"
            bad.write_text(
                "verify_commands:\n"
                "  direct:\n"
                "    - 42\n"  # numeric — TypeError
                "    - ~\n"   # nil — TypeError
                "    - '^rspec\\b'\n"  # valid; this MUST still match
                "rake_excluded: []\n"
            )
            proc = subprocess.run(
                [str(CLI), "--triggers", str(bad), "--cmd", "rspec spec/foo_spec.rb"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, f"matcher crashed: stderr={proc.stderr!r}")

    def test_invalid_regex_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "triggers.yml"
            bad.write_text(
                "verify_commands:\n"
                "  direct:\n"
                "    - '[unclosed'\n"  # invalid regex — RegexpError
                "    - '^rspec\\b'\n"
                "rake_excluded: []\n"
            )
            proc = subprocess.run(
                [str(CLI), "--triggers", str(bad), "--cmd", "rspec spec/foo_spec.rb"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, f"matcher crashed: stderr={proc.stderr!r}")


if __name__ == "__main__":
    unittest.main()
