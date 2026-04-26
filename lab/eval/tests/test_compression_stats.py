"""Subprocess-driven test for the compression-stats Ruby CLI reader.

The reader is the operator surface for the dry-run telemetry shipped with
the verify-output compression collector. These tests exercise the JSON
output mode against a synthetic jsonl payload."""

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "plugins" / "ruby-grape-rails" / "bin" / "compression-stats"


def _run(jsonl_path: Path) -> dict:
    proc = subprocess.run(
        [str(CLI), "--log", str(jsonl_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_no_log_file_returns_nonzero(tmp_path: Path) -> None:
    proc = subprocess.run(
        [str(CLI), "--log", str(tmp_path / "nope.jsonl"), "--json"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1


def test_classifies_and_aggregates(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entries = [
        {"ts": 1.0, "cmd": "rspec spec/foo", "raw_bytes": 1000, "compressed_bytes": 300, "ratio": 0.7, "violations": [], "raw_log": None},
        {"ts": 2.0, "cmd": "rspec spec/bar", "raw_bytes": 2000, "compressed_bytes": 600, "ratio": 0.7, "violations": [], "raw_log": None},
        {"ts": 3.0, "cmd": "bundle exec rubocop", "raw_bytes": 500, "compressed_bytes": 400, "ratio": 0.2, "violations": [], "raw_log": None},
        {"ts": 4.0, "cmd": "RAILS_ENV=test bundle exec rails db:migrate", "raw_bytes": 800, "compressed_bytes": 200, "ratio": 0.75, "violations": [], "raw_log": None},
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    payload = _run(log)
    assert payload["samples"] == 4
    assert payload["preservation_violations"] == 0
    assert set(payload["by_class"].keys()) == {"rspec", "rubocop", "migration"}
    assert payload["by_class"]["rspec"]["count"] == 2
    assert abs(payload["by_class"]["rspec"]["mean"] - 0.7) < 1e-6
    assert payload["recommendation"].startswith("keep-collecting")


def test_flags_preservation_violations(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entries = [
        {"ts": 1.0, "cmd": "rspec", "raw_bytes": 100, "compressed_bytes": 50, "ratio": 0.5, "violations": ["dropped foo"], "raw_log": None},
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    payload = _run(log)
    assert payload["preservation_violations"] == 1
    assert "preservation-violations" in payload["recommendation"]


def test_top_weak_samples(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entries = [
        {"ts": float(i), "cmd": f"rspec spec/x{i}", "raw_bytes": 100, "compressed_bytes": 95, "ratio": 0.05, "violations": [], "raw_log": None}
        for i in range(5)
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    payload = _run(log)
    assert len(payload["weak_samples"]) == 5
    for sample in payload["weak_samples"]:
        assert sample["ratio"] < 0.20


def test_corrupt_jsonl_lines_skipped(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    good = json.dumps({"ts": 1.0, "cmd": "rspec", "raw_bytes": 10, "compressed_bytes": 5, "ratio": 0.5, "violations": [], "raw_log": None})
    log.write_text("\n".join([good, "{not-json", "", good]) + "\n")

    payload = _run(log)
    assert payload["samples"] == 2


def _run_redact(jsonl_path: Path) -> dict:
    proc = subprocess.run(
        [str(CLI), "--log", str(jsonl_path), "--redact"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_redact_strips_env_values_and_paths(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entry = {
        "ts": 1.0,
        "cmd": "RAILS_ENV=production SECRET_KEY=abcdef rspec spec/models/user_spec.rb",
        "raw_bytes": 1000,
        "compressed_bytes": 100,
        "ratio": 0.05,
        "violations": [],
        "raw_log": "/data/cache/plugins/verify-raw/uuid-1.log",
    }
    log.write_text(json.dumps(entry) + "\n")

    payload = _run_redact(log)
    assert payload["redaction_applied"] is True
    weak = payload["weak_samples"][0]
    assert "production" not in weak["cmd"]
    assert "abcdef" not in weak["cmd"]
    assert "user_spec.rb" not in weak["cmd"]
    assert "rspec" in weak["cmd"]  # verb preserved for classification
    assert "RAILS_ENV=<v>" in weak["cmd"]
    assert weak["raw_log_id"] == "uuid-1"
    assert "/data/cache" not in json.dumps(payload)


def test_redact_drops_violation_message_strings(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entry = {
        "ts": 1.0,
        "cmd": "bundle exec rubocop",
        "raw_bytes": 500,
        "compressed_bytes": 400,
        "ratio": 0.2,
        "violations": ["dropped /data/private/file.rb:42"],
        "raw_log": "/data/cache/plugins/verify-raw/uuid-2.log",
    }
    log.write_text(json.dumps(entry) + "\n")

    payload = _run_redact(log)
    assert payload["preservation_violations"] == 1
    sample = payload["violation_samples"][0]
    assert sample["violation_count"] == 1
    assert "private/file.rb" not in json.dumps(payload)
    assert "/data/private" not in json.dumps(payload)
    assert sample["raw_log_id"] == "uuid-2"


def test_redact_drops_trailing_freeform_args(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entry = {
        "ts": 1.0,
        "cmd": "bundle exec rubocop -- /repo/myapp/lib/foo.rb /repo/myapp/lib/bar.rb",
        "raw_bytes": 200,
        "compressed_bytes": 190,
        "ratio": 0.05,
        "violations": [],
        "raw_log": None,
    }
    log.write_text(json.dumps(entry) + "\n")

    payload = _run_redact(log)
    assert "/repo/myapp" not in json.dumps(payload)
    assert "myapp" not in json.dumps(payload)


def test_redact_omits_absolute_paths(tmp_path: Path) -> None:
    """--redact JSON must carry no absolute path components.

    Specifically the raw-log directory under ${CLAUDE_PLUGIN_DATA}
    contains the user's home dir on real installs; pasting redacted
    JSON into a public GitHub issue must not leak it. Consumers that
    need to Read raw logs reconstruct the path locally from the
    inline-substituted ${CLAUDE_PLUGIN_DATA}, never from --redact
    output.
    """
    log = tmp_path / "compression.jsonl"
    entry = {
        "ts": 1.0,
        "cmd": "rspec",
        "raw_bytes": 100,
        "compressed_bytes": 30,
        "ratio": 0.7,
        "violations": [],
        "raw_log": "/data/cache/plugins/verify-raw/uuid-1.log",
    }
    log.write_text(json.dumps(entry) + "\n")

    payload = _run_redact(log)
    assert "raw_log_dir" not in payload
    blob = json.dumps(payload)
    assert "/data/cache" not in blob
    # Generic absolute-path guard. Catches any value starting with `/`
    # followed by an alphanumeric segment that looks like a real
    # filesystem path (excluding pure-id basenames like `/uuid-1`).
    import re
    assert not re.search(r'"/(?:Users|home|var|opt|data|repo)/', blob), (
        f"redacted JSON contains an absolute path-shaped value: {blob}"
    )


def test_redact_keeps_aggregate_stats(tmp_path: Path) -> None:
    log = tmp_path / "compression.jsonl"
    entries = [
        {"ts": float(i), "cmd": "rspec", "raw_bytes": 100, "compressed_bytes": 30, "ratio": 0.7, "violations": [], "raw_log": None}
        for i in range(5)
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    payload = _run_redact(log)
    assert payload["samples"] == 5
    assert payload["by_class"]["rspec"]["count"] == 5
    assert abs(payload["by_class"]["rspec"]["mean"] - 0.7) < 1e-6


