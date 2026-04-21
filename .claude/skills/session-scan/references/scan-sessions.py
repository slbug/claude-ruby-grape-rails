#!/usr/bin/env python3
"""
Session Scan — deterministic end-to-end orchestrator.

Discovers sessions from the local ccrider SQLite DB, scores each with
compute-metrics, appends results to metrics.jsonl, prints a triage table.
No LLM. No subagents. Read-only SQL.

Usage:
    python3 scan-sessions.py [options]

Options:
    --since DATE         ISO date cutoff (default: 7 days ago)
    --project SUBSTR     Match sessions.project_path LIKE '%SUBSTR%'
    --provider NAME      Match sessions.provider exactly (e.g. claude, codex)
    --limit N            Max sessions to process (default: 50)
    --list               Discovery only; show candidates and exit
    --rescan             Recompute metrics for already-scanned sessions
    --db PATH            Override ccrider DB path
    --metrics-dir DIR    Override metrics dir (default: .claude/session-metrics)
    --min-messages N     Pre-filter by message_count (default: 5)

Exit codes:
    0  success
    1  other error
    2  ccrider DB path unavailable (explicit path missing or no default found)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def load_scoring_module():
    """Load compute-metrics.py as a module via importlib (hyphen in filename)."""
    path = SCRIPT_DIR / "compute-metrics.py"
    if not path.exists():
        sys.exit(f"Error: scorer not found at {path}")
    spec = importlib.util.spec_from_file_location("compute_metrics", path)
    if spec is None or spec.loader is None:
        sys.exit(f"Error: unable to load scorer module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def default_db_candidates() -> list[Path]:
    home = Path.home()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    env_db = os.environ.get("CCRIDER_DB")
    cands: list[Path] = []
    if env_db:
        cands.append(Path(os.path.expandvars(env_db)).expanduser())
    if xdg:
        cands.append(
            Path(os.path.expandvars(xdg)).expanduser() / "ccrider" / "sessions.db"
        )
    cands.extend(
        [
            home / ".config" / "ccrider" / "sessions.db",
            home / "Library" / "Application Support" / "ccrider" / "sessions.db",
        ]
    )
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / "ccrider" / "sessions.db")
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in cands:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


def resolve_db(explicit: str | None) -> Path:
    if explicit:
        p = Path(os.path.expandvars(explicit)).expanduser()
        if not p.exists():
            sys.stderr.write(f"Error: --db path does not exist: {p}\n")
            sys.exit(2)
        if not p.is_file():
            sys.stderr.write(f"Error: --db path is not a file: {p}\n")
            sys.exit(2)
        return p
    cands = default_db_candidates()
    for p in cands:
        if p.exists() and p.is_file():
            return p
    sys.stderr.write("ccrider DB not found. Tried:\n")
    for p in cands:
        sys.stderr.write(f"  - {p}\n")
    sys.stderr.write(
        "Pass --db PATH or set CCRIDER_DB env var. "
        "Install ccrider: https://github.com/neilberkman/ccrider\n"
    )
    sys.exit(2)


def open_db_readonly(path: Path) -> sqlite3.Connection:
    uri = f"{path.resolve().as_uri()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def parse_since(value: str | None) -> str:
    if value:
        return value
    return (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()


def discover_sessions(
    conn: sqlite3.Connection,
    *,
    since: str,
    project: str | None,
    provider: str | None,
    limit: int,
    min_messages: int,
) -> list[sqlite3.Row]:
    sql = [
        "SELECT id, session_id, project_path, provider, updated_at,",
        "       message_count, COALESCE(summary, '') AS summary",
        "FROM sessions",
        "WHERE message_count >= :min_messages",
        "  AND updated_at >= :since",
    ]
    params: dict[str, object] = {
        "min_messages": min_messages,
        "since": since,
        "limit": limit,
    }
    if project:
        sql.append("  AND project_path LIKE :project")
        params["project"] = f"%{project}%"
    if provider:
        sql.append("  AND provider = :provider")
        params["provider"] = provider
    sql.append("ORDER BY updated_at DESC")
    sql.append("LIMIT :limit")
    cursor = conn.execute("\n".join(sql), params)
    return list(cursor.fetchall())


def load_session_messages(
    conn: sqlite3.Connection, session_pk: int
) -> tuple[list[dict], int, int]:
    rows = conn.execute(
        "SELECT content FROM messages WHERE session_id = ? ORDER BY sequence",
        (session_pk,),
    ).fetchall()
    msgs: list[dict] = []
    decode_failures = 0
    non_empty_rows = 0
    for (content,) in rows:
        if not content:
            continue
        non_empty_rows += 1
        try:
            msgs.append(json.loads(content))
        except json.JSONDecodeError:
            decode_failures += 1
            continue
    return msgs, decode_failures, non_empty_rows


def read_ledger(metrics_path: Path) -> set[str]:
    ids: set[str] = set()
    if not metrics_path.exists():
        return ids
    with metrics_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = entry.get("session_id")
            if sid:
                ids.add(sid)
    return ids


def short_project(path: str | None) -> str:
    if not path:
        return "unknown"
    return Path(path).name or path


def format_triage_table(entries: list[dict]) -> str:
    if not entries:
        return "No sessions scored."
    entries = sorted(entries, key=lambda e: e.get("friction_score", 0.0), reverse=True)
    header = (
        "| ID       | Provider    | Project        | Date       | "
        "Fingerprint   | Friction | Opportunity | Tier2 |"
    )
    sep = (
        "|----------|-------------|----------------|------------|"
        "---------------|----------|-------------|-------|"
    )
    lines = [header, sep]
    for e in entries:
        sid = (e.get("session_id") or "")[:8]
        provider = (e.get("provider") or "?")[:11]
        project = short_project(e.get("project"))[:14]
        date = (e.get("date") or "")[:10]
        fp = (e.get("fingerprint") or "?")[:13]
        friction = e.get("friction_score", 0.0)
        opp = e.get("plugin_opportunity_score", 0.0)
        tier2 = "Yes" if e.get("tier2_eligible") else "No"
        lines.append(
            f"| {sid:<8} | {provider:<11} | {project:<14} | {date:<10} | "
            f"{fp:<13} | {friction:>8.2f} | {opp:>11.2f} | {tier2:<5} |"
        )
    return "\n".join(lines)


def format_list_table(rows: list[sqlite3.Row]) -> str:
    header = (
        "| ID       | Provider    | Project        | Updated              | "
        "Msgs | Summary                           |"
    )
    sep = (
        "|----------|-------------|----------------|----------------------|"
        "------|-----------------------------------|"
    )
    lines = [header, sep]
    for r in rows:
        sid = (r["session_id"] or "")[:8]
        provider = (r["provider"] or "?")[:11]
        project = short_project(r["project_path"])[:14]
        updated = (r["updated_at"] or "")[:19]
        msgs = r["message_count"]
        summary = (r["summary"] or "").splitlines()[0][:33] if r["summary"] else ""
        lines.append(
            f"| {sid:<8} | {provider:<11} | {project:<14} | {updated:<20} | "
            f"{msgs:>4} | {summary:<33} |"
        )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--since")
    ap.add_argument("--project")
    ap.add_argument("--provider")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--rescan", action="store_true")
    ap.add_argument("--db")
    ap.add_argument("--metrics-dir", default=".claude/session-metrics")
    ap.add_argument("--min-messages", type=int, default=5)
    args = ap.parse_args(argv)

    db_path = resolve_db(args.db)
    since = parse_since(args.since)
    metrics_dir = (
        Path(os.path.expandvars(args.metrics_dir)).expanduser().resolve()
    )
    metrics_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = metrics_dir / "metrics.jsonl"
    latest_scan_path = metrics_dir / "latest-scan.json"

    print(f"DB: {db_path}", file=sys.stderr)
    print(
        f"Filters: since={since} project={args.project or '-'} "
        f"provider={args.provider or '-'} min_messages={args.min_messages} "
        f"limit={args.limit}",
        file=sys.stderr,
    )

    conn = open_db_readonly(db_path)
    try:
        rows = discover_sessions(
            conn,
            since=since,
            project=args.project,
            provider=args.provider,
            limit=args.limit,
            min_messages=args.min_messages,
        )

        discovered = len(rows)
        print(
            f"Discovered: {discovered} sessions (>= {args.min_messages} msgs).",
            file=sys.stderr,
        )

        if args.list:
            print(format_list_table(rows))
            print(
                f"\n{discovered} candidate(s). Add --rescan to recompute scored ones.",
                file=sys.stderr,
            )
            return 0

        scorer = load_scoring_module()
        ledger_ids = read_ledger(metrics_path)

        to_score: list[sqlite3.Row] = []
        skipped = 0
        for r in rows:
            if r["session_id"] in ledger_ids and not args.rescan:
                skipped += 1
                continue
            to_score.append(r)

        print(
            f"New: {len(to_score)}, already in ledger: {skipped} "
            f"(rescan={args.rescan}).",
            file=sys.stderr,
        )

        results: list[dict] = []
        errors: list[tuple[str, str]] = []
        warnings: list[dict[str, object]] = []
        for i, r in enumerate(to_score, 1):
            sid = r["session_id"]
            project = short_project(r["project_path"])
            provider = r["provider"]
            date = (r["updated_at"] or "")[:10] or None
            try:
                msgs, decode_failures, non_empty_rows = load_session_messages(
                    conn, r["id"]
                )
                if decode_failures:
                    warning = {
                        "session_id": sid,
                        "decode_failures": decode_failures,
                        "non_empty_rows": non_empty_rows,
                        "reason": (
                            f"skipped {decode_failures} malformed message JSON row(s)"
                        ),
                    }
                    warnings.append(warning)
                    print(
                        f"  [{i}/{len(to_score)}] {sid[:8]} WARNING: "
                        f"{warning['reason']}",
                        file=sys.stderr,
                    )
                    if not msgs and non_empty_rows:
                        raise ValueError(
                            f"failed to decode all {non_empty_rows} non-empty "
                            f"message row(s) for session {sid}"
                        )
                metrics = scorer.compute_session_metrics(
                    msgs, sid, project, date=date, provider=provider
                )
                with metrics_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(metrics) + "\n")
                results.append(metrics)
                print(
                    f"  [{i}/{len(to_score)}] {sid[:8]} {project[:20]:<20} "
                    f"msgs={len(msgs):<4} friction={metrics['friction_score']:.2f} "
                    f"fp={metrics['fingerprint']}",
                    file=sys.stderr,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append((sid, repr(exc)))
                print(
                    f"  [{i}/{len(to_score)}] {sid[:8]} ERROR: {exc!r}",
                    file=sys.stderr,
                )

        tier2 = [r for r in results if r.get("tier2_eligible")]
        scan_meta = {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "db_path": str(db_path),
            "since": since,
            "project_filter": args.project,
            "provider_filter": args.provider,
            "min_messages": args.min_messages,
            "limit": args.limit,
            "sessions_discovered": discovered,
            "sessions_scanned": len(results),
            "sessions_skipped": skipped,
            "sessions_failed": len(errors),
            "sessions_warned": len(warnings),
            "tier2_eligible": len(tier2),
            "errors": [{"session_id": s, "reason": r} for s, r in errors],
            "warnings": warnings,
        }
        latest_scan_path.write_text(
            json.dumps(scan_meta, indent=2) + "\n",
            encoding="utf-8",
        )

        print()
        print(format_triage_table(results))
        print()
        print(
            f"Scanned {len(results)}, skipped {skipped}, warnings {len(warnings)}, "
            f"errors {len(errors)}. Tier2-eligible: {len(tier2)}.",
            file=sys.stderr,
        )
        if tier2:
            print(
                "Suggest: /session-deep-dive --from-scan  (inspect tier2 sessions)",
                file=sys.stderr,
            )

        return 1 if errors else 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
