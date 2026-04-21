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

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def positive_int(value: str) -> int:
    """Argparse type for positive integer flags."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid integer value: {value!r}"
        ) from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


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
    uri = f"{path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def parse_since(value: str | None) -> str:
    """Normalize ``--since`` for SQL comparison against ccrider ``updated_at``.

    ccrider stores timestamps as ``"YYYY-MM-DD HH:MM:SS.<frac> +OFFSET TZ"``
    with mixed offsets across rows, and SQLite's ``datetime()`` cannot parse
    the trailing offset/zone suffix. To compare instants correctly we:

    1. Accept ISO-8601 date (``YYYY-MM-DD``) or datetime with optional ``T``
       separator and optional trailing ``Z`` or ``±HH:MM`` offset.
    2. Convert tz-aware inputs to UTC; treat naive inputs as UTC.
    3. Return a fixed-width ``"YYYY-MM-DD HH:MM:SS"`` string (space separator
       matches the 19-char prefix of ccrider's ``updated_at``). Date-only
       input is padded to ``"YYYY-MM-DD 00:00:00"`` so ``SUBSTR(updated_at,
       1, 19) >= :since`` is a total order over all rows.

    ccrider rows stored with non-UTC offsets still carry local wall-clock in
    the first 19 chars, so rows imported from non-UTC environments can drift
    by the offset amount. In practice the vast majority of ccrider imports
    are UTC (the Go binary defaults to UTC), and rejecting malformed input
    early is worth more than trying to parse every offset server-side.

    Bails out with exit code 1 on invalid input so typos do not silently
    yield empty result sets.
    """

    if not value:
        start = (datetime.now(timezone.utc) - timedelta(days=7)).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        return start.strftime("%Y-%m-%d %H:%M:%S")

    raw = value.strip()
    if not raw:
        sys.stderr.write(
            "Error: --since must be an ISO-8601 date or datetime.\n"
        )
        sys.exit(1)

    try:
        if "T" not in raw and " " not in raw:
            # Pure date; pad to midnight UTC.
            day = datetime.fromisoformat(raw).date()
            return datetime.combine(
                day, datetime.min.time()
            ).strftime("%Y-%m-%d %H:%M:%S")

        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        sys.stderr.write(
            f"Error: invalid --since value {value!r}. "
            "Expected an ISO-8601 date or datetime.\n"
        )
        sys.exit(1)


def discover_sessions(
    conn: sqlite3.Connection,
    *,
    since: str,
    project: str | None,
    provider: str | None,
    limit: int,
    min_messages: int,
    offset: int = 0,
) -> list[sqlite3.Row]:
    # ``updated_at`` is stored as Go's ``time.Time.String()`` output —
    # e.g. ``"2025-12-23 06:11:34.193 +0000 UTC"`` — which SQLite's
    # ``datetime()`` cannot parse because of the trailing offset/zone
    # suffix. Comparing against the 19-char prefix
    # (``YYYY-MM-DD HH:MM:SS``) alongside a UTC-normalized ``:since``
    # gives a lexical order that matches the instant order for rows that
    # ccrider imported in UTC (the common case). See ``parse_since`` for
    # the normalization contract.
    sql = [
        "SELECT id, session_id, project_path, provider, updated_at,",
        "       message_count, COALESCE(summary, '') AS summary",
        "FROM sessions",
        "WHERE message_count >= :min_messages",
        "  AND SUBSTR(updated_at, 1, 19) >= :since",
    ]
    params: dict[str, object] = {
        "min_messages": min_messages,
        "since": since,
        "limit": limit,
        "offset": offset,
    }
    if project:
        sql.append("  AND project_path LIKE :project")
        params["project"] = f"%{project}%"
    if provider:
        sql.append("  AND provider = :provider")
        params["provider"] = provider
    sql.append("ORDER BY updated_at DESC")
    sql.append("LIMIT :limit")
    sql.append("OFFSET :offset")
    cursor = conn.execute("\n".join(sql), params)
    return list(cursor.fetchall())


def reconstruct_message(
    content: str | None,
    text_content: str | None,
    msg_type: str | None,
    sender: str | None,
) -> tuple[dict | None, str]:
    """Rebuild one message dict from a ccrider ``messages`` row.

    ccrider stores two projections: ``content`` (raw provider JSON, populated
    for Claude) and ``text_content`` (normalized plain text, populated for
    all providers). Codex sessions leave ``content`` empty, so provider-
    neutral reconstruction falls back to ``text_content`` plus role metadata.

    Returns ``(message_dict_or_None, status)`` with statuses:
      - ``"ok"``             content parsed as provider JSON
      - ``"synth"``          synthesized from text_content + type/sender
      - ``"decode_failed"``  content present but malformed and no fallback
      - ``"empty"``          row carries no usable data
    """

    text = text_content if isinstance(text_content, str) else ""
    has_text = bool(text.strip())

    if content:
        try:
            return json.loads(content), "ok"
        except json.JSONDecodeError:
            if has_text:
                role = msg_type or sender or "user"
                return {"role": role, "content": text}, "synth"
            return None, "decode_failed"

    if has_text:
        role = msg_type or sender or "user"
        return {"role": role, "content": text}, "synth"

    return None, "empty"


def load_session_messages(
    conn: sqlite3.Connection, session_pk: int
) -> tuple[list[dict], int, int, int]:
    """Load messages for one session.

    Returns ``(messages, decode_failures, candidate_rows, synthesized)``.
    ``candidate_rows`` counts rows that had either ``content`` or a non-blank
    ``text_content`` — i.e. rows the reconstructor actually considered.
    ``synthesized`` counts rows where the message was synthesized from
    ``text_content`` (Codex path or malformed-content fallback).
    """
    rows = conn.execute(
        (
            "SELECT content, text_content, type, sender "
            "FROM messages WHERE session_id = ? ORDER BY sequence"
        ),
        (session_pk,),
    ).fetchall()
    msgs: list[dict] = []
    decode_failures = 0
    candidate_rows = 0
    synthesized = 0
    for row in rows:
        content = row["content"]
        text_content = row["text_content"]
        msg_type = row["type"]
        sender = row["sender"]
        if not content and not (
            isinstance(text_content, str) and text_content.strip()
        ):
            continue
        candidate_rows += 1
        msg, status = reconstruct_message(content, text_content, msg_type, sender)
        if status == "ok":
            msgs.append(msg)
        elif status == "synth":
            msgs.append(msg)
            synthesized += 1
        elif status == "decode_failed":
            decode_failures += 1
        # status == "empty" already filtered above
    return msgs, decode_failures, candidate_rows, synthesized


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


def parse_entry_timestamp(entry: dict) -> datetime:
    value = entry.get("scanned_at") or entry.get("date") or ""
    if not value:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            return datetime(2000, 1, 1, tzinfo=timezone.utc)


def read_latest_ledger_entries(metrics_path: Path) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    if not metrics_path.exists():
        return entries
    with metrics_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            session_id = entry.get("session_id")
            if session_id:
                entries[session_id] = entry
    return entries


def collect_unscanned_sessions(
    conn: sqlite3.Connection,
    *,
    since: str,
    project: str | None,
    provider: str | None,
    limit: int,
    min_messages: int,
    ledger_ids: set[str],
) -> tuple[list[sqlite3.Row], int]:
    page_size = max(limit, 50)
    offset = 0
    skipped = 0
    collected: list[sqlite3.Row] = []

    while len(collected) < limit:
        batch = discover_sessions(
            conn,
            since=since,
            project=project,
            provider=provider,
            limit=page_size,
            min_messages=min_messages,
            offset=offset,
        )
        if not batch:
            break

        for row in batch:
            if row["session_id"] in ledger_ids:
                skipped += 1
                continue
            collected.append(row)
            if len(collected) >= limit:
                break

        offset += len(batch)
        if len(batch) < page_size:
            break

    return collected, skipped


def build_current_view_entries(
    view_rows: list[sqlite3.Row], latest_entries: dict[str, dict]
) -> list[dict]:
    entries = [
        latest_entries[row["session_id"]]
        for row in view_rows
        if row["session_id"] in latest_entries
    ]
    return sorted(entries, key=parse_entry_timestamp, reverse=True)


def format_triage_table(entries: list[dict]) -> str:
    if not entries:
        return "No scored sessions available for the current view."
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
    ap.add_argument("--limit", type=positive_int, default=50)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--rescan", action="store_true")
    ap.add_argument("--db")
    ap.add_argument("--metrics-dir", default=".claude/session-metrics")
    ap.add_argument("--min-messages", type=positive_int, default=5)
    args = ap.parse_args(argv)

    db_path = resolve_db(args.db)
    since = parse_since(args.since)
    metrics_dir = (
        Path(os.path.expandvars(args.metrics_dir)).expanduser().resolve()
    )

    print(f"DB: {db_path}", file=sys.stderr)
    print(
        f"Filters: since={since} project={args.project or '-'} "
        f"provider={args.provider or '-'} min_messages={args.min_messages} "
        f"limit={args.limit}",
        file=sys.stderr,
    )

    conn: sqlite3.Connection | None = None
    try:
        conn = open_db_readonly(db_path)
        rows = discover_sessions(
            conn,
            since=since,
            project=args.project,
            provider=args.provider,
            limit=args.limit,
            min_messages=args.min_messages,
        )
    except sqlite3.Error as exc:
        print(f"Error: failed to read ccrider DB at {db_path}: {exc}", file=sys.stderr)
        return 1
    try:

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

        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = metrics_dir / "metrics.jsonl"
        latest_scan_path = metrics_dir / "latest-scan.json"

        scorer = load_scoring_module()
        ledger_ids = read_ledger(metrics_path)

        if args.rescan:
            to_score = rows
            skipped = 0
        else:
            to_score, skipped = collect_unscanned_sessions(
                conn,
                since=since,
                project=args.project,
                provider=args.provider,
                limit=args.limit,
                min_messages=args.min_messages,
                ledger_ids=ledger_ids,
            )

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
            project = r["project_path"] or "unknown"
            provider = r["provider"]
            date = (r["updated_at"] or "")[:10] or None
            try:
                msgs, decode_failures, candidate_rows, synthesized = (
                    load_session_messages(conn, r["id"])
                )
                if decode_failures:
                    warning = {
                        "session_id": sid,
                        "decode_failures": decode_failures,
                        "candidate_rows": candidate_rows,
                        "synthesized_from_text": synthesized,
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
                    if not msgs and candidate_rows:
                        raise ValueError(
                            f"failed to decode all {candidate_rows} candidate "
                            f"message row(s) for session {sid}"
                        )
                metrics = scorer.compute_session_metrics(
                    msgs, sid, project, date=date, provider=provider
                )
                with metrics_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(metrics) + "\n")
                results.append(metrics)
                print(
                    f"  [{i}/{len(to_score)}] {sid[:8]} "
                    f"{short_project(project)[:20]:<20} "
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

        latest_entries = read_latest_ledger_entries(metrics_path)
        view_entries = build_current_view_entries(rows, latest_entries)
        # Merge newly-scored sessions that fell outside the initial top-N
        # `rows` window (paginated backfill hits). Without this, the triage
        # table + latest-scan.json would reference only the first page and
        # hide sessions actually scored on this run.
        view_ids = {entry.get("session_id") for entry in view_entries}
        for metric in results:
            sid = metric.get("session_id")
            if sid and sid not in view_ids:
                view_entries.append(metric)
                view_ids.add(sid)
        view_entries = sorted(view_entries, key=parse_entry_timestamp, reverse=True)
        view_tier2 = [entry for entry in view_entries if entry.get("tier2_eligible")]
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
            "sessions_in_view": len(view_entries),
            "tier2_eligible": len(view_tier2),
            "view_session_ids": [entry["session_id"] for entry in view_entries],
            "tier2_session_ids": [entry["session_id"] for entry in view_tier2],
            "errors": [{"session_id": s, "reason": r} for s, r in errors],
            "warnings": warnings,
        }
        latest_scan_path.write_text(
            json.dumps(scan_meta, indent=2) + "\n",
            encoding="utf-8",
        )

        print()
        print(format_triage_table(view_entries))
        print()
        print(
            f"Scanned {len(results)}, skipped {skipped}, warnings {len(warnings)}, "
            f"errors {len(errors)}. View sessions: {len(view_entries)}. "
            f"Tier2-eligible: {len(view_tier2)}.",
            file=sys.stderr,
        )
        if view_tier2:
            print(
                "Suggest: /session-deep-dive --from-scan  (inspect tier2 sessions)",
                file=sys.stderr,
            )

        return 1 if errors else 0
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
