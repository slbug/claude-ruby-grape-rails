from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
BLOCK_DANGEROUS_OPS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/block-dangerous-ops.sh"
IRON_LAW_VERIFIER = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/iron-law-verifier.sh"
INJECT_IRON_LAWS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh"
SECURITY_REMINDER = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/security-reminder.sh"
SECRET_SCAN = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/secret-scan.sh"
DETECT_STACK = REPO_ROOT / "plugins/ruby-grape-rails/scripts/detect-stack.rb"
DETECT_RUNTIME = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime.sh"
DETECT_RUNTIME_FAST = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime-fast.sh"
DETECT_RUNTIME_ASYNC = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime-async.sh"
DEBUG_STATEMENT_WARNING = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/debug-statement-warning.sh"
HOOKS_JSON = REPO_ROOT / "plugins/ruby-grape-rails/hooks/hooks.json"
PRE_COMMIT_HOOK = REPO_ROOT / ".husky/pre-commit.bash"
CHECK_PENDING_PLANS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-pending-plans.sh"
CHECK_RESUME = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-resume.sh"
CHECK_SCRATCHPAD = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-scratchpad.sh"
SETUP_DIRS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/setup-dirs.sh"
ACTIVE_PLAN_LIB = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/active-plan-lib.sh"
WORKSPACE_ROOT_LIB = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/workspace-root-lib.sh"
FORMAT_RUBY = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/format-ruby.sh"
VERIFY_RUBY = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/verify-ruby.sh"
RUBYISH_POST_EDIT = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/rubyish-post-edit.sh"
STOP_FAILURE_LOG = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/stop-failure-log.sh"
ERROR_CRITIC = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/error-critic.sh"
RUBY_POST_TOOL_USE_FAILURE = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/ruby-post-tool-use-failure.sh"
PRECOMPACT_RULES = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/precompact-rules.sh"
POSTCOMPACT_VERIFY = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/postcompact-verify.sh"
CHECK_DYNAMIC_INJECTION = REPO_ROOT / "scripts/check-dynamic-injection.sh"
RUN_EVAL = REPO_ROOT / "lab/eval/run_eval.sh"
GENERATE_IRON_LAW_CONTENT = REPO_ROOT / "scripts/generate-iron-law-content.rb"
GENERATE_IRON_LAW_OUTPUTS = REPO_ROOT / "scripts/generate-iron-law-outputs.sh"


