from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".claude"
    / "skills"
    / "session-scan"
    / "references"
    / "scan-sessions.py"
)

if not MODULE_PATH.exists():
    raise ImportError(f"Cannot find 'session_scan_orchestrator' at {MODULE_PATH}")

SPEC = importlib.util.spec_from_file_location("session_scan_orchestrator", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Cannot load 'session_scan_orchestrator' from {MODULE_PATH}")
session_scan_orchestrator = importlib.util.module_from_spec(SPEC)
try:
    SPEC.loader.exec_module(session_scan_orchestrator)
except OSError as exc:
    raise ImportError(
        f"Cannot execute 'session_scan_orchestrator' from {MODULE_PATH}"
    ) from exc


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


if __name__ == "__main__":
    unittest.main()
