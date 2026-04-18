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
BLOCK_DANGEROUS_OPS = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/block-dangerous-ops.sh"
)
IRON_LAW_VERIFIER = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/iron-law-verifier.sh"
)
INJECT_IRON_LAWS = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh"
)
SECURITY_REMINDER = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/security-reminder.sh"
)
SECRET_SCAN = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/secret-scan.sh"
DETECT_STACK = REPO_ROOT / "plugins/ruby-grape-rails/bin/detect-stack"
DETECT_RUNTIME = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime.sh"
DETECT_RUNTIME_FAST = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime-fast.sh"
)
DETECT_RUNTIME_ASYNC = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/detect-runtime-async.sh"
)
DEBUG_STATEMENT_WARNING = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/debug-statement-warning.sh"
)
HOOKS_JSON = REPO_ROOT / "plugins/ruby-grape-rails/hooks/hooks.json"
PRE_COMMIT_HOOK = REPO_ROOT / ".husky/pre-commit.bash"
CHECK_PENDING_PLANS = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-pending-plans.sh"
)
CHECK_RESUME = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-resume.sh"
CHECK_PLUGIN_VERSION = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-plugin-version.sh"
)
PLUGIN_ROOT = REPO_ROOT / "plugins/ruby-grape-rails"
CHECK_SCRATCHPAD = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/check-scratchpad.sh"
)
SETUP_DIRS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/setup-dirs.sh"
ACTIVE_PLAN_LIB = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/active-plan-lib.sh"
)
WORKSPACE_ROOT_LIB = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/workspace-root-lib.sh"
)
FORMAT_RUBY = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/format-ruby.sh"
VERIFY_RUBY = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/verify-ruby.sh"
RUBYISH_POST_EDIT = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/rubyish-post-edit.sh"
)
PLAN_STOP_REMINDER = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/plan-stop-reminder.sh"
)
LOG_PROGRESS = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/log-progress.sh"
STOP_FAILURE_LOG = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/stop-failure-log.sh"
)
ERROR_CRITIC = REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/error-critic.sh"
RUBY_FAILURE_HINTS = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/ruby-failure-hints.sh"
)
RUBY_POST_TOOL_USE_FAILURE = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/ruby-post-tool-use-failure.sh"
)
PRECOMPACT_RULES = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/precompact-rules.sh"
)
POSTCOMPACT_VERIFY = (
    REPO_ROOT / "plugins/ruby-grape-rails/hooks/scripts/postcompact-verify.sh"
)
CHECK_DYNAMIC_INJECTION = REPO_ROOT / "scripts/check-dynamic-injection.sh"
FETCH_CLAUDE_DOCS = REPO_ROOT / "scripts/fetch-claude-docs.sh"
RUN_EVAL = REPO_ROOT / "lab/eval/run_eval.sh"
GENERATE_IRON_LAW_CONTENT = REPO_ROOT / "scripts/generate-iron-law-content.rb"
GENERATE_IRON_LAW_OUTPUTS = REPO_ROOT / "scripts/generate-iron-law-outputs.sh"
RUN_EVAL_TESTS = REPO_ROOT / "scripts/run-eval-tests.sh"
VALIDATE_PLUGIN = REPO_ROOT / "scripts/validate-plugin.sh"


def run_block_hook(
    command: str,
    shell: str = "bash",
    extra_env: dict[str, str] | None = None,
    payload_override: str | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = (
        json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": command,
                },
            }
        )
        if payload_override is None
        else payload_override
    )
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


