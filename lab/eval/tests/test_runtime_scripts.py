from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
BLOCK_DANGEROUS_OPS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/block-dangerous-ops.sh"
DETECT_STACK = REPO_ROOT / "plugins/ruby-grape-rails/scripts/detect-stack.rb"


def run_block_hook(command: str, shell: str = "bash") -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": command,
            },
        }
    )
    return subprocess.run(
        [shell, str(BLOCK_DANGEROUS_OPS)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


def run_detect_stack(tmpdir: str) -> dict[str, str]:
    result = subprocess.run(
        ["ruby", str(DETECT_STACK)],
        cwd=tmpdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)

    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


class RuntimeScriptTests(unittest.TestCase):
    def test_block_dangerous_ops_blocks_quoted_and_namespaced_db_tasks(self) -> None:
        for command in (
            'bundle exec rails "db:drop"',
            "rake 'db:reset'",
            "bundle exec rails db:drop:all",
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn("destructive Rails database command", result.stderr)

    def test_block_dangerous_ops_blocks_force_push_with_git_config_prefix(self) -> None:
        result = run_block_hook("git -c push.default=current push --force origin main")
        self.assertEqual(result.returncode, 2)
        self.assertIn("force push detected", result.stderr)

    def test_block_dangerous_ops_does_not_treat_echo_as_production_command(self) -> None:
        result = run_block_hook('echo "RAILS_ENV=production"')
        self.assertEqual(result.returncode, 0)

    def test_block_dangerous_ops_is_bash_3_2_safe_for_redis_flush(self) -> None:
        result = run_block_hook("redis-cli FLUSHALL", shell="/bin/bash")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("bad substitution", result.stderr)
        self.assertIn("destructive Redis flush detected", result.stderr)

    def test_detect_stack_supports_function_call_gem_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                textwrap.dedent(
                    """
                    source "https://rubygems.org"
                    gem("rails")
                    gem("sidekiq")
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (tmp / "Gemfile.lock").write_text(
                textwrap.dedent(
                    """
                    GEM
                      specs:
                        rails (8.1.0)
                        sidekiq (7.3.0)
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["RAILS_VERSION"], "8.1.0")
        self.assertIn("rails", values["DETECTED_STACK"])
        self.assertIn("sidekiq", values["DETECTED_STACK"])

    def test_detect_stack_supports_gemspec_driven_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\n\ngemspec\n',
                encoding="utf-8",
            )
            (tmp / "demo.gemspec").write_text(
                textwrap.dedent(
                    """
                    Gem::Specification.new do |spec|
                      spec.name = "demo"
                      spec.version = "0.1.0"
                      spec.add_dependency "rails", "~> 8.1"
                      spec.add_dependency "grape"
                    end
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            (tmp / "Gemfile.lock").write_text(
                textwrap.dedent(
                    """
                    GEM
                      specs:
                        grape (2.4.0)
                        rails (8.1.0)
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["RAILS_VERSION"], "8.1.0")
        self.assertIn("rails", values["DETECTED_STACK"])
        self.assertIn("grape", values["DETECTED_STACK"])


if __name__ == "__main__":
    unittest.main()