def run_block_hook(
    command: str,
    shell: str = "bash",
    extra_env: dict[str, str] | None = None,
    payload_override: str | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": command,
            },
        }
    ) if payload_override is None else payload_override
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [shell, str(BLOCK_DANGEROUS_OPS)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
        env=env,
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


def run_workspace_hook(script_path: Path, repo_root: str, payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = repo_root
    return subprocess.run(
        ["bash", str(script_path)],
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
        env=env,
    )


def run_workspace_hook_raw(script_path: Path, repo_root: str, payload: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = repo_root
    return subprocess.run(
        ["bash", str(script_path)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
        env=env,
    )


def run_active_plan_query(repo_root: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = repo_root
    command = f"source {shlex.quote(str(ACTIVE_PLAN_LIB))}; get_active_plan"
    return subprocess.run(
        ["bash", "-c", command],
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

    def test_rubyish_post_edit_delegates_are_executable(self) -> None:
        for path in (IRON_LAW_VERIFIER, FORMAT_RUBY, VERIFY_RUBY, DEBUG_STATEMENT_WARNING):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_post_tool_use_routes_ruby_hooks_through_targeted_filters(self) -> None:
        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["PostToolUse"]

        broad_group = next(group for group in groups if group.get("matcher") == "Edit|Write")
        broad_commands = {
            hook.get("command", "").rsplit("/", 1)[-1]: hook
            for hook in broad_group.get("hooks", [])
        }
        self.assertEqual(set(broad_commands), {"security-reminder.sh", "log-progress.sh", "secret-scan.sh"})
        self.assertTrue(broad_commands["log-progress.sh"].get("async", False))

        rubyish_expected = {
            "*.rb",
            "*.rake",
            "*Gemfile",
            "*Rakefile",
            "*config.ru",
        }
        for matcher in ("Edit", "Write"):
            group = next(group for group in groups if group.get("matcher") == matcher)
            rubyish_hooks = [
                hook
                for hook in group.get("hooks", [])
                if hook.get("command", "").endswith("/rubyish-post-edit.sh")
            ]
            self.assertEqual(
                {hook.get("if") for hook in rubyish_hooks},
                {f"{matcher}({pattern})" for pattern in rubyish_expected},
            )

        write_group = next(group for group in groups if group.get("matcher") == "Write")
        plan_hook = next(
            hook
            for hook in write_group.get("hooks", [])
            if hook.get("command", "").endswith("/plan-stop-reminder.sh")
        )
        self.assertEqual(plan_hook.get("if"), "Write(*plan.md)")

        direct_commands = {
            hook.get("command", "")
            for group in groups
            for hook in group.get("hooks", [])
        }
        self.assertNotIn(
            "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/iron-law-verifier.sh",
            direct_commands,
        )

    def test_post_tool_use_failure_hooks_are_filtered_to_ruby_command_families(self) -> None:
        hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["PostToolUseFailure"]
        hook_entries = [hook for group in hooks for hook in group.get("hooks", [])]
        self.assertTrue(hook_entries)
        expected_filters = {
            "Bash(bundle *)",
            "Bash(*=* bundle *)",
            "Bash(rails *)",
            "Bash(*=* rails *)",
            "Bash(bin/rails *)",
            "Bash(*=* bin/rails *)",
            "Bash(./bin/rails *)",
            "Bash(*=* ./bin/rails *)",
            "Bash(rake *)",
            "Bash(*=* rake *)",
            "Bash(bin/rake *)",
            "Bash(*=* bin/rake *)",
            "Bash(./bin/rake *)",
            "Bash(*=* ./bin/rake *)",
            "Bash(ruby *)",
            "Bash(*=* ruby *)",
            "Bash(rspec *)",
            "Bash(*=* rspec *)",
            "Bash(bin/rspec *)",
            "Bash(*=* bin/rspec *)",
            "Bash(./bin/rspec *)",
            "Bash(*=* ./bin/rspec *)",
            "Bash(standardrb *)",
            "Bash(*=* standardrb *)",
            "Bash(bin/standardrb *)",
            "Bash(*=* bin/standardrb *)",
            "Bash(./bin/standardrb *)",
            "Bash(*=* ./bin/standardrb *)",
            "Bash(rubocop *)",
            "Bash(*=* rubocop *)",
            "Bash(bin/rubocop *)",
            "Bash(*=* bin/rubocop *)",
            "Bash(./bin/rubocop *)",
            "Bash(*=* ./bin/rubocop *)",
            "Bash(brakeman *)",
            "Bash(*=* brakeman *)",
            "Bash(bin/brakeman *)",
            "Bash(*=* bin/brakeman *)",
            "Bash(./bin/brakeman *)",
            "Bash(*=* ./bin/brakeman *)",
        }
        seen_filters = {hook.get("if") for hook in hook_entries}
        self.assertEqual(seen_filters, expected_filters)
        self.assertTrue(all(hook.get("if") for hook in hook_entries))
        self.assertEqual(len(hook_entries), len(expected_filters))
        self.assertEqual(
            {hook.get("command") for hook in hook_entries},
            {"${CLAUDE_PLUGIN_ROOT}/hooks/scripts/ruby-post-tool-use-failure.sh"},
        )

    def test_ruby_post_tool_use_failure_prefers_error_critic_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "ruby-post-tool-use-failure.sh"
            wrapper.write_text(RUBY_POST_TOOL_USE_FAILURE.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)

            (tmp / "ruby-failure-hints.sh").write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s' '{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUseFailure\",\"additionalContext\":\"hint\"}}'\n",
                encoding="utf-8",
            )
            (tmp / "ruby-failure-hints.sh").chmod(0o755)

            (tmp / "error-critic.sh").write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s' '{\"hookSpecificOutput\":{\"hookEventName\":\"PostToolUseFailure\",\"additionalContext\":\"critic\"}}'\n",
                encoding="utf-8",
            )
            (tmp / "error-critic.sh").chmod(0o755)

            result = subprocess.run(
                ["bash", str(wrapper)],
                input=json.dumps({"tool_input": {"command": "bundle exec rspec"}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout,
            '{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"critic"}}',
        )

    def test_ruby_post_tool_use_failure_stops_after_first_failed_delegate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "ruby-post-tool-use-failure.sh"
            wrapper.write_text(RUBY_POST_TOOL_USE_FAILURE.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)

            (tmp / "ruby-failure-hints.sh").write_text(
                "#!/usr/bin/env bash\n"
                "echo ran > \"$(dirname \"$0\")/hints-ran\"\n"
                "exit 2\n",
                encoding="utf-8",
            )
            (tmp / "ruby-failure-hints.sh").chmod(0o755)

            (tmp / "error-critic.sh").write_text(
                "#!/usr/bin/env bash\n"
                "echo ran > \"$(dirname \"$0\")/critic-ran\"\n",
                encoding="utf-8",
            )
            (tmp / "error-critic.sh").chmod(0o755)

            result = subprocess.run(
                ["bash", str(wrapper)],
                input=json.dumps({"tool_input": {"command": "bundle exec rspec"}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=dict(os.environ),
            )

            hints_ran = (tmp / "hints-ran").is_file()
            critic_ran = (tmp / "critic-ran").exists()

        self.assertEqual(result.returncode, 2)
        self.assertTrue(hints_ran)
        self.assertFalse(critic_ran)

    def test_session_start_runtime_detection_uses_fast_sync_and_async_refresh_hooks(self) -> None:
        hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
        commands = [
            hook
            for group in hooks
            for hook in group.get("hooks", [])
            if "detect-runtime" in hook.get("command", "")
        ]
        self.assertEqual(len(commands), 2)
        fast_hook = next(hook for hook in commands if hook["command"].endswith("detect-runtime-fast.sh"))
        async_hook = next(hook for hook in commands if hook["command"].endswith("detect-runtime-async.sh"))
        self.assertFalse(fast_hook.get("async", False))
        self.assertTrue(async_hook.get("async", False))
        self.assertEqual(async_hook.get("statusMessage"), "Refreshing Ruby runtime context...")

    def test_rubyish_post_edit_fails_closed_on_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir

            result = subprocess.run(
                ["bash", str(RUBYISH_POST_EDIT)],
                input="{not-json",
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("could not safely inspect an invalid hook payload", result.stderr)

    def test_rubyish_post_edit_blocks_when_workspace_root_lib_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "rubyish-post-edit.sh"
            wrapper.write_text(RUBYISH_POST_EDIT.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)

            result = subprocess.run(
                ["bash", str(wrapper)],
                input=json.dumps({"tool_input": {"file_path": "app/demo.rb"}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("workspace-root-lib.sh is unavailable", result.stderr)

    def test_rubyish_post_edit_stops_after_first_delegated_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "rubyish-post-edit.sh"
            wrapper.write_text(RUBYISH_POST_EDIT.read_text(encoding="utf-8"), encoding="utf-8")
            wrapper.chmod(0o755)

            (tmp / "workspace-root-lib.sh").write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    read_hook_input() {
                      HOOK_INPUT_VALUE=$(cat)
                      HOOK_INPUT_STATUS=ok
                    }
                    """
                ),
                encoding="utf-8",
            )
            (tmp / "workspace-root-lib.sh").chmod(0o755)

            for name, body in (
                (
                    "iron-law-verifier.sh",
                    "#!/usr/bin/env bash\n"
                    "echo ran > \"$(dirname \"$0\")/iron-law-ran\"\n"
                    "exit 2\n",
                ),
                (
                    "format-ruby.sh",
                    "#!/usr/bin/env bash\n"
                    "echo ran > \"$(dirname \"$0\")/format-ran\"\n",
                ),
                (
                    "verify-ruby.sh",
                    "#!/usr/bin/env bash\n"
                    "echo ran > \"$(dirname \"$0\")/verify-ran\"\n",
                ),
                (
                    "debug-statement-warning.sh",
                    "#!/usr/bin/env bash\n"
                    "echo ran > \"$(dirname \"$0\")/debug-ran\"\n",
                ),
            ):
                script = tmp / name
                script.write_text(body, encoding="utf-8")
                script.chmod(0o755)

            result = subprocess.run(
                ["bash", str(wrapper)],
                input=json.dumps({"tool_input": {"file_path": "app/demo.rb"}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=dict(os.environ),
            )

            iron_law_ran = (tmp / "iron-law-ran").is_file()
            format_ran = (tmp / "format-ran").exists()
            verify_ran = (tmp / "verify-ran").exists()
            debug_ran = (tmp / "debug-ran").exists()

        self.assertEqual(result.returncode, 2)
        self.assertTrue(iron_law_ran)
        self.assertFalse(format_ran)
        self.assertFalse(verify_ran)
        self.assertFalse(debug_ran)

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

    def test_block_dangerous_ops_blocks_force_push_by_refspec(self) -> None:
        result = run_block_hook("git push origin +main")
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
        for command in (
            'ruby -e "system(\'rails db:drop\')"',
            "ruby -e 'system(%q{rails db:drop})'",
            "ruby -e 'system(%q(rails db:drop))'",
            "ruby -e 'send(:system, %q{rails db:drop})'",
            "ruby -e 'Kernel.send(:system, %q{rails db:drop})'",
            "ruby -e '`rails db:drop`'",
            'ruby -e "cmd=\'rails db:drop\'; system(cmd)"',
            'ruby -e \'system("rails db:drop", exception: true)\'',
            "ruby -e 'exec(%Q{rails db:drop})'",
            "ruby -e 'system(%Q(rails db:drop))'",
            "ruby -e '%x{rails db:drop}'",
            "ruby -e '%x(rails db:drop)'",
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn("destructive Rails database command", result.stderr)

    def test_block_dangerous_ops_blocks_array_style_wrapper_forms(self) -> None:
        for command, expected in (
            ('ruby -e "system(\'git\',\'push\',\'--force\')"', "force push detected"),
            ('ruby -e "exec(\'rails\',\'db:drop\')"', "destructive Rails database command"),
            ('ruby -e "spawn(\'redis-cli\',\'flushall\')"', "destructive Redis flush detected"),
            ('python3 -c "import subprocess; subprocess.run([\'git\', \'push\', \'--force\'])"', "force push detected"),
            ('python3 -c "import os; os.execvp(\'git\', [\'git\', \'push\', \'--force\'])"', "force push detected"),
            ("command git push --force", "force push detected"),
            ("builtin git push --force", "force push detected"),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

    def test_block_dangerous_ops_blocks_common_python_wrapper_forms(self) -> None:
        for command, expected in (
            ('python3 -c "import os; os.system(\'rails db:drop\')"', "destructive Rails database command"),
            ('python3 -c "import os; os.system(\'redis-cli flushall\')"', "destructive Redis flush detected"),
            ('python3 -c "import os; os.system(\'RAILS_ENV=production rails db:migrate\')"', "production environment detected"),
            ('python3 -c "import subprocess as s; s.run(\'rails db:drop\', shell=True)"', "destructive Rails database command"),
            ('python3 -c "from subprocess import run; run(\'rails db:drop\', shell=True)"', "destructive Rails database command"),
            ('python3 -c "import os; getattr(os, \'system\')(\'rails db:drop\')"', "destructive Rails database command"),
            ('python3 -c "import os; cmd=\'rails db:drop\'; os.system(cmd)"', "destructive Rails database command"),
            ('python3 -c "import subprocess; cmd=\'git push --force\'; subprocess.run(cmd, shell=True)"', "force push detected"),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

    def test_block_dangerous_ops_blocks_absolute_path_binaries(self) -> None:
        for command, expected in (
            ("/usr/bin/git push --force origin main", "force push detected"),
            ("/usr/bin/redis-cli flushall", "destructive Redis flush detected"),
            ("/usr/bin/rails db:drop", "destructive Rails database command"),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

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
        self.assertEqual(result.stdout, "")

    def test_block_dangerous_ops_does_not_split_quoted_operators(self) -> None:
        for command in ('echo "safe && rails db:drop"', 'printf "x|rails db:drop"'):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 0, command)

    def test_block_dangerous_ops_fails_closed_on_truncated_hook_payload(self) -> None:
        result = run_block_hook(
            "rails db:drop",
            extra_env={"RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES": "10"},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("could not safely inspect a truncated hook payload", result.stderr)

    def test_block_dangerous_ops_uses_default_limit_when_hook_byte_env_is_invalid(self) -> None:
        result = run_block_hook(
            "rails db:drop",
            extra_env={"RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES": "abc"},
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("destructive Rails database command", result.stderr)

    def test_workspace_root_lib_debug_warning_is_bash_3_2_safe(self) -> None:
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                f"source {shlex.quote(str(WORKSPACE_ROOT_LIB))}; read_hook_input",
            ],
            input="",
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
            env={
                **os.environ,
                "RUBY_PLUGIN_DEBUG_HOOKS": "1",
                "RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES": "abc",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("bad substitution", result.stderr)
        self.assertIn("invalid RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES=", result.stderr)

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

    def test_detect_stack_finds_nested_package_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text('source "https://rubygems.org"\n', encoding="utf-8")
            (tmp / "packs" / "billing" / "invoices").mkdir(parents=True)
            (tmp / "packs" / "billing" / "invoices" / "package.yml").write_text(
                "enforce_dependencies: true\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["PACKAGE_LAYOUT"], "modular_monolith")
        self.assertIn("packs/billing/invoices", values["PACKAGE_LOCATIONS"])

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

    def test_detect_runtime_fast_skips_optional_helper_version_probes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in ("rtk", "dcg", "shellfirm"):
                script = fake_bin / name
                script.write_text(
                    "#!/usr/bin/env bash\n"
                    "if [[ \"${1:-}\" == \"--version\" || \"${1:-}\" == \"gain\" ]]; then\n"
                    "  echo should-not-run >&2\n"
                    "  exit 97\n"
                    "fi\n"
                    "exit 0\n",
                    encoding="utf-8",
                )
                script.chmod(0o755)

            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            result = subprocess.run(
                ["bash", str(DETECT_RUNTIME_FAST)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

            runtime_env = (tmp / ".claude" / ".runtime_env").read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("should-not-run", result.stderr)
        self.assertIn("RTK_AVAILABLE=true", runtime_env)
        self.assertIn("DCG_AVAILABLE=true", runtime_env)
        self.assertIn("SHELLFIRM_AVAILABLE=true", runtime_env)
        self.assertNotIn("RTK_VERSION=", runtime_env)
        self.assertNotIn("DCG_VERSION=", runtime_env)
        self.assertNotIn("SHELLFIRM_VERSION=", runtime_env)

    def test_iron_law_verifier_fails_closed_when_jq_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            app_dir = tmp / "app"
            app_dir.mkdir()
            (app_dir / "demo.rb").write_text("class Demo; end\n", encoding="utf-8")
            payload = json.dumps({"tool_input": {"file_path": "app/demo.rb"}})
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = str(tmp / "bin")
            (tmp / "bin").mkdir()

            result = subprocess.run(
                ["/bin/bash", str(IRON_LAW_VERIFIER)],
                input=payload,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot inspect the hook payload because jq is unavailable", result.stderr)

    def test_security_reminder_fails_closed_when_jq_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            app_dir = tmp / "app" / "controllers"
            app_dir.mkdir(parents=True)
            (app_dir / "admin_controller.rb").write_text("class AdminController; end\n", encoding="utf-8")
            payload = json.dumps({"tool_input": {"file_path": "app/controllers/admin_controller.rb"}})
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = str(tmp / "bin")
            (tmp / "bin").mkdir()

            result = subprocess.run(
                ["/bin/bash", str(SECURITY_REMINDER)],
                input=payload,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot inspect the hook payload because jq is unavailable", result.stderr)

    def test_inject_iron_laws_no_longer_requires_jq(self) -> None:
        env = dict(os.environ)
        env["PATH"] = "/usr/bin:/bin"

        result = subprocess.run(
            ["bash", str(INJECT_IRON_LAWS)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        self.assertIn("Iron Law 1", payload["hookSpecificOutput"]["additionalContext"])

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

    def test_secret_scan_blocks_strict_recent_change_scan_when_git_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake = tmp / "betterleaks"
            fake.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_jq = shutil.which("jq")
            real_grep = shutil.which("grep")
            self.assertIsNotNone(real_jq)
            self.assertIsNotNone(real_grep)
            (fake_bin / "jq").write_text(f"#!/bin/sh\nexec {real_jq} \"$@\"\n", encoding="utf-8")
            (fake_bin / "grep").write_text(f"#!/bin/sh\nexec {real_grep} \"$@\"\n", encoding="utf-8")
            (fake_bin / "git").write_text("#!/bin/sh\nexit 127\n", encoding="utf-8")
            os.chmod(fake_bin / "jq", 0o755)
            os.chmod(fake_bin / "grep", 0o755)
            os.chmod(fake_bin / "git", 0o755)
            payload = json.dumps({"tool_input": {}})
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["BETTERLEAKS_PATH"] = str(fake)
            env["RUBY_PLUGIN_HOOK_MODE"] = "strict"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

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
        self.assertIn("could not perform strict recent-change scanning", result.stderr)

    def test_secret_scan_blocks_when_strict_recent_change_staging_fails(self) -> None:
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
            fake.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            self.assertIsNotNone(real_git)
            (fake_bin / "git").write_text(f"#!/bin/sh\nexec {real_git} \"$@\"\n", encoding="utf-8")
            (fake_bin / "cp").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            os.chmod(fake_bin / "git", 0o755)
            os.chmod(fake_bin / "cp", 0o755)

            payload = json.dumps({"tool_input": {}})
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["BETTERLEAKS_PATH"] = str(fake)
            env["RUBY_PLUGIN_HOOK_MODE"] = "strict"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

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
        self.assertIn("could not stage", result.stderr)

    def test_secret_scan_reports_tempdir_creation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            target = tmp / "secret.txt"
            target.write_text("token=abc\n", encoding="utf-8")
            fake = tmp / "betterleaks"
            fake.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)

            payload = json.dumps({"tool_input": {"file_path": str(target)}})
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["BETTERLEAKS_PATH"] = str(fake)
            env["RUBY_PLUGIN_HOOK_MODE"] = "strict"
            env["TMPDIR"] = str(tmp / "missing-tmpdir")

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
        self.assertIn("secret scan could not create a temporary workspace", result.stderr)

    def test_format_ruby_reports_tempfile_creation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            (tmp / "Gemfile").write_text('source "https://rubygems.org"\ngem "standard"\n', encoding="utf-8")
            target = tmp / "demo.rb"
            target.write_text("puts :ok\n", encoding="utf-8")
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            fake_bundle = fake_bin / "bundle"
            fake_bundle.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake_bundle.chmod(0o755)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["TMPDIR"] = str(tmp / "missing-tmpdir")
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", str(FORMAT_RUBY)],
                input=json.dumps({"tool_input": {"file_path": str(target)}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("temporary file could not be created", result.stderr)

    def test_verify_ruby_reports_tempfile_creation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            target = tmp / "demo.rb"
            target.write_text("puts :ok\n", encoding="utf-8")
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["TMPDIR"] = str(tmp / "missing-tmpdir")

            result = subprocess.run(
                ["bash", str(VERIFY_RUBY)],
                input=json.dumps({"tool_input": {"file_path": str(target)}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("temporary file could not be created", result.stderr)

    def test_detect_runtime_warns_when_runtime_env_tempfile_cannot_be_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            (fake_bin / "mktemp").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            os.chmod(fake_bin / "mktemp", 0o755)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["RUBY_PLUGIN_DETECT_RUNTIME_QUIET"] = "1"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", str(DETECT_RUNTIME)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("could not update .runtime_env", result.stderr)

    def test_detect_runtime_warns_when_runtime_state_dir_cannot_be_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").write_text("not-a-directory\n", encoding="utf-8")
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["RUBY_PLUGIN_DETECT_RUNTIME_QUIET"] = "1"

            result = subprocess.run(
                ["bash", str(DETECT_RUNTIME)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("runtime state directory could not be prepared", result.stderr)

    def test_detect_runtime_warns_when_runtime_env_final_move_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            (fake_bin / "mv").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            os.chmod(fake_bin / "mv", 0o755)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["RUBY_PLUGIN_DETECT_RUNTIME_QUIET"] = "1"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", str(DETECT_RUNTIME)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("final file move failed", result.stderr)

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

    def test_pre_commit_hook_requires_python3_for_json_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "demo.json").write_text('{"ok": true}\n', encoding="utf-8")
            subprocess.run(["git", "add", "demo.json"], cwd=tmp, check=True, capture_output=True)

            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            self.assertIsNotNone(real_git)
            (fake_bin / "git").write_text(f"#!/bin/sh\nexec {real_git} \"$@\"\n", encoding="utf-8")
            os.chmod(fake_bin / "git", 0o755)

            env = dict(os.environ)
            env["PATH"] = str(fake_bin)
            result = subprocess.run(
                ["/bin/bash", str(PRE_COMMIT_HOOK)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("python3 not found", result.stderr)

    def test_detect_runtime_ignores_lefthook_comment_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            (tmp / "lefthook.yml").write_text(
                "# rubocop only in comment\npre-commit:\n  commands:\n    noop:\n      run: echo hi\n",
                encoding="utf-8",
            )

            runtime_env = run_detect_runtime(tmpdir)

        self.assertIn("LEFTHOOK_CONFIG_PRESENT=true", runtime_env)
        self.assertIn("LEFTHOOK_LINT_COVERED=false", runtime_env)

    def test_setup_dirs_skips_mutation_on_invalid_hook_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            result = run_workspace_hook_raw(SETUP_DIRS, tmpdir, "{not-json")

            claude_dir = tmp / ".claude"
            created_dirs = [
                claude_dir / "plans",
                claude_dir / "research",
                claude_dir / "reviews",
                claude_dir / "solutions",
                claude_dir / "audit",
                claude_dir / "skill-metrics",
            ]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipping setup-dirs.sh because hook input was invalid", result.stderr)
        self.assertFalse(claude_dir.exists())
        for path in created_dirs:
            self.assertFalse(path.exists(), path)

    def test_check_resume_blocks_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook_raw(CHECK_RESUME, tmpdir, "{not-json")

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("could not safely inspect", result.stderr)

    def test_stop_failure_log_skips_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(str(plan_dir) + "\n", encoding="utf-8")
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook_raw(STOP_FAILURE_LOG, tmpdir, "{not-json")

        self.assertEqual(result.returncode, 0)
        self.assertIn("could not safely inspect", result.stderr)
        self.assertFalse((plan_dir / "scratchpad.md").exists())

    def test_active_plan_marker_respects_numbered_unchecked_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("# Demo\n\n1. [ ] first task\n", encoding="utf-8")
            active_marker = tmp / ".claude" / "ACTIVE_PLAN"
            active_marker.write_text(str(plan_dir.resolve()) + "\n", encoding="utf-8")

            result = run_active_plan_query(tmpdir)
            marker_exists = active_marker.exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), plan_dir.resolve())
        self.assertTrue(marker_exists)

    def test_active_plan_fallback_respects_bullet_unchecked_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("# Demo\n\n* [ ] first task\n", encoding="utf-8")

            result = run_active_plan_query(tmpdir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), plan_dir.resolve())

    def test_plan_hooks_count_common_markdown_checkbox_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text(
                textwrap.dedent(
                    """
                    # Demo

                    * [ ] one
                    1. [ ] two
                    - [ ] three
                    + [x] done
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            pending = run_workspace_hook(CHECK_PENDING_PLANS, tmpdir, {"stop_hook_active": False})
            resume = run_workspace_hook(CHECK_RESUME, tmpdir)

        self.assertEqual(pending.returncode, 0, pending.stderr)
        self.assertIn("1 plan(s) have uncompleted tasks", pending.stdout)
        self.assertEqual(resume.returncode, 0, resume.stderr)
        self.assertIn("has 3 remaining tasks (1 done)", resume.stdout)

    def test_check_scratchpad_auto_initializes_missing_scratchpad_for_active_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("# Demo\n\n- [ ] first task\n", encoding="utf-8")
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(str(plan_dir.resolve()) + "\n", encoding="utf-8")

            result = run_workspace_hook(CHECK_SCRATCHPAD, tmpdir)
            scratchpad = plan_dir / "scratchpad.md"
            scratchpad_exists = scratchpad.is_file()
            content = scratchpad.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(scratchpad_exists)
        self.assertIn("## Dead Ends", content)
        self.assertIn("## Decisions", content)
        self.assertIn("## Open Questions", content)
        self.assertIn("## Handoff", content)
        self.assertIn("Scratchpad notes ready in 1 plan(s):", result.stdout)

    def test_check_scratchpad_does_not_backfill_completed_historical_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plans_dir = tmp / ".claude" / "plans"

            active_dir = plans_dir / "active"
            active_dir.mkdir(parents=True)
            (active_dir / "plan.md").write_text("# Active\n\n- [ ] first task\n", encoding="utf-8")

            complete_dir = plans_dir / "complete"
            complete_dir.mkdir(parents=True)
            (complete_dir / "plan.md").write_text("# Complete\n\n- [x] done\n", encoding="utf-8")
            (complete_dir / "progress.md").write_text("done\n", encoding="utf-8")

            noted_dir = plans_dir / "noted"
            noted_dir.mkdir(parents=True)
            (noted_dir / "plan.md").write_text("# Noted\n\n- [x] done\n", encoding="utf-8")
            (noted_dir / "scratchpad.md").write_text("# Scratchpad: noted\n", encoding="utf-8")

            (tmp / ".claude" / "ACTIVE_PLAN").write_text(str(active_dir.resolve()) + "\n", encoding="utf-8")

            result = run_workspace_hook(CHECK_SCRATCHPAD, tmpdir)
            active_exists = (active_dir / "scratchpad.md").is_file()
            complete_exists = (complete_dir / "scratchpad.md").exists()
            noted_exists = (noted_dir / "scratchpad.md").is_file()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(active_exists)
        self.assertFalse(complete_exists)
        self.assertTrue(noted_exists)
        self.assertIn("Scratchpad notes ready in 2 plan(s):", result.stdout)
        self.assertIn("active (ACTIVE)", result.stdout)
        self.assertIn("noted", result.stdout)

    def test_error_critic_surfaces_repeated_failure_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = {
                "tool_input": {"command": "bundle exec rspec spec/models"},
                "error": "expected: 1\ngot: 0",
                "session_id": "abc123",
            }
            first = run_workspace_hook(ERROR_CRITIC, tmpdir, payload)
            second = run_workspace_hook(ERROR_CRITIC, tmpdir, payload)

        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, "")
        self.assertEqual(second.returncode, 0)
        self.assertIn("REPEATED FAILURE", second.stdout)

    def test_error_critic_warns_when_hook_state_storage_cannot_be_prepared(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").write_text("not-a-directory\n", encoding="utf-8")
            payload = {
                "tool_input": {"command": "bundle exec rspec spec/models"},
                "error": "expected: 1\ngot: 0",
                "session_id": "abc123",
            }
            result = run_workspace_hook(ERROR_CRITIC, tmpdir, payload)

        self.assertEqual(result.returncode, 0)
        self.assertIn("hook-state storage could not be prepared", result.stderr)

    def test_error_critic_warns_when_hook_state_update_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            (fake_bin / "mv").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            os.chmod(fake_bin / "mv", 0o755)
            payload = {
                "tool_input": {"command": "bundle exec rspec spec/models"},
                "error": "expected: 1\ngot: 0",
                "session_id": "abc123",
            }
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", str(ERROR_CRITIC)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("hook-state could not be updated", result.stderr)

    def test_precompact_rules_surfaces_active_plan_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            research_dir = plan_dir / "research"
            research_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(str(plan_dir) + "\n", encoding="utf-8")
            (research_dir / "notes.md").write_text("x\n", encoding="utf-8")

            result = run_workspace_hook(PRECOMPACT_RULES, tmpdir, {})

        self.assertEqual(result.returncode, 0)
        self.assertIn("PRESERVE ACROSS COMPACTION", result.stderr)

    def test_postcompact_verify_surfaces_active_plan_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(str(plan_dir) + "\n", encoding="utf-8")
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook(POSTCOMPACT_VERIFY, tmpdir, {})

        self.assertEqual(result.returncode, 2)
        self.assertIn("POST-COMPACTION", result.stderr)
        self.assertIn(".claude/plans/demo/plan.md", result.stderr)

    def test_check_dynamic_injection_warns_when_fallback_scan_is_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8")
            os.chmod(script_copy, 0o755)
            plugin_dir = tmp / "plugins"
            plugin_dir.mkdir()
            (plugin_dir / "doc.md").write_text("x" * 32, encoding="utf-8")
            env = dict(os.environ)
            env["RUBY_PLUGIN_DYNAMIC_INJECTION_MAX_BYTES"] = "1"

            result = subprocess.run(
                ["bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("results are partial", result.stderr)
        self.assertIn("cannot be trusted", result.stderr)

    def test_run_eval_marks_include_untracked_as_local_only(self) -> None:
        env = dict(os.environ)
        env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
        env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
        env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"
        result = subprocess.run(
            ["bash", str(RUN_EVAL), "--changed", "--include-untracked"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("local-only and non-comparable", result.stdout)

    def test_run_eval_warns_when_include_untracked_is_ignored_outside_changed(self) -> None:
        env = dict(os.environ)
        env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
        env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
        env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"
        result = subprocess.run(
            ["bash", str(RUN_EVAL), "--ci", "--include-untracked"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("will be ignored for --ci", result.stdout)

    def test_run_eval_requires_valid_against_ref(self) -> None:
        env = dict(os.environ)
        env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
        env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
        env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"
        result = subprocess.run(
            ["bash", str(RUN_EVAL), "--changed", "--against", "refs/does-not-exist"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("could not resolve merge-base", result.stderr)

    def test_run_eval_rejects_invalid_threshold_envs(self) -> None:
        for env_name, mode in (
            ("RUBY_PLUGIN_EVAL_FAIL_UNDER", "--skills"),
            ("RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER", "--agents"),
            ("RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER", "--triggers"),
        ):
            env = dict(os.environ)
            env[env_name] = "not-a-number"
            result = subprocess.run(
                ["bash", str(RUN_EVAL), mode],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 1, env_name)
            self.assertIn(f"{env_name} must be a finite numeric threshold", result.stderr)

    def test_run_eval_reports_tempfile_creation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            (fake_bin / "mktemp").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            os.chmod(fake_bin / "mktemp", 0o755)
            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"

            result = subprocess.run(
                ["bash", str(RUN_EVAL), "--skills"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("could not create a temporary score payload file", result.stderr)

    def test_generate_iron_law_content_rejects_mismatched_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            yaml_path = tmp / "iron-laws.yml"
            yaml_path.write_text(
                textwrap.dedent(
                    """
                    version: "1"
                    last_updated: "2026-04-01"
                    total_laws: 2
                    categories:
                      - id: data
                        name: Data
                        law_count: 2
                    laws:
                      - id: 1
                        category: data
                        title: One
                        rule: Do it
                        summary_text: One
                        rationale: Why
                        subagent_text: One
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["RUBY_PLUGIN_IRON_LAWS_YAML"] = str(yaml_path)
            result = subprocess.run(
                ["ruby", str(GENERATE_IRON_LAW_CONTENT), "readme"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match", result.stderr)

    def test_generate_iron_law_outputs_help_succeeds(self) -> None:
        result = subprocess.run(
            ["bash", str(GENERATE_IRON_LAW_OUTPUTS), "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Regenerate Iron Law projections", result.stdout)
        self.assertNotIn("claude", result.stdout)


if __name__ == "__main__":
    unittest.main()
