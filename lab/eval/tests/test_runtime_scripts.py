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
DEBUG_STATEMENT_WARNING = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/debug-statement-warning.sh"
HOOKS_JSON = REPO_ROOT / "plugins/ruby-grape-rails/hooks/hooks.json"
PRE_COMMIT_HOOK = REPO_ROOT / ".husky/pre-commit.bash"


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


def run_debug_statement_warning(repo_root: str, file_path: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"file_path": file_path}})
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = repo_root
    return subprocess.run(
        ["bash", str(DEBUG_STATEMENT_WARNING)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
        env=env,
    )


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
    def test_hook_command_targets_are_executable(self) -> None:
        hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]
        command_paths: set[Path] = set()

        for groups in hooks.values():
            for group in groups:
                for hook in group.get("hooks", []):
                    command = hook.get("command", "")
                    prefix = "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
                    if command.startswith(prefix):
                        relative = command[len("${CLAUDE_PLUGIN_ROOT}/") :]
                        command_paths.add(REPO_ROOT / "plugins/ruby-grape-rails" / relative)

        for path in sorted(command_paths):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(os.access(path, os.X_OK), path)

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

    def test_block_dangerous_ops_blocks_production_env_assignments_beyond_prefixes(self) -> None:
        for command in (
            "rails db:migrate RAILS_ENV=production",
            "export RAILS_ENV=production; rails db:migrate",
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn("production environment detected", result.stderr)

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

    def test_detect_stack_ignores_transitive_lockfile_specs_for_gemspec_repo(self) -> None:
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
                      spec.add_dependency "rack"
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
                        rack (3.0.0)
                        rails (8.1.0)

                    DEPENDENCIES
                      demo!

                    BUNDLED WITH
                       2.5.0
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertEqual(values.get("DETECTED_STACK", ""), "")
        self.assertNotIn("RAILS_VERSION", values)

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

    def test_secret_scan_strict_mode_includes_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
            (tmp / "tracked.txt").write_text("ok\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=tmp, check=True)
            subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "untracked.txt").write_text("token=abc\n", encoding="utf-8")

            fake = tmp / "betterleaks"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "echo 'FOUND SECRET'\n"
                "exit 0\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)

            payload = json.dumps({"tool_input": {}})
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["BETTERLEAKS_PATH"] = str(fake)
            env["RUBY_PLUGIN_HOOK_MODE"] = "strict"

            result = subprocess.run(
                ["bash", str(SECRET_SCAN)],
                input=payload,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Potential secret detected", result.stderr)

    def test_debug_statement_warning_detects_standalone_p_and_inline_puts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            app_dir = tmp / "app"
            app_dir.mkdir()
            file_path = app_dir / "demo.rb"

            file_path.write_text("p user\n", encoding="utf-8")
            result = run_debug_statement_warning(tmpdir, "app/demo.rb")
            self.assertEqual(result.returncode, 2)
            self.assertIn("DEBUG STATEMENTS", result.stderr)

            file_path.write_text('foo && puts("debug")\n', encoding="utf-8")
            result = run_debug_statement_warning(tmpdir, "app/demo.rb")
            self.assertEqual(result.returncode, 2)
            self.assertIn("DEBUG STATEMENTS", result.stderr)

    def test_pre_commit_hook_runs_without_mapfile_on_bash_3_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)

            result = subprocess.run(
                ["/bin/bash", str(PRE_COMMIT_HOOK)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("mapfile", result.stderr)


if __name__ == "__main__":
    unittest.main()
