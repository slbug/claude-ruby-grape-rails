---
name: session-scan
description: Compute exploratory metrics for recent Claude sessions. Deterministic SQLite-direct scan over the local ccrider database; no MCP, no LLM, no subagents for scoring.
argument-hint: "[--since DATE] [--project NAME] [--provider NAME] [--limit N] [--list] [--rescan] [--db PATH] [--metrics-dir PATH] [--min-messages N]"
disable-model-invocation: true
---

# Session Scan (Tier 1)

Compute deterministic-but-heuristic session metrics from sessions indexed by
the local `ccrider` SQLite database. Contributor analytics, not release
gating.

## How It Works

Scoring is pure regex + aggregation in Python. No LLM reasoning. No subagent
fan-out. One Bash call invokes `references/scan-sessions.py` which:

1. Resolves the ccrider DB path.
2. Runs a read-only SQL query to list candidate sessions.
3. For each candidate: pulls `messages.content` rows, reconstructs the
   message list, passes it to the canonical scorer, appends the result to
   `metrics.jsonl`.
4. Prints a triage table.

Entire scan takes seconds and uses negligible main-context tokens — the
transcript data never leaves the Python process.

## Requirements

- `ccrider` installed locally — see <https://github.com/neilberkman/ccrider>
- `ccrider sync` has run (populates the SQLite DB from Claude Code /
  Codex session files)
- python3 available

## DB Path Resolution

The scanner searches these locations in order:

1. `--db PATH` CLI flag
2. `CCRIDER_DB` environment variable
3. `$XDG_CONFIG_HOME/ccrider/sessions.db`
4. `$HOME/.config/ccrider/sessions.db`  (Linux / macOS default)
5. `$HOME/Library/Application Support/ccrider/sessions.db`  (macOS alt)
6. `$APPDATA/ccrider/sessions.db`  (Windows)

**If no candidate exists**, the script exits with code `2` and lists the
paths it tried. When that happens, ask the contributor for the DB path and
re-run with `--db PATH` — do not hard-fail until the contributor confirms
no path is available.

## Usage

```text
/session-scan
/session-scan --since 2026-02-01
/session-scan --project myapp
/session-scan --provider claude
/session-scan --limit 20
/session-scan --list
/session-scan --rescan
/session-scan --db /custom/path/to/sessions.db
```

Providers exposed by the ccrider DB include `claude` and `codex`. The
contributor may use different project directories in the same stack; the
`--provider` filter keeps single-stack comparisons honest.

## Main-Context Workflow

### 1. Parse Arguments

Pass `$ARGUMENTS` through to `scan-sessions.py`. Supported flags:

- `--since DATE`         (default: 7 days ago)
- `--project SUBSTR`     (matches `sessions.project_path LIKE '%SUBSTR%'`)
- `--provider NAME`      (exact match on `sessions.provider`)
- `--limit N`            (default: 50)
- `--list`               (discovery only, no scoring)
- `--rescan`             (recompute already-scanned sessions)
- `--db PATH`            (override DB path)
- `--metrics-dir DIR`    (default: `.claude/session-metrics`)
- `--min-messages N`     (default: 5 — filter trivial ping/hi sessions)

### 2. Invoke the Scanner

```bash
python3 .claude/skills/session-scan/references/scan-sessions.py \
  [flags from step 1]
```

### 3. Handle "DB Not Found"

If the script exits with code `2`:

1. Read stderr — it lists every candidate path that was tried.
2. Ask the contributor where their ccrider DB lives.
3. Re-run with `--db PATH` once they answer.
4. Only treat the scan as impossible if the contributor confirms no local DB
   exists (e.g. ccrider not installed, not synced).

### 4. Relay the Triage Table

The script prints a Markdown table sorted by friction descending. Pass it
through to the contributor as-is. Add a one-line summary with the
scanned / skipped / error counts from stderr.

If the script reports `Tier2-eligible > 0`, suggest `/session-deep-dive
--from-scan` for qualitative analysis.

### 5. Scan Metadata

The script writes `.claude/session-metrics/latest-scan.json` with scan
timestamp, filters used, counts, and any session-level errors. No main-
context action needed.

## Files

- `references/scan-sessions.py` — end-to-end orchestrator (discovery,
  dedup, scoring, ledger append, table)
- `references/compute-metrics.py` — canonical scorer; also supports
  `--from-db SESSION_ID --db PATH` for manual single-session rescoring
- `references/scoring-guide.md` — what each metric means

## Iron Laws

1. Read-only SQL only. No `UPDATE`, `DELETE`, `INSERT`, `DROP`, or PRAGMA
   changes anywhere in the scan path.
2. Transcript data never enters main context — the Python process reads
   rows and emits metrics; only the small JSON metrics line and the final
   table cross process boundaries.
3. Keep `metrics.jsonl` append-only. Dedup happens before scoring.
4. Use the canonical scorer, not ad-hoc reimplementations of the metric
   formulas.
5. Treat scan output as triage input, not release proof.
6. Honor `--provider` when the contributor asks for a provider-scoped view.

## Epistemic Posture

Scan output is triage signal, not decision-grade. Report what the
scorer actually produced with direct language; do not dress up raw
heuristics in confident framing. Low-sample sessions remain low-
confidence in the output. Apology cascades and hedge chains have no
place in a scan summary.