def run_detect_stack(tmpdir: str, cwd: str | None = None) -> dict[str, str]:
    result = subprocess.run(
        ["ruby", str(DETECT_STACK)],
        cwd=cwd or tmpdir,
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


def run_debug_statement_warning(
    repo_root: str, file_path: str
) -> subprocess.CompletedProcess[str]:
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


def run_workspace_hook(
    script_path: Path, repo_root: str, payload: dict | None = None
) -> subprocess.CompletedProcess[str]:
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


def run_workspace_hook_raw(
    script_path: Path, repo_root: str, payload: str
) -> subprocess.CompletedProcess[str]:
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
                        command_paths.add(
                            REPO_ROOT / "plugins/ruby-grape-rails" / relative
                        )

        for path in sorted(command_paths):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_rubyish_post_edit_delegates_are_executable(self) -> None:
        for path in (
            IRON_LAW_VERIFIER,
            FORMAT_RUBY,
            VERIFY_RUBY,
            DEBUG_STATEMENT_WARNING,
        ):
            self.assertTrue(path.is_file(), path)
            self.assertTrue(os.access(path, os.X_OK), path)

    def test_post_tool_use_routes_ruby_hooks_through_targeted_filters(self) -> None:
        groups = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"][
            "PostToolUse"
        ]

        broad_group = next(
            group for group in groups if group.get("matcher") == "Edit|Write"
        )
        broad_commands = {
            hook.get("command", "").rsplit("/", 1)[-1]: hook
            for hook in broad_group.get("hooks", [])
        }
        self.assertEqual(
            set(broad_commands),
            {"log-progress.sh", "secret-scan.sh"},
        )
        self.assertTrue(broad_commands["log-progress.sh"].get("async", False))

        # security-reminder.sh is narrowed to code/config files via
        # separate Edit and Write groups with per-pattern if filters
        security_expected = {
            "*.rb", "*.rake", "*Gemfile", "*Rakefile",
            "config/**", "*.yml", "*.env*", "*.json",
        }
        for matcher in ("Edit", "Write"):
            security_group = next(
                group for group in groups
                if group.get("matcher") == matcher
                and any(
                    hook.get("command", "").endswith("/security-reminder.sh")
                    for hook in group.get("hooks", [])
                )
            )
            security_hooks = [
                hook for hook in security_group.get("hooks", [])
                if hook.get("command", "").endswith("/security-reminder.sh")
            ]
            self.assertEqual(
                {hook.get("if") for hook in security_hooks},
                {f"{matcher}({pattern})" for pattern in security_expected},
            )

        rubyish_expected = {
            "*.rb",
            "*.rake",
            "*Gemfile",
            "*Rakefile",
            "*config.ru",
        }
        for matcher in ("Edit", "Write"):
            rubyish_group = next(
                group for group in groups
                if group.get("matcher") == matcher
                and any(
                    hook.get("command", "").endswith("/rubyish-post-edit.sh")
                    for hook in group.get("hooks", [])
                )
            )
            rubyish_hooks = [
                hook
                for hook in rubyish_group.get("hooks", [])
                if hook.get("command", "").endswith("/rubyish-post-edit.sh")
            ]
            self.assertEqual(
                {hook.get("if") for hook in rubyish_hooks},
                {f"{matcher}({pattern})" for pattern in rubyish_expected},
            )

        plan_hook_found = False
        for group in groups:
            if group.get("matcher") != "Write":
                continue
            for hook in group.get("hooks", []):
                if hook.get("command", "").endswith("/plan-stop-reminder.sh"):
                    self.assertEqual(hook.get("if"), "Write(*plan.md)")
                    plan_hook_found = True
        self.assertTrue(plan_hook_found, "plan-stop-reminder.sh not found")

        direct_commands = {
            hook.get("command", "")
            for group in groups
            for hook in group.get("hooks", [])
        }
        self.assertNotIn(
            "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/iron-law-verifier.sh",
            direct_commands,
        )

    def test_post_tool_use_failure_hooks_are_filtered_to_ruby_command_families(
        self,
    ) -> None:
        hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"][
            "PostToolUseFailure"
        ]
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
            wrapper.write_text(
                RUBY_POST_TOOL_USE_FAILURE.read_text(encoding="utf-8"), encoding="utf-8"
            )
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

            (tmp / "ruby-failure-hints.sh").write_text(
                "#!/usr/bin/env bash\n"
                'printf \'%s\' \'{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"hint"}}\'\n',
                encoding="utf-8",
            )
            (tmp / "ruby-failure-hints.sh").chmod(0o755)

            (tmp / "error-critic.sh").write_text(
                "#!/usr/bin/env bash\n"
                'printf \'%s\' \'{"hookSpecificOutput":{"hookEventName":"PostToolUseFailure","additionalContext":"critic"}}\'\n',
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
            wrapper.write_text(
                RUBY_POST_TOOL_USE_FAILURE.read_text(encoding="utf-8"), encoding="utf-8"
            )
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

            (tmp / "ruby-failure-hints.sh").write_text(
                '#!/usr/bin/env bash\necho ran > "$(dirname "$0")/hints-ran"\nexit 2\n',
                encoding="utf-8",
            )
            (tmp / "ruby-failure-hints.sh").chmod(0o755)

            (tmp / "error-critic.sh").write_text(
                '#!/usr/bin/env bash\necho ran > "$(dirname "$0")/critic-ran"\n',
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

    def test_ruby_post_tool_use_failure_blocks_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "ruby-post-tool-use-failure.sh"
            wrapper.write_text(
                RUBY_POST_TOOL_USE_FAILURE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            wrapper.chmod(0o755)

            (tmp / "workspace-root-lib.sh").write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    read_hook_input() {
                      HOOK_INPUT_VALUE=""
                      HOOK_INPUT_STATUS=invalid
                    }
                    """
                ),
                encoding="utf-8",
            )
            (tmp / "workspace-root-lib.sh").chmod(0o755)

            (tmp / "ruby-failure-hints.sh").write_text(
                '#!/usr/bin/env bash\necho ran > "$(dirname "$0")/hints-ran"\n',
                encoding="utf-8",
            )
            (tmp / "ruby-failure-hints.sh").chmod(0o755)

            (tmp / "error-critic.sh").write_text(
                '#!/usr/bin/env bash\necho ran > "$(dirname "$0")/critic-ran"\n',
                encoding="utf-8",
            )
            (tmp / "error-critic.sh").chmod(0o755)

            result = subprocess.run(
                ["bash", str(wrapper)],
                input="{not-json",
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=dict(os.environ),
            )

            hints_ran = (tmp / "hints-ran").exists()
            critic_ran = (tmp / "critic-ran").exists()

        self.assertEqual(result.returncode, 2)
        self.assertIn("could not safely inspect an invalid hook payload", result.stderr)
        self.assertFalse(hints_ran)
        self.assertFalse(critic_ran)

    def test_session_start_runtime_detection_uses_fast_sync_and_async_refresh_hooks(
        self,
    ) -> None:
        hooks = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"][
            "SessionStart"
        ]
        commands = [
            hook
            for group in hooks
            for hook in group.get("hooks", [])
            if "detect-runtime" in hook.get("command", "")
        ]
        self.assertEqual(len(commands), 2)
        fast_hook = next(
            hook
            for hook in commands
            if hook["command"].endswith("detect-runtime-fast.sh")
        )
        async_hook = next(
            hook
            for hook in commands
            if hook["command"].endswith("detect-runtime-async.sh")
        )
        self.assertFalse(fast_hook.get("async", False))
        self.assertTrue(async_hook.get("async", False))
        self.assertEqual(
            async_hook.get("statusMessage"), "Refreshing Ruby runtime context..."
        )

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
            wrapper.write_text(
                RUBYISH_POST_EDIT.read_text(encoding="utf-8"), encoding="utf-8"
            )
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

    def test_rubyish_post_edit_aggregates_delegate_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "rubyish-post-edit.sh"
            wrapper.write_text(
                RUBYISH_POST_EDIT.read_text(encoding="utf-8"), encoding="utf-8"
            )
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
                    'echo ran > "$(dirname "$0")/iron-law-ran"\n'
                    "exit 2\n",
                ),
                (
                    "format-ruby.sh",
                    "#!/usr/bin/env bash\n"
                    'echo ran > "$(dirname "$0")/format-ran"\n'
                    "exit 2\n",
                ),
                (
                    "verify-ruby.sh",
                    '#!/usr/bin/env bash\necho ran > "$(dirname "$0")/verify-ran"\n',
                ),
                (
                    "debug-statement-warning.sh",
                    '#!/usr/bin/env bash\necho ran > "$(dirname "$0")/debug-ran"\n',
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
        self.assertTrue(format_ran)
        self.assertTrue(verify_ran)
        self.assertTrue(debug_ran)
        self.assertIn("delegated post-edit failures", result.stderr)

    def test_rubyish_post_edit_blocks_when_delegate_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper = tmp / "rubyish-post-edit.sh"
            wrapper.write_text(
                RUBYISH_POST_EDIT.read_text(encoding="utf-8"), encoding="utf-8"
            )
            wrapper.chmod(0o755)

            (tmp / "workspace-root-lib.sh").write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    path_basename() {
                      local path="$1"
                      printf '%s\\n' "${path##*/}"
                    }
                    read_hook_input() {
                      HOOK_INPUT_VALUE=$(cat)
                      HOOK_INPUT_STATUS=valid
                    }
                    """
                ),
                encoding="utf-8",
            )
            (tmp / "workspace-root-lib.sh").chmod(0o755)

            for name in ("format-ruby.sh", "debug-statement-warning.sh"):
                script = tmp / name
                script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
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

        self.assertEqual(result.returncode, 2)
        self.assertIn("iron-law-verifier.sh is unavailable", result.stderr)

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
            (
                'bash -lc "RAILS_ENV=production rails runner 1"',
                "production environment detected",
            ),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

    def test_block_dangerous_ops_blocks_common_ruby_wrapper_forms(self) -> None:
        for command in (
            "ruby -e \"system('rails db:drop')\"",
            "ruby -e 'system(%q{rails db:drop})'",
            "ruby -e 'system(%q(rails db:drop))'",
            "ruby -e 'send(:system, %q{rails db:drop})'",
            "ruby -e 'Kernel.send(:system, %q{rails db:drop})'",
            "ruby -e '`rails db:drop`'",
            "ruby -e \"cmd='rails db:drop'; system(cmd)\"",
            "ruby -e 'system(\"rails db:drop\", exception: true)'",
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
            ("ruby -e \"system('git','push','--force')\"", "force push detected"),
            (
                "ruby -e \"exec('rails','db:drop')\"",
                "destructive Rails database command",
            ),
            (
                "ruby -e \"spawn('redis-cli','flushall')\"",
                "destructive Redis flush detected",
            ),
            (
                "python3 -c \"import subprocess; subprocess.run(['git', 'push', '--force'])\"",
                "force push detected",
            ),
            (
                "python3 -c \"import os; os.execvp('git', ['git', 'push', '--force'])\"",
                "force push detected",
            ),
            ("command git push --force", "force push detected"),
            ("builtin git push --force", "force push detected"),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

    def test_block_dangerous_ops_blocks_common_python_wrapper_forms(self) -> None:
        for command, expected in (
            (
                "python3 -c \"import os; os.system('rails db:drop')\"",
                "destructive Rails database command",
            ),
            (
                "python3 -c \"import os; os.system('redis-cli flushall')\"",
                "destructive Redis flush detected",
            ),
            (
                "python3 -c \"import os; os.system('RAILS_ENV=production rails db:migrate')\"",
                "production environment detected",
            ),
            (
                "python3 -c \"import subprocess as s; s.run('rails db:drop', shell=True)\"",
                "destructive Rails database command",
            ),
            (
                "python3 -c \"from subprocess import run; run('rails db:drop', shell=True)\"",
                "destructive Rails database command",
            ),
            (
                "python3 -c \"import os; getattr(os, 'system')('rails db:drop')\"",
                "destructive Rails database command",
            ),
            (
                "python3 -c \"import os; cmd='rails db:drop'; os.system(cmd)\"",
                "destructive Rails database command",
            ),
            (
                "python3 -c \"import subprocess; cmd='git push --force'; subprocess.run(cmd, shell=True)\"",
                "force push detected",
            ),
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

    def test_block_dangerous_ops_blocks_production_env_assignments_beyond_prefixes(
        self,
    ) -> None:
        for command in (
            "rails db:migrate RAILS_ENV=production",
            "export RAILS_ENV=production; rails db:migrate",
            "RAILS_ENV=$(printf 'production') rails db:migrate",
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn("production environment detected", result.stderr)

    def test_block_dangerous_ops_uses_shfmt_to_allow_harmless_probe_with_cmdsub_prefix(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_shfmt = tmp / "shfmt"
            fake_shfmt.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    cat >/dev/null
                    cat <<'JSON'
                    {
                      "Type": "File",
                      "Stmts": [
                        {
                          "Pos": {"Offset": 0},
                          "End": {"Offset": 38},
                          "Cmd": {
                            "Type": "CallExpr",
                            "Pos": {"Offset": 0},
                            "End": {"Offset": 38},
                            "Assigns": [
                              {
                                "Name": {"Value": "RAILS_ENV"},
                                "Value": {
                                  "Parts": [
                                    {
                                      "Type": "CmdSubst",
                                      "Stmts": [
                                        {
                                          "Cmd": {
                                            "Type": "CallExpr",
                                            "Args": [
                                              {"Parts": [{"Type": "Lit", "Value": "printf"}]},
                                              {"Parts": [{"Type": "Lit", "Value": "production"}]}
                                            ]
                                          }
                                        }
                                      ]
                                    }
                                  ]
                                }
                              }
                            ],
                            "Args": [
                              {"Pos": {"Offset": 31}, "Parts": [{"Type": "Lit", "Value": "echo"}]},
                              {"Pos": {"Offset": 36}, "Parts": [{"Type": "Lit", "Value": "ok"}]}
                            ]
                          }
                        }
                      ]
                    }
                    JSON
                    """
                ),
                encoding="utf-8",
            )
            fake_shfmt.chmod(0o755)

            result = run_block_hook(
                "RAILS_ENV=$(printf production) echo ok",
                extra_env={"PATH": f"{tmpdir}{os.pathsep}{os.environ.get('PATH', '')}"},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_block_dangerous_ops_blocks_single_background_operator_variants(
        self,
    ) -> None:
        for command, expected in (
            ("echo ok & git push --force origin main", "force push detected"),
            ("echo ok & rails db:drop", "destructive Rails database command"),
            (
                "export RAILS_ENV=production & bundle exec rails db:migrate",
                "production environment detected",
            ),
        ):
            result = run_block_hook(command)
            self.assertEqual(result.returncode, 2, command)
            self.assertIn(expected, result.stderr)

    def test_block_dangerous_ops_blocks_ruby_script_file_wrapper(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmpdir:
            tmp = Path(tmpdir)
            script = tmp / "drop.rb"
            script.write_text('system("rails db:drop")\n', encoding="utf-8")

            result = run_block_hook(f"ruby {script}")

        self.assertEqual(result.returncode, 2)
        self.assertIn("destructive Rails database command", result.stderr)

    def test_block_dangerous_ops_blocks_python_script_file_wrapper(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmpdir:
            tmp = Path(tmpdir)
            script = tmp / "drop.py"
            script.write_text(
                'import os\nos.system("rails db:drop")\n', encoding="utf-8"
            )

            result = run_block_hook(f"python3 {script}")

        self.assertEqual(result.returncode, 2)
        self.assertIn("destructive Rails database command", result.stderr)

    def test_block_dangerous_ops_does_not_inspect_wrapper_sources_outside_repo_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script = tmp / "drop.rb"
            script.write_text('system("rails db:drop")\n', encoding="utf-8")

            result = run_block_hook(f"ruby {script}")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_block_dangerous_ops_does_not_treat_echo_as_production_command(
        self,
    ) -> None:
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
        self.assertIn(
            "could not safely inspect a truncated hook payload", result.stderr
        )

    def test_block_dangerous_ops_blocks_when_command_field_is_missing(self) -> None:
        result = run_block_hook(
            "rails db:drop",
            payload_override=json.dumps({"tool_name": "Bash", "tool_input": {}}),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("tool_input.command was missing", result.stderr)

    def test_block_dangerous_ops_uses_default_limit_when_hook_byte_env_is_invalid(
        self,
    ) -> None:
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

    def test_detect_stack_finds_repo_root_from_nested_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\n\ngem "rails"\n',
                encoding="utf-8",
            )
            (tmp / "Gemfile.lock").write_text(
                textwrap.dedent(
                    """
                    GEM
                      specs:
                        rails (8.1.0)
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            nested = tmp / "app" / "models"
            nested.mkdir(parents=True)

            values = run_detect_stack(tmpdir, cwd=str(nested))

        self.assertEqual(values["RAILS_VERSION"], "8.1.0")
        self.assertIn("rails", values["DETECTED_STACK"])

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

    def test_detect_stack_supports_gemspec_only_repos(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "demo.gemspec").write_text(
                textwrap.dedent(
                    """
                    Gem::Specification.new do |spec|
                      spec.name = "demo"
                      spec.version = "0.1.0"
                      spec.add_dependency "rails", "~> 8.1"
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
                        rails (8.1.0)
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["RAILS_VERSION"], "8.1.0")
        self.assertIn("rails", values["DETECTED_STACK"])

    def test_detect_stack_treats_split_hotwire_gems_as_hotwire(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                textwrap.dedent(
                    """
                    source "https://rubygems.org"

                    gem "turbo-rails"
                    gem "stimulus-rails"
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
                        stimulus-rails (1.3.0)
                        turbo-rails (2.0.5)

                    DEPENDENCIES
                      stimulus-rails
                      turbo-rails
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertIn("hotwire", values["DETECTED_STACK"])
        self.assertEqual(values["HAS_HOTWIRE"], "true")

    def test_detect_stack_ignores_transitive_lockfile_specs_for_gemspec_repo(
        self,
    ) -> None:
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

    def test_detect_stack_ignores_symlinked_manifests(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as extdir,
        ):
            tmp = Path(tmpdir)
            external = Path(extdir) / "Gemfile"
            external.write_text(
                'source "https://rubygems.org"\n\ngem "grape"\n',
                encoding="utf-8",
            )
            os.symlink(external, tmp / "Gemfile")

            values = run_detect_stack(tmpdir)

        self.assertEqual(values, {})

    def test_detect_stack_ignores_symlinked_packwerk_marker(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.TemporaryDirectory() as extdir,
        ):
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\n', encoding="utf-8"
            )
            external = Path(extdir) / "packwerk.yml"
            external.write_text("enforce_dependencies: true\n", encoding="utf-8")
            os.symlink(external, tmp / "packwerk.yml")

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["PACKAGE_LAYOUT"], "single_app")
        self.assertEqual(values["HAS_PACKWERK"], "false")

    def test_detect_stack_ignores_unreadable_gemfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            gemfile = tmp / "Gemfile"
            gemfile.write_text(
                'source "https://rubygems.org"\n\ngem "rails"\n', encoding="utf-8"
            )
            gemfile.chmod(0)

            values = run_detect_stack(tmpdir)

        self.assertEqual(values.get("DETECTED_STACK", ""), "")

    def test_detect_stack_reports_project_ruby_version_from_ruby_version_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\n', encoding="utf-8"
            )
            (tmp / ".ruby-version").write_text("3.4.1\n", encoding="utf-8")

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["RUBY_VERSION"], "3.4.1")
        self.assertIn("INTERPRETER_RUBY_VERSION", values)

    def test_detect_stack_finds_nested_package_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\n', encoding="utf-8"
            )
            (tmp / "packs" / "billing" / "invoices").mkdir(parents=True)
            (tmp / "packs" / "billing" / "invoices" / "package.yml").write_text(
                "enforce_dependencies: true\n",
                encoding="utf-8",
            )

            values = run_detect_stack(tmpdir)

        self.assertEqual(values["PACKAGE_LAYOUT"], "modular_monolith")
        self.assertIn("packs/billing/invoices", values["PACKAGE_LOCATIONS"])

    def test_detect_stack_falls_back_to_ruby_project_markers_without_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "app").mkdir()
            (tmp / "config").mkdir()
            (tmp / "config" / "application.rb").write_text("# rails-ish\n", encoding="utf-8")
            (tmp / "bin").mkdir()
            (tmp / "bin" / "rails").write_text("#!/usr/bin/env ruby\n", encoding="utf-8")
            os.chmod(tmp / "bin" / "rails", 0o755)

            values = run_detect_stack(tmpdir)

        self.assertEqual(values.get("FULL_RAILS_APP"), "true")
        self.assertEqual(values.get("PACKAGE_LAYOUT"), "single_app")

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
                    'if [[ "${1:-}" == "--version" || "${1:-}" == "gain" ]]; then\n'
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
        self.assertIn(
            "cannot inspect the hook payload because jq is unavailable", result.stderr
        )

    def test_security_reminder_warns_when_jq_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            app_dir = tmp / "app" / "controllers"
            app_dir.mkdir(parents=True)
            (app_dir / "admin_controller.rb").write_text(
                "class AdminController; end\n", encoding="utf-8"
            )
            payload = json.dumps(
                {"tool_input": {"file_path": "app/controllers/admin_controller.rb"}}
            )
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

        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "cannot inspect the hook payload because jq is unavailable", result.stderr
        )

    def test_security_reminder_warns_on_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()

            result = run_workspace_hook_raw(SECURITY_REMINDER, tmpdir, "{not-json")

        self.assertEqual(result.returncode, 0)
        self.assertIn("could not inspect an invalid hook payload", result.stderr)

    def test_security_reminder_warns_when_file_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()

            result = run_workspace_hook(SECURITY_REMINDER, tmpdir, {"tool_input": {}})

        self.assertEqual(result.returncode, 0)
        self.assertIn("tool_input.file_path was missing", result.stderr)

    def test_security_reminder_is_advisory_for_security_sensitive_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            target_dir = tmp / "app" / "controllers"
            target_dir.mkdir(parents=True)
            target = target_dir / "sessions_controller.rb"
            target.write_text("class SessionsController; end\n", encoding="utf-8")

            result = run_workspace_hook(
                SECURITY_REMINDER,
                tmpdir,
                {"tool_input": {"file_path": "app/controllers/sessions_controller.rb"}},
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("security-sensitive file detected", result.stderr.lower())
        self.assertIn("/rb:review security", result.stderr)

    def test_plan_stop_reminder_fails_closed_on_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()

            result = run_workspace_hook_raw(PLAN_STOP_REMINDER, tmpdir, "{not-json")

        self.assertEqual(result.returncode, 2)
        self.assertIn("could not safely inspect an invalid hook payload", result.stderr)

    def test_log_progress_warns_and_skips_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()

            result = run_workspace_hook_raw(LOG_PROGRESS, tmpdir, "{not-json")

        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "skipped progress logging because the hook payload was invalid",
            result.stderr,
        )

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
        self.assertEqual(
            payload["hookSpecificOutput"]["hookEventName"], "SubagentStart"
        )
        self.assertIn("Iron Law 1", payload["hookSpecificOutput"]["additionalContext"])

    def test_secret_scan_treats_stdout_findings_as_secret_hits_even_on_nonzero_exit(
        self,
    ) -> None:
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
            subprocess.run(
                ["git", "config", "user.email", "a@b.c"], cwd=tmp, check=True
            )
            subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
            (tmp / "tracked.txt").write_text("ok\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "commit", "--no-gpg-sign", "-m", "init"],
                cwd=tmp,
                check=True,
                capture_output=True,
            )
            (tmp / "untracked.txt").write_text("token=abc\n", encoding="utf-8")

            fake = tmp / "betterleaks"
            fake.write_text(
                "#!/usr/bin/env bash\necho 'FOUND SECRET'\nexit 0\n",
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

    def test_secret_scan_warns_when_betterleaks_is_missing_in_default_mode(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            target = tmp / "demo.txt"
            target.write_text("safe text\n", encoding="utf-8")
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in (
                "dirname",
                "jq",
                "grep",
                "git",
                "head",
                "pwd",
                "readlink",
                "rm",
                "mkdir",
                "cp",
                "mktemp",
                "mv",
                "sed",
                "wc",
                "find",
                "cut",
                "stat",
                "date",
                "tail",
                "tr",
                "cat",
            ):
                source = shutil.which(name)
                if source is None:
                    self.fail(name)
                os.symlink(source, fake_bin / name)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["BETTERLEAKS_PATH"] = ""
            env["RUBY_PLUGIN_HOOK_MODE"] = "default"
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(SECRET_SCAN)],
                input=json.dumps({"tool_input": {"file_path": str(target)}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED: Betterleaks is unavailable", result.stderr)

    def test_secret_scan_warns_when_default_mode_cannot_resolve_workspace_root(
        self,
    ) -> None:
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env["BETTERLEAKS_PATH"] = ""
        env["RUBY_PLUGIN_HOOK_MODE"] = "default"

        result = subprocess.run(
            ["bash", str(SECRET_SCAN)],
            input=json.dumps({"tool_input": {}}),
            capture_output=True,
            text=True,
            cwd="/",
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "BLOCKED: secret-scan.sh could not resolve the workspace root for secret scanning",
            result.stderr,
        )

    def test_secret_scan_blocks_strict_recent_change_scan_when_git_is_unavailable(
        self,
    ) -> None:
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
            if real_jq is None:
                self.fail('real_jq')
            if real_grep is None:
                self.fail('real_grep')
            (fake_bin / "jq").write_text(
                f'#!/bin/sh\nexec {real_jq} "$@"\n', encoding="utf-8"
            )
            (fake_bin / "grep").write_text(
                f'#!/bin/sh\nexec {real_grep} "$@"\n', encoding="utf-8"
            )
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
        self.assertIn("BLOCKED:", result.stderr)
        self.assertIn("could not perform strict recent-change scanning", result.stderr)

    def test_secret_scan_blocks_when_strict_recent_change_staging_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "a@b.c"], cwd=tmp, check=True
            )
            subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
            (tmp / "tracked.txt").write_text("ok\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "commit", "--no-gpg-sign", "-m", "init"],
                cwd=tmp,
                check=True,
                capture_output=True,
            )
            (tmp / "untracked.txt").write_text("token=abc\n", encoding="utf-8")

            fake = tmp / "betterleaks"
            fake.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            fake.chmod(0o755)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            if real_git is None:
                self.fail('real_git')
            (fake_bin / "git").write_text(
                f'#!/bin/sh\nexec {real_git} "$@"\n', encoding="utf-8"
            )
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
        self.assertIn("BLOCKED:", result.stderr)
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
        self.assertIn(
            "secret scan could not create a temporary workspace", result.stderr
        )

    def test_format_ruby_reports_tempfile_creation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\ngem "standard"\n', encoding="utf-8"
            )
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

    def test_format_ruby_skips_gemfile_when_formatter_dependency_state_is_transitional(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            gemfile = tmp / "Gemfile"
            gemfile.write_text(
                'source "https://rubygems.org"\ngem "standard"\n', encoding="utf-8"
            )
            (tmp / "Gemfile.lock").write_text(
                textwrap.dedent(
                    """
                    GEM
                      specs:
                        rubocop (1.80.0)

                    DEPENDENCIES
                      rubocop
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            fake_bundle = fake_bin / "bundle"
            fake_bundle.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
            fake_bundle.chmod(0o755)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", str(FORMAT_RUBY)],
                input=json.dumps({"tool_input": {"file_path": str(gemfile)}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("formatter dependencies are in transition", result.stderr)

    def test_format_ruby_blocks_when_bundler_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            (tmp / "Gemfile").write_text(
                'source "https://rubygems.org"\ngem "standard"\n', encoding="utf-8"
            )
            target = tmp / "demo.rb"
            target.write_text("puts :ok\n", encoding="utf-8")
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in ("jq", "dirname", "head", "readlink", "grep", "sed"):
                source = shutil.which(name)
                if source is None:
                    self.fail(name)
                os.symlink(source, fake_bin / name)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(FORMAT_RUBY)],
                input=json.dumps({"tool_input": {"file_path": str(target)}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED", result.stderr)
        self.assertNotIn("skipped", result.stderr)

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

    def test_verify_ruby_blocks_when_ruby_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()
            target = tmp / "demo.rb"
            target.write_text("puts :ok\n", encoding="utf-8")
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in ("jq", "dirname", "head", "readlink"):
                source = shutil.which(name)
                if source is None:
                    self.fail(name)
                os.symlink(source, fake_bin / name)
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(VERIFY_RUBY)],
                input=json.dumps({"tool_input": {"file_path": str(target)}}),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED", result.stderr)
        self.assertNotIn("skipped", result.stderr)

    def test_verify_ruby_blocks_when_file_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()

            result = run_workspace_hook(VERIFY_RUBY, tmpdir, {"tool_input": {}})

        self.assertEqual(result.returncode, 2)
        self.assertIn("tool_input.file_path was missing", result.stderr)

    def test_detect_runtime_warns_when_runtime_env_tempfile_cannot_be_created(
        self,
    ) -> None:
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

    def test_detect_runtime_warns_when_runtime_state_dir_cannot_be_prepared(
        self,
    ) -> None:
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
            subprocess.run(
                ["git", "add", "demo.json"], cwd=tmp, check=True, capture_output=True
            )

            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            if real_git is None:
                self.fail('real_git')
            (fake_bin / "git").write_text(
                f'#!/bin/sh\nexec {real_git} "$@"\n', encoding="utf-8"
            )
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

    def test_pre_commit_hook_requires_shellcheck_for_shell_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            shell_file = tmp / "demo.sh"
            shell_file.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
            subprocess.run(["git", "add", "demo.sh"], cwd=tmp, check=True, capture_output=True)

            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in ("git", "npx", "python3", "bash"):
                source = shutil.which(name)
                if source is None:
                    self.fail(name)
                os.symlink(source, fake_bin / name)

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
        self.assertIn("shellcheck not found", result.stderr)
        self.assertIn("Install shellcheck", result.stderr)

    def test_validate_plugin_reports_missing_claude_cli_with_install_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            env = dict(os.environ)
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(VALIDATE_PLUGIN)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("claude is required for plugin validation", result.stderr)
        self.assertIn("@anthropic-ai/claude-code", result.stderr)

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
            degradation_log = claude_dir / ".logs" / "hook-degradations.log"
            log_exists = degradation_log.is_file()
            log_content = degradation_log.read_text(encoding="utf-8") if log_exists else ""
            created_dirs = [
                claude_dir / "plans",
                claude_dir / "research",
                claude_dir / "reviews",
                claude_dir / "solutions",
                claude_dir / "audit",
                claude_dir / "skill-metrics",
            ]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "skipping setup-dirs.sh because hook input was invalid", result.stderr
        )
        self.assertTrue(log_exists)
        self.assertIn(
            "session directory bootstrap skipped because hook input was invalid",
            log_content,
        )
        for path in created_dirs:
            self.assertFalse(path.exists(), path)

    def test_setup_dirs_does_not_follow_symlinked_degradation_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            log_dir = tmp / ".claude" / ".logs"
            log_dir.mkdir(parents=True)
            external_log = tmp / "external.log"
            external_log.write_text("before\n", encoding="utf-8")
            os.symlink(external_log, log_dir / "hook-degradations.log")

            result = run_workspace_hook_raw(SETUP_DIRS, tmpdir, "{not-json")
            external_log_contents = external_log.read_text(encoding="utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipping setup-dirs.sh because hook input was invalid", result.stderr)
        self.assertEqual(external_log_contents, "before\n")

    def test_check_resume_blocks_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook_raw(CHECK_RESUME, tmpdir, "{not-json")
            degradation_log = tmp / ".claude" / ".logs" / "hook-degradations.log"
            log_exists = degradation_log.is_file()
            log_content = degradation_log.read_text(encoding="utf-8") if log_exists else ""

        self.assertEqual(result.returncode, 0)
        self.assertIn("could not safely inspect", result.stderr)
        self.assertTrue(log_exists)
        self.assertIn(
            "resume reminder skipped because hook input was invalid",
            log_content,
        )

    def test_stop_failure_log_skips_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(plan_dir) + "\n", encoding="utf-8"
            )
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook_raw(STOP_FAILURE_LOG, tmpdir, "{not-json")
            degradation_log = tmp / ".claude" / ".logs" / "hook-degradations.log"
            log_exists = degradation_log.is_file()
            log_content = degradation_log.read_text(encoding="utf-8") if log_exists else ""

        self.assertEqual(result.returncode, 0)
        self.assertIn("could not safely inspect", result.stderr)
        self.assertTrue(log_exists)
        self.assertIn(
            "stop-failure context was not persisted because hook input was invalid",
            log_content,
        )

    def test_check_scratchpad_logs_invalid_payload_degradation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / ".claude").mkdir()

            result = run_workspace_hook_raw(CHECK_SCRATCHPAD, tmpdir, "{not-json")
            degradation_log = tmp / ".claude" / ".logs" / "hook-degradations.log"
            log_exists = degradation_log.is_file()
            log_content = degradation_log.read_text(encoding="utf-8") if log_exists else ""
            scratchpad_exists = (tmp / ".claude" / "scratchpad.md").exists()

        self.assertEqual(result.returncode, 0)
        self.assertIn("hook input was invalid", result.stderr)
        self.assertTrue(log_exists)
        self.assertIn(
            "scratchpad reminder skipped because hook input was invalid",
            log_content,
        )
        self.assertFalse(scratchpad_exists)

    def test_active_plan_marker_respects_numbered_unchecked_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text(
                "# Demo\n\n1. [ ] first task\n", encoding="utf-8"
            )
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
            (plan_dir / "plan.md").write_text(
                "# Demo\n\n* [ ] first task\n", encoding="utf-8"
            )

            result = run_active_plan_query(tmpdir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), plan_dir.resolve())

    def test_active_plan_fallback_respects_bare_markdown_checkboxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text(
                "# Demo\n\n[ ] first task\n", encoding="utf-8"
            )

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

            pending = run_workspace_hook(
                CHECK_PENDING_PLANS, tmpdir, {"stop_hook_active": False}
            )
            resume = run_workspace_hook(CHECK_RESUME, tmpdir)

        self.assertEqual(pending.returncode, 0, pending.stderr)
        self.assertIn("1 plan(s) have uncompleted tasks", pending.stdout)
        self.assertEqual(resume.returncode, 0, resume.stderr)
        self.assertIn("has 3 remaining tasks (1 done)", resume.stdout)

    def test_check_pending_plans_does_not_suppress_output_on_stop_hook_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("# Demo\n\n- [ ] task\n", encoding="utf-8")

            pending = run_workspace_hook(
                CHECK_PENDING_PLANS, tmpdir, {"stop_hook_active": True}
            )

        self.assertEqual(pending.returncode, 0, pending.stderr)
        self.assertIn("1 plan(s) have uncompleted tasks", pending.stdout)

    def test_check_resume_counts_bare_markdown_checkboxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text(
                textwrap.dedent(
                    """
                    # Demo

                    [ ] investigate race condition
                    [x] document findings
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            resume = run_workspace_hook(CHECK_RESUME, tmpdir)

        self.assertEqual(resume.returncode, 0, resume.stderr)
        self.assertIn("has 1 remaining tasks (1 done)", resume.stdout)

    def _current_plugin_version(self) -> str:
        plugin_json = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(plugin_json.read_text(encoding="utf-8"))
        version = data.get("version")
        if not isinstance(version, str) or not version:
            self.fail("plugin.json missing version field")
        return version

    def _run_check_plugin_version(
        self,
        repo_root: str,
        *,
        session_id: str = "test-session",
        data_dir: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = repo_root
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
        if data_dir is not None:
            env["CLAUDE_PLUGIN_DATA"] = data_dir
        else:
            env.pop("CLAUDE_PLUGIN_DATA", None)
        payload = json.dumps({"session_id": session_id, "cwd": repo_root})
        return subprocess.run(
            ["bash", str(CHECK_PLUGIN_VERSION)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
            env=env,
        )

    def _write_claude_md_with_pinned_version(
        self, repo_root: Path, pinned: str
    ) -> None:
        (repo_root / "CLAUDE.md").write_text(
            textwrap.dedent(
                f"""
                <!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
                <!-- Auto-generated by /rb:init | 2026-04-18 | Ruby 3.4.7 | Betterleaks: available | plugin v{pinned} -->

                Managed content.

                <!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    def test_check_plugin_version_silent_on_match(self) -> None:
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            self._write_claude_md_with_pinned_version(Path(tmpdir), current)
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_check_plugin_version_warns_when_pinned_is_outdated(self) -> None:
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            self._write_claude_md_with_pinned_version(Path(tmpdir), "0.1.0")
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"v{current}", result.stdout)
        self.assertIn("v0.1.0", result.stdout)
        self.assertIn("/rb:init --update", result.stdout)

    def test_check_plugin_version_warns_when_pinned_is_newer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            # Pinned is deliberately ahead of any real plugin version.
            self._write_claude_md_with_pinned_version(Path(tmpdir), "99.0.0")
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v99.0.0", result.stdout)
        self.assertIn("downgraded", result.stdout)

    def test_check_plugin_version_silent_when_claude_md_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_check_plugin_version_silent_when_marker_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            (Path(tmpdir) / "CLAUDE.md").write_text(
                "# Project\n\nNo managed block here.\n", encoding="utf-8"
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_check_plugin_version_once_per_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            self._write_claude_md_with_pinned_version(Path(tmpdir), "0.1.0")
            first = self._run_check_plugin_version(
                tmpdir, session_id="sess-1", data_dir=data
            )
            second = self._run_check_plugin_version(
                tmpdir, session_id="sess-1", data_dir=data
            )
            third = self._run_check_plugin_version(
                tmpdir, session_id="sess-2", data_dir=data
            )

        self.assertIn("v0.1.0", first.stdout)
        self.assertEqual(second.stdout, "", "second call in same session should be silent")
        self.assertIn("v0.1.0", third.stdout, "different session_id should re-fire")

    def test_check_plugin_version_handles_pipe_delimited_real_header(self) -> None:
        # Shape matching the actual injected template header comment (no space
        # between version and trailing pipe or comment close).
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            (Path(tmpdir) / "CLAUDE.md").write_text(
                textwrap.dedent(
                    f"""
                    <!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
                    <!-- Auto-generated by /rb:init | 2026-04-18 | Ruby 3.4.7 | Betterleaks: available | plugin v{current}|something else -->

                    Managed content.

                    <!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "",
            "pipe-delimited real-header shape must extract cleanly and stay silent on match",
        )

    def test_check_plugin_version_ignores_foreign_plugin_markers(self) -> None:
        # Managed block may contain unrelated tokens like `some-plugin v1.2.3`
        # from other tools. Only the word-bounded `plugin v<semver>` token is
        # ours — foreign prefixes must not hijack extraction.
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            (Path(tmpdir) / "CLAUDE.md").write_text(
                textwrap.dedent(
                    f"""
                    <!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
                    <!-- some-plugin v1.2.3 | another-plugin v4.5.6 | plugin v{current} -->

                    Managed content.

                    <!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "",
            f"foreign plugin markers must not trigger a drift warning "
            f"when our `plugin v{current}` token matches the installed version",
        )

    def test_check_plugin_version_picks_our_token_despite_foreign_versions(
        self,
    ) -> None:
        # Same scenario but our token is pinned to an older version. Hook
        # must extract `plugin v0.1.0` (not `some-plugin v1.2.3`) and warn.
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            (Path(tmpdir) / "CLAUDE.md").write_text(
                textwrap.dedent(
                    f"""
                    <!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
                    <!-- some-plugin v{current} | plugin v0.1.0 | another-plugin v{current} -->

                    Managed content.

                    <!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("v0.1.0", result.stdout)
        self.assertIn(f"v{current}", result.stdout)
        self.assertIn("/rb:init --update", result.stdout)

    def test_check_plugin_version_rejects_non_semver_marker(self) -> None:
        # `1.2.3rc1` (no `-` separator) is NOT valid semver per §9 grammar.
        # Strict regex must reject it so the hook stays silent instead of
        # mis-parsing it as a version.
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            (Path(tmpdir) / "CLAUDE.md").write_text(
                textwrap.dedent(
                    """
                    <!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
                    <!-- plugin v1.2.3rc1 -->

                    Managed content.

                    <!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout, "", "non-semver marker must not be parsed as a version"
        )

    def test_check_plugin_version_rejects_leading_zero_marker(self) -> None:
        # Leading zeros on MAJOR/MINOR/PATCH are invalid per semver §2.
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            (Path(tmpdir) / "CLAUDE.md").write_text(
                textwrap.dedent(
                    """
                    <!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
                    <!-- plugin v01.02.03 -->

                    Managed content.

                    <!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout, "", "leading-zero marker must not be parsed as a version"
        )

    def test_check_plugin_version_ignores_build_metadata_per_semver(self) -> None:
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            # Per semver.org/#spec-item-10, build metadata (`+<build>`) MUST NOT
            # affect equality or precedence. Same triple + different builds
            # must stay silent.
            self._write_claude_md_with_pinned_version(
                Path(tmpdir), f"{current}+build.5"
            )
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "",
            "same version with differing build metadata must not warn",
        )

    def test_check_plugin_version_treats_prerelease_as_outdated_vs_release(
        self,
    ) -> None:
        current = self._current_plugin_version()
        with tempfile.TemporaryDirectory() as tmpdir, tempfile.TemporaryDirectory() as data:
            # Per semver precedence (and `sort -V`): `1.13.1-rc1` < `1.13.1`.
            self._write_claude_md_with_pinned_version(Path(tmpdir), f"{current}-rc1")
            result = self._run_check_plugin_version(tmpdir, data_dir=data)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"v{current}-rc1", result.stdout)
        self.assertIn(f"v{current}", result.stdout)
        self.assertIn("/rb:init --update", result.stdout)

    def test_check_scratchpad_auto_initializes_missing_scratchpad_for_active_plan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text(
                "# Demo\n\n- [ ] first task\n", encoding="utf-8"
            )
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(plan_dir.resolve()) + "\n", encoding="utf-8"
            )

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

    def test_check_scratchpad_does_not_backfill_completed_historical_plans(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plans_dir = tmp / ".claude" / "plans"

            active_dir = plans_dir / "active"
            active_dir.mkdir(parents=True)
            (active_dir / "plan.md").write_text(
                "# Active\n\n- [ ] first task\n", encoding="utf-8"
            )

            complete_dir = plans_dir / "complete"
            complete_dir.mkdir(parents=True)
            (complete_dir / "plan.md").write_text(
                "# Complete\n\n- [x] done\n", encoding="utf-8"
            )
            (complete_dir / "progress.md").write_text("done\n", encoding="utf-8")

            noted_dir = plans_dir / "noted"
            noted_dir.mkdir(parents=True)
            (noted_dir / "plan.md").write_text(
                "# Noted\n\n- [x] done\n", encoding="utf-8"
            )
            (noted_dir / "scratchpad.md").write_text(
                "# Scratchpad: noted\n", encoding="utf-8"
            )

            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(active_dir.resolve()) + "\n", encoding="utf-8"
            )

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

    def test_error_critic_warns_when_hook_state_storage_cannot_be_prepared(
        self,
    ) -> None:
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
                ["/bin/bash", str(ERROR_CRITIC)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("hook-state could not be updated", result.stderr)

    def test_error_critic_blocks_when_cksum_or_awk_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in (
                "jq",
                "grep",
                "dirname",
                "mkdir",
                "mktemp",
                "mv",
                "rmdir",
                "tail",
                "head",
                "tr",
                "date",
            ):
                source = shutil.which(name)
                if source is None:
                    self.fail(name)
                os.symlink(source, fake_bin / name)
            payload = {
                "tool_input": {"command": "bundle exec rspec spec/models"},
                "error": "expected: 1\ngot: 0",
                "session_id": "abc123",
            }
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(ERROR_CRITIC)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cksum", result.stderr)

    def test_ruby_failure_hints_blocks_on_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            result = subprocess.run(
                ["bash", str(RUBY_FAILURE_HINTS)],
                input="{bad-json",
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("could not safely inspect an invalid hook payload", result.stderr)

    def test_ruby_failure_hints_distinguishes_truncated_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = dict(os.environ)
            env["CLAUDE_PROJECT_DIR"] = tmpdir
            env["RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES"] = "10"
            result = subprocess.run(
                ["bash", str(RUBY_FAILURE_HINTS)],
                input=json.dumps(
                    {"tool_input": {"command": "bundle exec rspec spec/models"}}
                ),
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "could not safely inspect a truncated hook payload", result.stderr
        )

    def test_precompact_rules_surfaces_active_plan_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            research_dir = plan_dir / "research"
            research_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(plan_dir) + "\n", encoding="utf-8"
            )
            (research_dir / "notes.md").write_text("x\n", encoding="utf-8")

            result = run_workspace_hook(PRECOMPACT_RULES, tmpdir, {})

        self.assertEqual(result.returncode, 0)
        self.assertIn("PRESERVE ACROSS COMPACTION", result.stderr)

    def test_precompact_rules_blocks_during_work_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(plan_dir) + "\n", encoding="utf-8"
            )
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook(PRECOMPACT_RULES, tmpdir, {})

        self.assertEqual(result.returncode, 2)
        self.assertIn("PRESERVE ACROSS COMPACTION", result.stderr)

    def test_precompact_rules_blocks_during_full_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(plan_dir) + "\n", encoding="utf-8"
            )
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")
            (plan_dir / "progress.md").write_text(
                "**State**: working\n", encoding="utf-8"
            )

            result = run_workspace_hook(PRECOMPACT_RULES, tmpdir, {})

        self.assertEqual(result.returncode, 2)
        self.assertIn("PRESERVE ACROSS COMPACTION", result.stderr)
        self.assertIn("/rb:full", result.stderr)

    def test_postcompact_verify_surfaces_active_plan_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "demo"
            plan_dir.mkdir(parents=True)
            (tmp / ".claude" / "ACTIVE_PLAN").write_text(
                str(plan_dir) + "\n", encoding="utf-8"
            )
            (plan_dir / "plan.md").write_text("- [ ] task\n", encoding="utf-8")

            result = run_workspace_hook(POSTCOMPACT_VERIFY, tmpdir, {})

        self.assertEqual(result.returncode, 2)
        self.assertIn("POST-COMPACTION", result.stderr)
        self.assertIn(".claude/plans/demo/plan.md", result.stderr)

    def test_active_plan_detection_allows_benign_double_dot_plan_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            plan_dir = tmp / ".claude" / "plans" / "feature..v2"
            plan_dir.mkdir(parents=True)
            (plan_dir / "plan.md").write_text("[ ] investigate drift\n", encoding="utf-8")

            result = run_active_plan_query(tmpdir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), plan_dir.resolve())

    def test_check_dynamic_injection_errors_when_git_is_missing_for_tracked_scan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            plugin_dir = tmp / "plugins"
            plugin_dir.mkdir()
            (plugin_dir / "doc.md").write_text("x" * 32, encoding="utf-8")
            env = dict(os.environ)
            env["RUBY_PLUGIN_DYNAMIC_INJECTION_MAX_BYTES"] = "1"

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "tracked dynamic-injection scan requires git metadata or an explicit --manifest <file>",
            result.stderr,
        )
        self.assertIn("rerun from a repository checkout", result.stderr)

    def test_check_dynamic_injection_manifest_supports_non_git_changed_scan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / "README.md").write_text("Literal danger: !`uname -a`\n", encoding="utf-8")
            manifest = tmp / "manifest.txt"
            manifest.write_text("README.md\n", encoding="utf-8")

            result = subprocess.run(
                ["/bin/bash", str(script_copy), "--manifest", str(manifest)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dynamic context injection found", result.stdout)

    def test_check_dynamic_injection_manifest_scans_invalid_utf8_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / "README.md").write_bytes(b"Literal danger: !`uname -a`\xff\n")
            manifest = tmp / "manifest.txt"
            manifest.write_text("README.md\n", encoding="utf-8")

            result = subprocess.run(
                ["/bin/bash", str(script_copy), "--manifest", str(manifest)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dynamic context injection found", result.stdout)

    def test_check_dynamic_injection_manifest_scans_invalid_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / "payload.json").write_bytes(
                b'{"danger":"!`uname -a`\xff"}\n'
            )
            manifest = tmp / "manifest.txt"
            manifest.write_text("payload.json\n", encoding="utf-8")

            result = subprocess.run(
                ["/bin/bash", str(script_copy), "--manifest", str(manifest)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dynamic context injection found", result.stdout)

    def test_check_dynamic_injection_manifest_rejects_unresolved_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / "README.md").write_text("safe\n", encoding="utf-8")
            manifest = tmp / "manifest.txt"
            manifest.write_text("README.md\nmissing.md\n", encoding="utf-8")

            result = subprocess.run(
                ["/bin/bash", str(script_copy), "--manifest", str(manifest)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("manifest entry could not be resolved", result.stderr)

    def test_check_dynamic_injection_manifest_rejects_unsupported_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / "script.rb").write_text("!`uname -a`\n", encoding="utf-8")
            manifest = tmp / "manifest.txt"
            manifest.write_text("script.rb\n", encoding="utf-8")

            result = subprocess.run(
                ["/bin/bash", str(script_copy), "--manifest", str(manifest)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("outside the supported markdown/json/yaml scan set", result.stderr)

    def test_check_dynamic_injection_manifest_rejects_untracked_entries_in_git_repo(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "README.md").write_text("safe\n", encoding="utf-8")
            (tmp / "notes.md").write_text("safe\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "README.md"], cwd=tmp, check=True, capture_output=True
            )
            manifest = tmp / "manifest.txt"
            manifest.write_text("README.md\nnotes.md\n", encoding="utf-8")

            result = subprocess.run(
                ["/bin/bash", str(script_copy), "--manifest", str(manifest)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("is not tracked by git", result.stderr)

    def test_check_dynamic_injection_scans_tracked_top_level_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "CHANGELOG.md").write_text(
                "## Change\n\n!`uname -a`\n", encoding="utf-8"
            )
            subprocess.run(
                ["git", "add", "CHANGELOG.md"], cwd=tmp, check=True, capture_output=True
            )

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dynamic context injection found", result.stdout)

    def test_check_dynamic_injection_ignores_bang_methods_inside_inline_code(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "README.md").write_text(
                "- Use `disable_ddl_transaction!` with `algorithm: :concurrently`\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "README.md"], cwd=tmp, check=True, capture_output=True
            )

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No dynamic context injection found.", result.stdout)

    def test_check_dynamic_injection_blocks_when_unbalanced_backticks_hide_token(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "README.md").write_text(
                'title: "prefix ` text !`uname -a`"\n',
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "README.md"], cwd=tmp, check=True, capture_output=True
            )

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("Dynamic context injection found", result.stdout)

    def test_check_dynamic_injection_ignores_fenced_code_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            (tmp / "README.md").write_text(
                textwrap.dedent(
                    """\
                    ```md
                    Example literal syntax: !`echo hello`
                    ```
                    """
                ),
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "README.md"], cwd=tmp, check=True, capture_output=True
            )

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=dict(os.environ),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No dynamic context injection found.", result.stdout)

    def test_check_dynamic_injection_requires_git_when_git_metadata_exists(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / ".git").mkdir()
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            dirname_path = shutil.which("dirname")
            grep_path = shutil.which("grep")
            awk_path = shutil.which("awk")
            python3_path = shutil.which("python3")
            if dirname_path is None:
                self.fail('dirname_path')
            if grep_path is None:
                self.fail('grep_path')
            if awk_path is None:
                self.fail('awk_path')
            if python3_path is None:
                self.fail('python3_path')
            os.symlink(dirname_path, fake_bin / "dirname")
            os.symlink(grep_path, fake_bin / "grep")
            os.symlink(awk_path, fake_bin / "awk")
            os.symlink(python3_path, fake_bin / "python3")
            env = dict(os.environ)
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "git is required for tracked dynamic-injection scanning", result.stderr
        )

    def test_check_dynamic_injection_requires_git_when_git_metadata_is_a_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            script_dir = tmp / "scripts"
            script_dir.mkdir()
            script_copy = script_dir / "check-dynamic-injection.sh"
            script_copy.write_text(
                CHECK_DYNAMIC_INJECTION.read_text(encoding="utf-8"), encoding="utf-8"
            )
            os.chmod(script_copy, 0o755)
            (tmp / ".git").write_text("gitdir: /tmp/worktrees/demo\n", encoding="utf-8")
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            dirname_path = shutil.which("dirname")
            grep_path = shutil.which("grep")
            awk_path = shutil.which("awk")
            python3_path = shutil.which("python3")
            if dirname_path is None:
                self.fail('dirname_path')
            if grep_path is None:
                self.fail('grep_path')
            if awk_path is None:
                self.fail('awk_path')
            if python3_path is None:
                self.fail('python3_path')
            os.symlink(dirname_path, fake_bin / "dirname")
            os.symlink(grep_path, fake_bin / "grep")
            os.symlink(awk_path, fake_bin / "awk")
            os.symlink(python3_path, fake_bin / "python3")
            env = dict(os.environ)
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(script_copy)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "git is required for tracked dynamic-injection scanning", result.stderr
        )

    def test_run_eval_marks_include_untracked_as_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            if real_git is None:
                self.fail('real_git')
            (fake_bin / "npm").write_text(
                "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
            )
            (fake_bin / "git").write_text(
                "#!/usr/bin/env bash\n"
                f"REAL_GIT={shlex.quote(real_git)}\n"
                'case "$*" in\n'
                "  'rev-parse --verify HEAD') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/evals/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/evals/') exit 0 ;;\n"
                "  'ls-files -z -- *.md *.json *.yml *.yaml') exit 0 ;;\n"
                "  'ls-files --others --exclude-standard') exit 0 ;;\n"
                "  'ls-files --others --exclude-standard -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'ls-files --others --exclude-standard -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'ls-files --others --exclude-standard -- lab/eval/triggers/') exit 0 ;;\n"
                "  'ls-files --others --exclude-standard -- lab/eval/evals/') exit 0 ;;\n"
                "esac\n"
                'exec "$REAL_GIT" "$@"\n',
                encoding="utf-8",
            )
            os.chmod(fake_bin / "npm", 0o755)
            os.chmod(fake_bin / "git", 0o755)
            env = dict(os.environ)
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
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

    def test_run_eval_changed_mode_lints_only_changed_markdown_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            real_python3 = shutil.which("python3")
            real_jq = shutil.which("jq")
            if real_git is None:
                self.fail('real_git')
            if real_python3 is None:
                self.fail('real_python3')
            if real_jq is None:
                self.fail('real_jq')
            (fake_bin / "npm").write_text(
                "#!/usr/bin/env bash\n"
                'if [[ "${1:-}" == "exec" ]]; then\n'
                '  shift\n'
                '  if [[ "$*" == "-- markdownlint -- plugins/ruby-grape-rails/agents/ruby-reviewer.md" ]]; then\n'
                "    exit 0\n"
                "  fi\n"
                '  echo "unexpected markdownlint invocation: $*" >&2\n'
                "  exit 9\n"
                "fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            (fake_bin / "git").write_text(
                "#!/usr/bin/env bash\n"
                f"REAL_GIT={shlex.quote(real_git)}\n"
                'case "$*" in\n'
                "  'rev-parse --verify HEAD') exit 0 ;;\n"
                "  'rev-parse --git-dir') printf '.git\\n'; exit 0 ;;\n"
                "  'ls-files -z -- *.md *.json *.yml *.yaml') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD') printf 'M\\0plugins/ruby-grape-rails/agents/ruby-reviewer.md\\0' ; exit 0 ;;\n"
                "  'diff --cached --name-status -z -M') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/agents/') printf 'M\\0plugins/ruby-grape-rails/agents/ruby-reviewer.md\\0' ; exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/evals/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/evals/') exit 0 ;;\n"
                "esac\n"
                'exec "$REAL_GIT" "$@"\n',
                encoding="utf-8",
            )
            os.chmod(fake_bin / "npm", 0o755)
            os.chmod(fake_bin / "git", 0o755)
            os.symlink(real_python3, fake_bin / "python3")
            os.symlink(real_jq, fake_bin / "jq")
            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"

            result = subprocess.run(
                ["bash", str(RUN_EVAL), "--changed"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Linting 1 changed markdown file(s).", result.stdout)

    def test_run_eval_changed_mode_does_not_require_npm_or_jq_when_no_changed_work_needs_them(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            if real_git is None:
                self.fail('real_git')
            (fake_bin / "git").write_text(
                "#!/usr/bin/env bash\n"
                f"REAL_GIT={shlex.quote(real_git)}\n"
                'case "$*" in\n'
                "  'rev-parse --verify HEAD') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/evals/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/evals/') exit 0 ;;\n"
                "esac\n"
                'exec "$REAL_GIT" "$@"\n',
                encoding="utf-8",
            )
            (fake_bin / "npm").write_text(
                "#!/usr/bin/env bash\necho 'npm should not be called' >&2\nexit 9\n",
                encoding="utf-8",
            )
            (fake_bin / "jq").write_text(
                "#!/usr/bin/env bash\necho 'jq should not be called' >&2\nexit 9\n",
                encoding="utf-8",
            )
            os.chmod(fake_bin / "git", 0o755)
            os.chmod(fake_bin / "npm", 0o755)
            os.chmod(fake_bin / "jq", 0o755)
            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"

            result = subprocess.run(
                ["bash", str(RUN_EVAL), "--changed"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No changed markdown files detected.", result.stdout)
        self.assertIn(
            "No changed markdown/JSON/YAML files detected for injection scan.",
            result.stdout,
        )
        self.assertIn("changed mode is partial coverage", result.stdout)

    def test_run_eval_warns_when_include_untracked_is_ignored_outside_changed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            if real_git is None:
                self.fail('real_git')
            (fake_bin / "npm").write_text(
                "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
            )
            (fake_bin / "git").write_text(
                "#!/usr/bin/env bash\n"
                f"REAL_GIT={shlex.quote(real_git)}\n"
                'exec "$REAL_GIT" "$@"\n',
                encoding="utf-8",
            )
            os.chmod(fake_bin / "npm", 0o755)
            os.chmod(fake_bin / "git", 0o755)
            env = dict(os.environ)
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
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
            self.assertIn(
                f"{env_name} must be a finite numeric threshold between 0 and 1",
                result.stderr,
            )

    def test_run_eval_rejects_out_of_range_threshold_envs(self) -> None:
        for threshold in ("-1", "2"):
            env = dict(os.environ)
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = threshold
            result = subprocess.run(
                ["bash", str(RUN_EVAL), "--skills"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 1, threshold)
            self.assertIn(
                "must be a finite numeric threshold between 0 and 1", result.stderr
            )

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

    def test_run_eval_reports_missing_npm_for_linting_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            python3_path = shutil.which("python3")
            dirname_path = shutil.which("dirname")
            git_path = shutil.which("git")
            mktemp_path = shutil.which("mktemp")
            jq_path = shutil.which("jq")
            if python3_path is None:
                self.fail('python3_path')
            if dirname_path is None:
                self.fail('dirname_path')
            if git_path is None:
                self.fail('git_path')
            if mktemp_path is None:
                self.fail('mktemp_path')
            if jq_path is None:
                self.fail('jq_path')
            os.symlink(python3_path, fake_bin / "python3")
            os.symlink(dirname_path, fake_bin / "dirname")
            os.symlink(git_path, fake_bin / "git")
            os.symlink(mktemp_path, fake_bin / "mktemp")
            os.symlink(jq_path, fake_bin / "jq")
            env = dict(os.environ)
            env["PATH"] = str(fake_bin)
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"

            result = subprocess.run(
                ["/bin/bash", str(RUN_EVAL), "--ci"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("npm is required for linting in --ci mode", result.stderr)

    def test_run_eval_changed_mode_skips_deleted_or_moved_paths_with_warning(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            real_git = shutil.which("git")
            real_python3 = shutil.which("python3")
            if real_git is None:
                self.fail('real_git')
            if real_python3 is None:
                self.fail('real_python3')
            (fake_bin / "npm").write_text(
                "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
            )
            (fake_bin / "git").write_text(
                "#!/usr/bin/env bash\n"
                f"REAL_GIT={shlex.quote(real_git)}\n"
                'case "$*" in\n'
                "  'rev-parse --verify HEAD') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/skills/')\n"
                "    printf 'M\\0plugins/ruby-grape-rails/skills/plan/SKILL.md\\0R100\\0plugins/ruby-grape-rails/skills/old/SKILL.md\\0plugins/ruby-grape-rails/skills/missing/SKILL.md\\0'\n"
                "    exit 0\n"
                "    ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/skills/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- plugins/ruby-grape-rails/agents/')\n"
                "    printf 'M\\0plugins/ruby-grape-rails/agents/ruby-reviewer.md\\0R100\\0plugins/ruby-grape-rails/agents/old.md\\0plugins/ruby-grape-rails/agents/missing.md\\0'\n"
                "    exit 0\n"
                "    ;;\n"
                "  'diff --cached --name-status -z -M -- plugins/ruby-grape-rails/agents/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/triggers/') exit 0 ;;\n"
                "  'diff --name-status -z -M HEAD -- lab/eval/evals/') exit 0 ;;\n"
                "  'diff --cached --name-status -z -M -- lab/eval/evals/') exit 0 ;;\n"
                "esac\n"
                'exec "$REAL_GIT" "$@"\n',
                encoding="utf-8",
            )
            os.chmod(fake_bin / "npm", 0o755)
            os.chmod(fake_bin / "git", 0o755)
            os.symlink(real_python3, fake_bin / "python3")
            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["RUBY_PLUGIN_EVAL_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_AGENT_FAIL_UNDER"] = "0"
            env["RUBY_PLUGIN_EVAL_TRIGGER_FAIL_UNDER"] = "0"

            result = subprocess.run(
                ["bash", str(RUN_EVAL), "--changed"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "skipping deleted or moved changed skills: missing", result.stderr
        )
        self.assertIn(
            "skipping deleted or moved changed agents: missing", result.stderr
        )

    def test_run_eval_tests_resolves_repo_root_when_invoked_through_symlink(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            symlink_path = tmp / "run-eval-tests.sh"
            os.symlink(RUN_EVAL_TESTS, symlink_path)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            python3 = fake_bin / "python3"
            python3.write_text(
                "#!/bin/bash\n"
                'if [[ "${1:-}" == "-c" ]]; then\n'
                "  exit 0\n"
                "fi\n"
                "pwd\n",
                encoding="utf-8",
            )
            python3.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

            result = subprocess.run(
                ["bash", str(symlink_path)],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(REPO_ROOT))

    def test_run_eval_tests_does_not_require_readlink_without_symlink_chain(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            dirname_path = shutil.which("dirname")
            if dirname_path is None:
                self.fail('dirname_path')
            python3 = fake_bin / "python3"
            python3.write_text(
                "#!/bin/bash\n"
                'if [[ "${1:-}" == "-c" ]]; then\n'
                "  exit 0\n"
                "fi\n"
                "pwd\n",
                encoding="utf-8",
            )
            python3.chmod(0o755)
            os.symlink(dirname_path, fake_bin / "dirname")
            env = dict(os.environ)
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(RUN_EVAL_TESTS)],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(REPO_ROOT))

    def test_fetch_claude_docs_unknown_argument_uses_stderr(self) -> None:
        result = subprocess.run(
            ["bash", str(FETCH_CLAUDE_DOCS), "--bogus"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Unknown argument: --bogus", result.stderr)

    def test_fetch_claude_docs_preflights_required_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_bin = tmp / "bin"
            fake_bin.mkdir()
            for name in (
                "curl",
                "date",
                "dirname",
                "mkdir",
                "mktemp",
                "mv",
                "rm",
                "sed",
                "stat",
                "wc",
            ):
                source = shutil.which(name)
                if source is None:
                    self.fail(name)
                os.symlink(source, fake_bin / name)
            env = dict(os.environ)
            env["PATH"] = str(fake_bin)

            result = subprocess.run(
                ["/bin/bash", str(FETCH_CLAUDE_DOCS), "--index-only"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("required command not found: grep", result.stderr)

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

    def test_generate_iron_law_content_rejects_duplicate_ids(self) -> None:
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
                        law_count: 1
                      - id: data
                        name: More Data
                        law_count: 1
                    laws:
                      - id: 1
                        category: data
                        title: One
                        rule: Do it
                        summary_text: One
                        rationale: Why
                        subagent_text: One
                      - id: 1
                        category: data
                        title: Two
                        rule: Do it again
                        summary_text: Two
                        rationale: Why
                        subagent_text: Two
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
        self.assertIn("duplicate category ids", result.stderr)
        self.assertIn("duplicate law ids", result.stderr)

    def test_generate_iron_law_content_rejects_null_required_category_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            yaml_path = tmp / "iron-laws.yml"
            yaml_path.write_text(
                textwrap.dedent(
                    """
                    version: "1"
                    last_updated: "2026-04-02"
                    total_laws: 1
                    categories:
                      - id: ~
                        name: ~
                        law_count: ~
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
        self.assertIn("category[0] missing: id, name, law_count", result.stderr)

    def test_generate_iron_law_content_rejects_null_required_law_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            yaml_path = tmp / "iron-laws.yml"
            yaml_path.write_text(
                textwrap.dedent(
                    """
                    version: "1"
                    last_updated: "2026-04-02"
                    total_laws: 1
                    categories:
                      - id: data
                        name: Data
                        law_count: 1
                    laws:
                      - id: ~
                        category: ~
                        title: ~
                        rule: ~
                        summary_text: ~
                        rationale: ~
                        subagent_text: ~
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
        self.assertIn(
            "law[0] missing: id, category, title, rule, summary_text, rationale, subagent_text",
            result.stderr,
        )

    def test_generate_iron_law_content_rejects_null_total_laws_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            yaml_path = tmp / "iron-laws.yml"
            yaml_path.write_text(
                textwrap.dedent(
                    """
                    version: "1"
                    last_updated: "2026-04-02"
                    total_laws: ~
                    categories:
                      - id: data
                        name: Data
                        law_count: 1
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
        self.assertIn("total_laws must be an integer", result.stderr)

    def test_generate_iron_law_content_rejects_null_category_law_count_without_crashing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            yaml_path = tmp / "iron-laws.yml"
            yaml_path.write_text(
                textwrap.dedent(
                    """
                    version: "1"
                    last_updated: "2026-04-02"
                    total_laws: 1
                    categories:
                      - id: data
                        name: Data
                        law_count: ~
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
        self.assertIn("category[0] missing: law_count", result.stderr)

    def test_generate_iron_law_content_rejects_invalid_preference_severity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            prefs_path = tmp / "preferences.yml"
            prefs_path.write_text(
                textwrap.dedent(
                    """
                    version: "1.0"
                    last_updated: "2026-04-18"
                    total_preferences: 1
                    categories:
                      - id: research
                        name: Research
                        preference_count: 1
                    preferences:
                      - id: 1
                        category: research
                        title: Example
                        rule: Do this
                        rationale: Because
                        summary_text: Short
                        subagent_text: Short
                        severity: critical
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["RUBY_PLUGIN_PREFERENCES_YAML"] = str(prefs_path)
            result = subprocess.run(
                ["ruby", str(GENERATE_IRON_LAW_CONTENT), "preferences_injectable"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn('severity="critical" not in', result.stderr)

    def test_generate_iron_law_content_rejects_preference_unknown_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            prefs_path = tmp / "preferences.yml"
            prefs_path.write_text(
                textwrap.dedent(
                    """
                    version: "1.0"
                    last_updated: "2026-04-18"
                    total_preferences: 1
                    categories:
                      - id: research
                        name: Research
                        preference_count: 1
                    preferences:
                      - id: 1
                        category: nonexistent
                        title: Example
                        rule: Do this
                        rationale: Because
                        summary_text: Short
                        subagent_text: Short
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["RUBY_PLUGIN_PREFERENCES_YAML"] = str(prefs_path)
            result = subprocess.run(
                ["ruby", str(GENERATE_IRON_LAW_CONTENT), "preferences_injectable"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("references unknown category", result.stderr)

    def test_generate_iron_law_content_rejects_preference_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            prefs_path = tmp / "preferences.yml"
            prefs_path.write_text(
                textwrap.dedent(
                    """
                    version: "1.0"
                    last_updated: "2026-04-18"
                    total_preferences: 2
                    categories:
                      - id: research
                        name: Research
                        preference_count: 1
                    preferences:
                      - id: 1
                        category: research
                        title: Example
                        rule: Do this
                        rationale: Because
                        summary_text: Short
                        subagent_text: Short
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["RUBY_PLUGIN_PREFERENCES_YAML"] = str(prefs_path)
            result = subprocess.run(
                ["ruby", str(GENERATE_IRON_LAW_CONTENT), "preferences_injectable"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("total_preferences=2 does not match actual preferences count=1", result.stderr)

    def test_generate_iron_law_content_fails_when_preferences_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "does-not-exist.yml"
            env = dict(os.environ)
            env["RUBY_PLUGIN_PREFERENCES_YAML"] = str(missing)
            result = subprocess.run(
                ["ruby", str(GENERATE_IRON_LAW_CONTENT), "preferences_injectable"],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=False,
                env=env,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("preferences.yml source not found", result.stderr)
        self.assertIn("RUBY_PLUGIN_PREFERENCES_YAML", result.stderr)

    def test_generate_iron_law_content_preferences_injectable_happy_path(self) -> None:
        result = subprocess.run(
            ["ruby", str(GENERATE_IRON_LAW_CONTENT), "preferences_injectable"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("## Advisory Preferences", result.stdout)
        self.assertIn("Apply when possible", result.stdout)
        self.assertIn("Context7 MCP", result.stdout)

    def test_generate_iron_law_outputs_help_succeeds(self) -> None:
        result = subprocess.run(
            ["bash", str(GENERATE_IRON_LAW_OUTPUTS), "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Regenerate Iron Law", result.stdout)
        self.assertIn("preferences.yml", result.stdout)
        self.assertNotIn("claude", result.stdout)
        self.assertNotIn("changelog", result.stdout.lower())

    def test_iron_law_generation_targets_do_not_reference_removed_outputs(self) -> None:
        yaml_text = (
            REPO_ROOT / "plugins/ruby-grape-rails/references/iron-laws.yml"
        ).read_text(encoding="utf-8")

        self.assertNotIn('file: "CHANGELOG.md"', yaml_text)


if __name__ == "__main__":
    unittest.main()
