from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
BLOCK_DANGEROUS_OPS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/block-dangerous-ops.sh"
SECRET_SCAN = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/secret-scan.sh"
DETECT_STACK = REPO_ROOT / "plugins/ruby-grape-rails/scripts/detect-stack.rb"
DETECT_RUNTIME = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime.sh"


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


def run_detect_runtime(tmpdir: str, extra_path: str | None = None) -> str:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = tmpdir
    env["RUBY_PLUGIN_DETECT_RUNTIME_QUIET"] = "1"
    if extra_path:
        env["PATH"] = f"{extra_path}{os.pathsep}{env.get('PATH', '')}"

    result = subprocess.run(
        ["bash", str(DETECT_RUNTIME)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)

    return Path(tmpdir, ".claude", ".runtime_env").read_text(encoding="utf-8")


def run_secret_scan(
    repo_root: str,
    file_path: str,
    betterleaks_path: str,
    hook_mode: str = "strict",
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"file_path": file_path}})
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = repo_root
    env["BETTERLEAKS_PATH"] = betterleaks_path
    env["RUBY_PLUGIN_HOOK_MODE"] = hook_mode
    return subprocess.run(
        ["bash", str(SECRET_SCAN)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
        env=env,
    )


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

    def test_block_dangerous_ops_blocks_common_wrapper_shell_forms(self) -> None:
        for command, expected in (
            ('bash -lc "rails db:drop"', "destructive Rails database command"),
            ('sh -lc "git push --force"', "force push detected"),
            ('bash -lc "redis-cli flushall"', "destructive Redis flush detected"),
            ('bash -lc "RAILS_ENV=production rails runner 1"', "production environment detected"),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

    def test_block_dangerous_ops_blocks_common_ruby_wrapper_forms(self) -> None:
        result = run_block_hook('ruby -e "system(\'rails db:drop\')"')
        self.assertEqual(result.returncode, 2)
        self.assertIn("destructive Rails database command", result.stderr)

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

    def test_detect_runtime_exports_dcg_and_shellfirm_when_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake_bin = tmp / "bin"
            fake_bin.mkdir()

            for name, version in (("dcg", "0.9.0"), ("shellfirm", "0.3.9")):
                script = fake_bin / name
                script.write_text(
                    textwrap.dedent(
                        f"""\
                        #!/usr/bin/env bash
                        if [[ "${{1:-}}" == "--version" ]]; then
                          echo "{name} {version}"
                          exit 0
                        fi
                        exit 0
                        """
                    ),
                    encoding="utf-8",
                )
                script.chmod(0o755)

            runtime_env = run_detect_runtime(tmpdir, extra_path=str(fake_bin))

        self.assertIn("DCG_AVAILABLE=true", runtime_env)
        self.assertIn("SHELLFIRM_AVAILABLE=true", runtime_env)
        self.assertIn("DCG_VERSION=0.9.0", runtime_env)
        self.assertIn("SHELLFIRM_VERSION=0.3.9", runtime_env)

    def test_secret_scan_treats_stdout_findings_as_secret_hits_even_on_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake = tmp / "betterleaks"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "echo 'FOUND SECRET'\n"
                "echo 'scanner warning' >&2\n"
                "exit 3\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            target = tmp / "demo.txt"
            target.write_text("token=abc\n", encoding="utf-8")

            result = run_secret_scan(tmpdir, str(target), str(fake))

        self.assertEqual(result.returncode, 2)
        self.assertIn("Potential secret detected", result.stderr)
        self.assertIn("FOUND SECRET", result.stderr)
        self.assertNotIn("Betterleaks failed while scanning", result.stderr)


if __name__ == "__main__":
    unittest.main()
