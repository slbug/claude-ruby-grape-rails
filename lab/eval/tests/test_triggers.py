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
