from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".claude"
    / "skills"
    / "session-scan"
    / "references"
    / "compute-metrics.py"
)

if not MODULE_PATH.exists():
    raise ImportError(f"Cannot find 'session_scan_metrics' at {MODULE_PATH}")

SPEC = importlib.util.spec_from_file_location("session_scan_metrics", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Cannot load 'session_scan_metrics' from {MODULE_PATH}")
session_scan_metrics = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(session_scan_metrics)
except OSError as exc:
    raise ImportError(f"Cannot execute 'session_scan_metrics' from {MODULE_PATH}") from exc


class SessionScanMetricTests(unittest.TestCase):
    def test_extract_plugin_commands_normalizes_aliases(self) -> None:
        user_msgs = [
            "Use /rb:verify next",
            "Then try /ruby-grape-rails:permissions",
        ]

        commands = session_scan_metrics.extract_plugin_commands(user_msgs)

        self.assertEqual(commands, ["/rb:verify", "/rb:permissions"])

    def test_extract_plugin_commands_ignores_placeholders(self) -> None:
        user_msgs = [
            "Template: /rb:{command}",
            "Placeholder: /ruby-grape-rails:<skill>",
            "Real: /rb:plan",
        ]

        commands = session_scan_metrics.extract_plugin_commands(user_msgs)

        self.assertEqual(commands, ["/rb:plan"])

    def test_locate_skill_invocations_normalizes_aliases(self) -> None:
        messages = [
            {
                "role": "user",
                "content": (
                    "<command-message>ruby-grape-rails:permissions</command-message>\n"
                    "<command-name>/ruby-grape-rails:permissions</command-name>"
                ),
            }
        ]

        invocations = session_scan_metrics._locate_skill_invocations([], messages)

        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0]["skill"], "/rb:permissions")

    def test_compute_plugin_opportunity_accepts_prefixed_commands(self) -> None:
        messages = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "bundle exec rspec spec/models/user_spec.rb"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_result", "is_error": True, "content": "failed with exit code 1"}],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "bundle exec rspec spec/models/user_spec.rb"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_result", "is_error": True, "content": "failed with exit code 1"}],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "bundle exec rspec spec/models/user_spec.rb"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_result", "is_error": True, "content": "failed with exit code 1"}],
            },
        ]
        tool_calls = [
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/models/user_spec.rb"}},
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/models/user_spec.rb"}},
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/models/user_spec.rb"}},
        ]

        score, could_use = session_scan_metrics.compute_plugin_opportunity(
            [],
            tool_calls,
            ["/ruby-grape-rails:verify", "/rb:plan"],
            messages,
        )

        self.assertEqual(score, 0.2)
        self.assertEqual(could_use, ["investigate"])

    def test_compute_plugin_opportunity_skips_investigate_when_already_used(self) -> None:
        messages = [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "bundle exec rspec spec/models/user_spec.rb"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_result", "is_error": True, "content": "failed with exit code 1"}],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "bundle exec rspec spec/models/user_spec.rb"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_result", "is_error": True, "content": "failed with exit code 1"}],
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "bundle exec rspec spec/models/user_spec.rb"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "tool_result", "is_error": True, "content": "failed with exit code 1"}],
            },
        ]
        tool_calls = [
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/models/user_spec.rb"}},
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/models/user_spec.rb"}},
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/models/user_spec.rb"}},
        ]

        score, could_use = session_scan_metrics.compute_plugin_opportunity(
            [],
            tool_calls,
            ["/rb:verify", "/rb:investigate"],
            messages,
        )

        self.assertEqual(score, 0.0)
        self.assertEqual(could_use, [])

    def test_skill_effectiveness_counts_text_mode_bash_runs(self) -> None:
        messages = [
            {
                "role": "user",
                "content": (
                    "<command-message>ruby-grape-rails:verify</command-message>\n"
                    "<command-name>/ruby-grape-rails:verify</command-name>"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "```bash\n"
                    "$ bundle exec rspec spec/models/user_spec.rb\n"
                    "```"
                ),
            },
        ]

        results = session_scan_metrics.compute_skill_effectiveness([], [], [], messages)

        self.assertIn("/rb:verify", results)
        self.assertEqual(results["/rb:verify"]["total_post_test_runs"], 1)

    def test_extract_tool_positions_ignores_plain_agent_prose(self) -> None:
        messages = [{"role": "assistant", "content": "We should ask the Agent to summarize this."}]

        tool_positions = session_scan_metrics.extract_tool_positions(messages)

        self.assertEqual(tool_positions, [])

    def test_extract_tool_positions_matches_tool_like_text_forms(self) -> None:
        messages = [
            {
                "role": "assistant",
                "content": "Use `Task` for discovery, then Agent(task=\"scan\") and tool:Bash if needed.",
            }
        ]

        tool_positions = session_scan_metrics.extract_tool_positions(messages)

        self.assertEqual(
            [item["tc"]["name"] for item in tool_positions],
            ["Task", "Agent", "Bash"],
        )

    def test_compute_trends_keeps_latest_entry_per_session(self) -> None:
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir) / "metrics.jsonl"
            entries = [
                {
                    "session_id": "session-a",
                    "scanned_at": (now.replace(microsecond=0)).isoformat(),
                    "provider": "claude",
                    "project": "alpha",
                    "date": now.date().isoformat(),
                    "friction_score": 0.1,
                    "plugin_opportunity_score": 0.1,
                    "fingerprint": "exploration",
                    "tier2_eligible": False,
                    "plugin_signals": {"rb_commands_used": []},
                },
                {
                    "session_id": "session-b",
                    "scanned_at": (now.replace(microsecond=0)).isoformat(),
                    "provider": "claude",
                    "project": "beta",
                    "date": now.date().isoformat(),
                    "friction_score": 0.3,
                    "plugin_opportunity_score": 0.2,
                    "fingerprint": "feature",
                    "tier2_eligible": False,
                    "plugin_signals": {"rb_commands_used": []},
                },
                {
                    "session_id": "session-a",
                    "scanned_at": (now.replace(microsecond=0)).isoformat(),
                    "provider": "claude",
                    "project": "alpha",
                    "date": now.date().isoformat(),
                    "friction_score": 0.9,
                    "plugin_opportunity_score": 0.4,
                    "fingerprint": "bug-fix",
                    "tier2_eligible": True,
                    "plugin_signals": {"rb_commands_used": ["/rb:investigate"]},
                },
            ]
            with metrics_path.open("w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")

            trends = session_scan_metrics.compute_trends(str(metrics_path))

        self.assertEqual(trends["total_sessions"], 2)
        self.assertEqual(trends["windows"]["all"]["count"], 2)
        self.assertEqual(trends["windows"]["all"]["avg_friction"], 0.6)
        self.assertEqual(trends["windows"]["all"]["tier2_eligible_count"], 1)

    def test_load_messages_from_db_expands_user_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir) / "db dir"
            db_dir.mkdir()
            db_path = db_dir / "sessions.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                (
                    "CREATE TABLE sessions ("
                    "id INTEGER PRIMARY KEY, "
                    "session_id TEXT NOT NULL, "
                    "project_path TEXT, "
                    "provider TEXT, "
                    "updated_at TEXT)"
                )
            )
            conn.execute(
                "CREATE TABLE messages (session_id INTEGER NOT NULL, sequence INTEGER NOT NULL, content TEXT)"
            )
            conn.execute(
                (
                    "INSERT INTO sessions (id, session_id, project_path, provider, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (1, "session-1", "/tmp/app", "claude", "2026-04-21T17:00:00Z"),
            )
            conn.execute(
                "INSERT INTO messages (session_id, sequence, content) VALUES (?, ?, ?)",
                (1, 1, json.dumps({"role": "user", "content": "hello"})),
            )
            conn.commit()
            conn.close()

            with mock.patch.dict(os.environ, {"HOME": tmpdir}, clear=False):
                messages = session_scan_metrics.load_messages_from_db(
                    "~/db dir/sessions.db", "session-1"
                )

        self.assertEqual(messages, [{"role": "user", "content": "hello"}])

    def test_load_session_data_from_db_uses_session_metadata_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                (
                    "CREATE TABLE sessions ("
                    "id INTEGER PRIMARY KEY, "
                    "session_id TEXT NOT NULL, "
                    "project_path TEXT, "
                    "provider TEXT, "
                    "updated_at TEXT)"
                )
            )
            conn.execute(
                "CREATE TABLE messages (session_id INTEGER NOT NULL, sequence INTEGER NOT NULL, content TEXT)"
            )
            conn.execute(
                (
                    "INSERT INTO sessions (id, session_id, project_path, provider, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (
                    1,
                    "session-1",
                    "/tmp/my-app",
                    "claude",
                    "2026-04-21T17:00:00Z",
                ),
            )
            conn.execute(
                "INSERT INTO messages (session_id, sequence, content) VALUES (?, ?, ?)",
                (1, 1, json.dumps({"role": "user", "content": "hello"})),
            )
            conn.commit()
            conn.close()

            messages, metadata = session_scan_metrics.load_session_data_from_db(
                str(db_path), "session-1"
            )

        self.assertEqual(messages, [{"role": "user", "content": "hello"}])
        self.assertEqual(metadata["project"], "my-app")
        self.assertEqual(metadata["provider"], "claude")
        self.assertEqual(metadata["date"], "2026-04-21")

    def test_load_session_data_from_db_raises_when_all_rows_are_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                (
                    "CREATE TABLE sessions ("
                    "id INTEGER PRIMARY KEY, "
                    "session_id TEXT NOT NULL, "
                    "project_path TEXT, "
                    "provider TEXT, "
                    "updated_at TEXT)"
                )
            )
            conn.execute(
                "CREATE TABLE messages (session_id INTEGER NOT NULL, sequence INTEGER NOT NULL, content TEXT)"
            )
            conn.execute(
                (
                    "INSERT INTO sessions (id, session_id, project_path, provider, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)"
                ),
                (1, "session-1", "/tmp/my-app", "claude", "2026-04-21T17:00:00Z"),
            )
            conn.execute(
                "INSERT INTO messages (session_id, sequence, content) VALUES (?, ?, ?)",
                (1, 1, "{not json"),
            )
            conn.commit()
            conn.close()

            with self.assertRaises(ValueError):
                session_scan_metrics.load_session_data_from_db(
                    str(db_path), "session-1"
                )

    def test_load_session_data_from_db_rejects_directory_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "not a file"):
                session_scan_metrics.load_session_data_from_db(tmpdir, "session-1")


if __name__ == "__main__":
    unittest.main()
