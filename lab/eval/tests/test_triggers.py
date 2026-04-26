"""Contributor tests for trigger-matcher CLI (Ruby runtime)."""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "plugins" / "ruby-grape-rails" / "bin" / "match-trigger"
TRIGGERS = REPO / "plugins" / "ruby-grape-rails" / "references" / "compression" / "triggers.yml"


def _matches(cmd: str) -> bool:
    proc = subprocess.run(
        [str(CLI), "--triggers", str(TRIGGERS), "--cmd", cmd],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def test_matches_rspec() -> None:
    assert _matches("rspec spec/models/user_spec.rb")


def test_matches_bundle_exec_brakeman() -> None:
    assert _matches("bundle exec brakeman")


def test_matches_rails_db_migrate() -> None:
    assert _matches("bundle exec rails db:migrate")


def test_does_not_match_rake_routes() -> None:
    assert not _matches("bundle exec rake routes")


def test_rake_excluded_wins_over_trigger() -> None:
    # rake db:drop must NEVER trigger compression even if rake_verify_only had overlap
    assert not _matches("bundle exec rake db:drop")


def test_unrelated_command() -> None:
    assert not _matches("ls -la")


def test_matches_env_prefix_rspec() -> None:
    assert _matches("RAILS_ENV=test rspec spec/models/user_spec.rb")


def test_matches_multi_env_prefix_bundle_exec() -> None:
    assert _matches("RAILS_ENV=test BUNDLE_GEMFILE=Gemfile bundle exec rspec")


def test_matches_env_prefix_rails_db_migrate() -> None:
    assert _matches("RAILS_ENV=production bundle exec rails db:migrate")


def test_env_prefix_does_not_bypass_rake_excluded() -> None:
    assert not _matches("RAILS_ENV=test bundle exec rake db:drop")


def test_does_not_match_rtk_rspec() -> None:
    # rtk's PreToolUse rewrite produces `rtk rspec` — must NOT compress.
    assert not _matches("rtk rspec spec/foo_spec.rb")


def test_non_string_pattern_does_not_crash(tmp_path: Path) -> None:
    # A malformed triggers.yml entry (nil / numeric / list-of-list)
    # used to raise TypeError out of Regexp.new, taking down the whole
    # matcher. The compile() helper must skip non-string entries and
    # keep evaluating the rest of the file.
    bad = tmp_path / "triggers.yml"
    bad.write_text(
        "verify_commands:\n"
        "  direct:\n"
        "    - 42\n"  # numeric — TypeError
        "    - ~\n"   # nil — TypeError
        "    - '^rspec\\b'\n"  # valid; this MUST still match
        "rake_excluded: []\n"
    )
    # match-trigger should treat the bad entries as non-matching and
    # then succeed on the valid `^rspec\b` pattern.
    proc = subprocess.run(
        [str(CLI), "--triggers", str(bad), "--cmd", "rspec spec/foo_spec.rb"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"matcher crashed: stderr={proc.stderr!r}"


def test_invalid_regex_does_not_crash(tmp_path: Path) -> None:
    bad = tmp_path / "triggers.yml"
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
    assert proc.returncode == 0, f"matcher crashed: stderr={proc.stderr!r}"
