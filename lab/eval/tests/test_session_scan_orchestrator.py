import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".claude"
    / "skills"
    / "session-scan"
    / "references"
    / "scan-sessions.py"
)
MODULE_FILENAME = MODULE_PATH.name
MODULE_IMPORT_NAME = "scan_sessions"

if not MODULE_PATH.exists():
    raise ImportError(f"Cannot find '{MODULE_FILENAME}' at {MODULE_PATH}")

SPEC = importlib.util.spec_from_file_location(MODULE_IMPORT_NAME, MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Cannot load '{MODULE_FILENAME}' from {MODULE_PATH}")
session_scan_orchestrator = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(session_scan_orchestrator)
except OSError as exc:
    raise ImportError(f"Cannot execute '{MODULE_FILENAME}' from {MODULE_PATH}") from exc


class SessionScanOrchestratorTests(unittest.TestCase):
    def test_load_scoring_module_exits_when_spec_has_no_loader(self) -> None:
        spec_without_loader = mock.Mock(loader=None)

        with mock.patch.object(
            session_scan_orchestrator.importlib.util,
            "spec_from_file_location",
            return_value=spec_without_loader,
        ):
            with self.assertRaises(SystemExit) as exc:
                session_scan_orchestrator.load_scoring_module()

        self.assertIn("unable to load scorer module", str(exc.exception))

    def test_main_closes_connection_in_list_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            metrics_dir = Path(tmpdir) / "metrics"
            conn = mock.Mock()

            with mock.patch.object(
                session_scan_orchestrator, "open_db_readonly", return_value=conn
            ), mock.patch.object(
                session_scan_orchestrator, "discover_sessions", return_value=[]
            ), mock.patch.object(
                session_scan_orchestrator, "format_list_table", return_value="No rows"
            ):
                rc = session_scan_orchestrator.main(
                    ["--db", str(db_path), "--metrics-dir", str(metrics_dir), "--list"]
                )

        self.assertEqual(rc, 0)
        conn.close.assert_called_once()

    def test_main_list_mode_does_not_create_metrics_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            metrics_dir = Path(tmpdir) / "metrics"
            conn = mock.Mock()

            with mock.patch.object(
                session_scan_orchestrator, "open_db_readonly", return_value=conn
            ), mock.patch.object(
                session_scan_orchestrator, "discover_sessions", return_value=[]
            ), mock.patch.object(
                session_scan_orchestrator, "format_list_table", return_value="No rows"
            ):
                rc = session_scan_orchestrator.main(
                    ["--db", str(db_path), "--metrics-dir", str(metrics_dir), "--list"]
                )

            self.assertEqual(rc, 0)
            self.assertFalse(metrics_dir.exists())

    def test_open_db_readonly_handles_paths_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_dir = Path(tmpdir) / "db dir"
            db_dir.mkdir()
            db_path = db_dir / "sessions.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE sessions (id INTEGER PRIMARY KEY, session_id TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO sessions (id, session_id) VALUES (?, ?)",
                (1, "session-1"),
            )
            conn.commit()
            conn.close()

            readonly = session_scan_orchestrator.open_db_readonly(db_path)
            try:
                row = readonly.execute(
                    "SELECT session_id FROM sessions WHERE id = 1"
                ).fetchone()
            finally:
                readonly.close()

        self.assertEqual(row["session_id"], "session-1")

    def test_load_session_messages_reports_decode_failures(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "session_id INTEGER NOT NULL, sequence INTEGER NOT NULL, "
                "content TEXT, text_content TEXT, type TEXT, sender TEXT)"
            )
            conn.execute(
                "INSERT INTO messages "
                "(session_id, sequence, content, text_content, type, sender) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (1, 1, '{"role":"user","content":"ok"}', "ok", "user", "human"),
            )
            conn.execute(
                "INSERT INTO messages "
                "(session_id, sequence, content, text_content, type, sender) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (1, 2, "{bad json", "", "assistant", "assistant"),
            )
            conn.commit()

            messages, decode_failures, candidate_rows, synthesized = (
                session_scan_orchestrator.load_session_messages(conn, 1)
            )
        finally:
            conn.close()

        self.assertEqual(messages, [{"role": "user", "content": "ok"}])
        self.assertEqual(decode_failures, 1)
        self.assertEqual(candidate_rows, 2)
        self.assertEqual(synthesized, 0)

    def test_load_session_messages_reconstructs_codex_rows_from_text_content(
        self,
    ) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute(
                "CREATE TABLE messages ("
                "session_id INTEGER NOT NULL, sequence INTEGER NOT NULL, "
                "content TEXT, text_content TEXT, type TEXT, sender TEXT)"
            )
            # Codex sessions leave content empty; only text_content is populated.
            conn.execute(
                "INSERT INTO messages "
                "(session_id, sequence, content, text_content, type, sender) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (1, 1, None, "hello from user", "user", "human"),
            )
            conn.execute(
                "INSERT INTO messages "
                "(session_id, sequence, content, text_content, type, sender) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (1, 2, "", "response body", "assistant", "assistant"),
            )
            conn.commit()

            messages, decode_failures, candidate_rows, synthesized = (
                session_scan_orchestrator.load_session_messages(conn, 1)
            )
        finally:
            conn.close()

        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "hello from user"},
                {"role": "assistant", "content": "response body"},
            ],
        )
        self.assertEqual(decode_failures, 0)
        self.assertEqual(candidate_rows, 2)
        self.assertEqual(synthesized, 2)

    def test_reconstruct_message_statuses(self) -> None:
        ok_msg, ok_status = session_scan_orchestrator.reconstruct_message(
            '{"role":"user","content":"hi"}', "hi", "user", "human"
        )
        synth_msg, synth_status = session_scan_orchestrator.reconstruct_message(
            None, "text only", "assistant", "assistant"
        )
        fallback_msg, fallback_status = session_scan_orchestrator.reconstruct_message(
            "{bad", "recovered", "user", "human"
        )
        fail_msg, fail_status = session_scan_orchestrator.reconstruct_message(
            "{bad", "", "user", "human"
        )
        empty_msg, empty_status = session_scan_orchestrator.reconstruct_message(
            None, "   ", "user", "human"
        )

        self.assertEqual(ok_status, "ok")
        self.assertEqual(ok_msg, {"role": "user", "content": "hi"})
        self.assertEqual(synth_status, "synth")
        self.assertEqual(synth_msg, {"role": "assistant", "content": "text only"})
        self.assertEqual(fallback_status, "synth")
        self.assertEqual(fallback_msg, {"role": "user", "content": "recovered"})
        self.assertEqual(fail_status, "decode_failed")
        self.assertIsNone(fail_msg)
        self.assertEqual(empty_status, "empty")
        self.assertIsNone(empty_msg)

    def test_main_returns_nonzero_on_partial_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            metrics_dir = Path(tmpdir) / "metrics"
            conn = mock.Mock()
            scorer = mock.Mock()
            scorer.compute_session_metrics.side_effect = [
                {
                    "session_id": "session-1",
                    "friction_score": 0.1,
                    "fingerprint": "feature",
                    "plugin_opportunity_score": 0.0,
                    "tier2_eligible": False,
                },
                RuntimeError("boom"),
            ]
            rows = [
                {
                    "id": 1,
                    "session_id": "session-1",
                    "project_path": "/tmp/app",
                    "provider": "claude",
                    "updated_at": "2026-04-21T17:00:00Z",
                },
                {
                    "id": 2,
                    "session_id": "session-2",
                    "project_path": "/tmp/app",
                    "provider": "claude",
                    "updated_at": "2026-04-21T17:01:00Z",
                },
            ]

            with mock.patch.object(
                session_scan_orchestrator, "open_db_readonly", return_value=conn
            ), mock.patch.object(
                session_scan_orchestrator,
                "discover_sessions",
                side_effect=[rows, rows],
            ), mock.patch.object(
                session_scan_orchestrator, "load_scoring_module", return_value=scorer
            ), mock.patch.object(
                session_scan_orchestrator,
                "load_session_messages",
                side_effect=[
                    ([{"role": "user", "content": "ok"}], 0, 1, 0),
                    ([{"role": "user", "content": "still ok"}], 0, 1, 0),
                ],
            ):
                rc = session_scan_orchestrator.main(
                    ["--db", str(db_path), "--metrics-dir", str(metrics_dir), "--limit", "2"]
                )

        self.assertEqual(rc, 1)

    def test_collect_unscanned_sessions_paginates_past_scanned_rows(self) -> None:
        conn = mock.Mock()
        page_one = [{"session_id": f"session-{i}"} for i in range(1, 51)]
        page_two = [
            {"session_id": "session-51"},
            {"session_id": "session-52"},
        ]

        with mock.patch.object(
            session_scan_orchestrator,
            "discover_sessions",
            side_effect=[page_one, page_two],
        ):
            collected, skipped = session_scan_orchestrator.collect_unscanned_sessions(
                conn,
                since="2026-04-14",
                project=None,
                provider=None,
                limit=2,
                min_messages=5,
                ledger_ids={row["session_id"] for row in page_one},
            )

        self.assertEqual(
            [row["session_id"] for row in collected],
            ["session-51", "session-52"],
        )
        self.assertEqual(skipped, 50)

    def test_main_uses_ledger_view_when_no_new_sessions_scored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            metrics_dir = Path(tmpdir) / "metrics"
            metrics_dir.mkdir()
            metrics_path = metrics_dir / "metrics.jsonl"
            metrics_path.write_text(
                (
                    '{"session_id":"session-1","project":"/tmp/app","provider":"claude",'
                    '"date":"2026-04-21","friction_score":0.6,'
                    '"plugin_opportunity_score":0.1,"fingerprint":"bug-fix",'
                    '"tier2_eligible":true,"plugin_signals":{"rb_commands_used":[]}}\n'
                ),
                encoding="utf-8",
            )
            conn = mock.Mock()
            rows = [
                {
                    "id": 1,
                    "session_id": "session-1",
                    "project_path": "/tmp/app",
                    "provider": "claude",
                    "updated_at": "2026-04-21T17:00:00Z",
                }
            ]

            with mock.patch.object(
                session_scan_orchestrator, "open_db_readonly", return_value=conn
            ), mock.patch.object(
                session_scan_orchestrator,
                "discover_sessions",
                side_effect=[rows, rows, []],
            ), mock.patch.object(
                session_scan_orchestrator, "load_scoring_module", return_value=mock.Mock()
            ):
                rc = session_scan_orchestrator.main(
                    ["--db", str(db_path), "--metrics-dir", str(metrics_dir), "--limit", "1"]
                )

            latest_scan = json.loads(
                (metrics_dir / "latest-scan.json").read_text(encoding="utf-8")
            )

        self.assertEqual(rc, 0)
        self.assertEqual(latest_scan["sessions_scanned"], 0)
        self.assertEqual(latest_scan["sessions_in_view"], 1)
        self.assertEqual(latest_scan["tier2_eligible"], 1)
        self.assertEqual(latest_scan["view_session_ids"], ["session-1"])

    def test_build_current_view_entries_prefers_latest_scanned_at(self) -> None:
        rows = [{"session_id": "session-a"}, {"session_id": "session-b"}]
        latest_entries = {
            "session-a": {
                "session_id": "session-a",
                "date": "2026-04-21",
                "scanned_at": "2026-04-21T10:00:00+00:00",
            },
            "session-b": {
                "session_id": "session-b",
                "date": "2026-04-22",
                "scanned_at": "2026-04-21T12:00:00+00:00",
            },
        }

        entries = session_scan_orchestrator.build_current_view_entries(
            rows, latest_entries
        )

        self.assertEqual(
            [entry["session_id"] for entry in entries],
            ["session-b", "session-a"],
        )

    def test_parse_since_accepts_iso_date(self) -> None:
        self.assertEqual(
            session_scan_orchestrator.parse_since("2026-04-21"), "2026-04-21"
        )

    def test_parse_since_accepts_iso_datetime_with_z(self) -> None:
        self.assertEqual(
            session_scan_orchestrator.parse_since("2026-04-21T12:00:00Z"),
            "2026-04-21T12:00:00+00:00",
        )

    def test_parse_since_rejects_invalid_value(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
            session_scan_orchestrator.parse_since("last week")
        self.assertEqual(exc.exception.code, 1)
        self.assertIn("invalid --since", stderr.getvalue())

    def test_parse_since_rejects_blank_string(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
            session_scan_orchestrator.parse_since("   ")
        self.assertEqual(exc.exception.code, 1)
        self.assertIn("ISO-8601", stderr.getvalue())

    def test_min_messages_rejects_non_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                session_scan_orchestrator.main(
                    ["--db", str(db_path), "--min-messages", "0"]
                )
            self.assertEqual(exc.exception.code, 2)

    def test_resolve_db_rejects_directory_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
                session_scan_orchestrator.resolve_db(tmpdir)

        self.assertEqual(exc.exception.code, 2)
        self.assertIn("not a file", stderr.getvalue())

    def test_main_reports_sqlite_errors_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            stderr = io.StringIO()

            with redirect_stderr(stderr), mock.patch.object(
                session_scan_orchestrator,
                "open_db_readonly",
                side_effect=sqlite3.DatabaseError("file is not a database"),
            ):
                rc = session_scan_orchestrator.main(["--db", str(db_path)])

        self.assertEqual(rc, 1)
        self.assertIn("failed to read ccrider DB", stderr.getvalue())

    def test_resolve_db_expands_env_vars(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")

            with mock.patch.dict(
                session_scan_orchestrator.os.environ,
                {"TEST_DB_ROOT": tmpdir},
                clear=False,
            ):
                resolved = session_scan_orchestrator.resolve_db(
                    "$TEST_DB_ROOT/sessions.db"
                )

        self.assertEqual(resolved, db_path)

    def test_default_db_candidates_expand_env_vars(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home_dir = Path(tmpdir) / "home"
            home_dir.mkdir()
            expected_db = home_dir / ".config" / "ccrider" / "sessions.db"

            with mock.patch.object(
                session_scan_orchestrator.Path,
                "home",
                return_value=home_dir,
            ), mock.patch.dict(
                session_scan_orchestrator.os.environ,
                {"CCRIDER_DB": "$HOME/.config/ccrider/sessions.db"},
                clear=False,
            ), mock.patch.dict(
                "os.environ",
                {"HOME": str(home_dir)},
                clear=False,
            ):
                candidates = session_scan_orchestrator.default_db_candidates()

        self.assertEqual(candidates[0], expected_db)

    def test_main_surfaces_backfilled_sessions_in_view(self) -> None:
        """Sessions scored via pagination must appear in triage + latest-scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "sessions.db"
            db_path.write_text("", encoding="utf-8")
            metrics_dir = Path(tmpdir) / "metrics"
            conn = mock.Mock()
            scorer = mock.Mock()
            scorer.compute_session_metrics.side_effect = [
                {
                    "session_id": "backfilled-1",
                    "scanned_at": "2026-04-21T17:02:00+00:00",
                    "friction_score": 0.8,
                    "fingerprint": "bug-fix",
                    "plugin_opportunity_score": 0.1,
                    "tier2_eligible": True,
                    "provider": "claude",
                    "project": "/tmp/app",
                    "date": "2026-04-21",
                },
            ]
            top_rows = [
                {
                    "id": 1,
                    "session_id": "known-1",
                    "project_path": "/tmp/app",
                    "provider": "claude",
                    "updated_at": "2026-04-21T17:00:00Z",
                },
            ]
            deeper_rows = [
                {
                    "id": 2,
                    "session_id": "backfilled-1",
                    "project_path": "/tmp/app",
                    "provider": "claude",
                    "updated_at": "2026-04-20T10:00:00Z",
                },
            ]
            metrics_dir.mkdir(parents=True, exist_ok=True)
            (metrics_dir / "metrics.jsonl").write_text(
                '{"session_id":"known-1","scanned_at":"2026-04-21T16:00:00+00:00",'
                '"friction_score":0.1,"fingerprint":"feature",'
                '"plugin_opportunity_score":0.0,"tier2_eligible":false,'
                '"provider":"claude","project":"/tmp/app","date":"2026-04-21"}\n',
                encoding="utf-8",
            )

            all_rows = top_rows + deeper_rows

            def discover_side_effect(*_args, **kwargs):
                # main() initial call uses --limit (1) for the visible top.
                # collect_unscanned_sessions calls with page_size >= 50 to
                # backfill past skipped top-N rows; simulate ccrider returning
                # every matching session on the first page.
                limit = kwargs.get("limit", 1)
                offset = kwargs.get("offset", 0)
                return all_rows[offset : offset + limit]

            with mock.patch.object(
                session_scan_orchestrator, "open_db_readonly", return_value=conn
            ), mock.patch.object(
                session_scan_orchestrator,
                "discover_sessions",
                side_effect=discover_side_effect,
            ), mock.patch.object(
                session_scan_orchestrator, "load_scoring_module", return_value=scorer
            ), mock.patch.object(
                session_scan_orchestrator,
                "load_session_messages",
                return_value=(
                    [{"role": "user", "content": "ok"}],
                    0,
                    1,
                    0,
                ),
            ):
                rc = session_scan_orchestrator.main(
                    [
                        "--db",
                        str(db_path),
                        "--metrics-dir",
                        str(metrics_dir),
                        "--limit",
                        "1",
                    ]
                )

            self.assertEqual(rc, 0)
            latest_scan = json.loads(
                (metrics_dir / "latest-scan.json").read_text(encoding="utf-8")
            )
            self.assertIn("backfilled-1", latest_scan["view_session_ids"])
            self.assertIn("backfilled-1", latest_scan["tier2_session_ids"])
            self.assertIn("known-1", latest_scan["view_session_ids"])


if __name__ == "__main__":
    unittest.main()
