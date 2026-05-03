---
name: session-scan
description: Compute exploratory metrics for recent Claude sessions. Deterministic SQLite-direct scan over the local ccrider database; no MCP, no LLM, no subagents for scoring.
argument-hint: "[--since DATE] [--project NAME] [--provider NAME] [--limit N] [--list] [--rescan] [--db PATH] [--metrics-dir PATH] [--min-messages N]"
disable-model-invocation: true
---

# Session Scan (Tier 1)

## Audience: Agents, Not Humans

Imperative-only. Contributor analytics, NOT release gating.

## Requirements

| Requirement | Detail |
|---|---|
| `ccrider` installed | <https://github.com/neilberkman/ccrider> |
| `ccrider sync` ran | populates SQLite DB from CC / Codex session files |
| Python | 3.14+ (uses `str \| None` / `list[X]` natively) |

## DB Path Resolution

Search order:

1. `--db PATH` flag
2. `CCRIDER_DB` env var
3. `$XDG_CONFIG_HOME/ccrider/sessions.db`
4. `$HOME/.config/ccrider/sessions.db` (Linux / macOS default)
5. `$HOME/Library/Application Support/ccrider/sessions.db` (macOS alt)
6. `$APPDATA/ccrider/sessions.db` (Windows)

No candidate exists → script exits with code `2`, lists tried paths.
Ask contributor for DB path, re-run with `--db PATH`. Do NOT hard-fail
until contributor confirms no path is available.

## Usage

| Command | Behavior |
|---|---|
| `/session-scan` | default 7-day window |
| `/session-scan --since 2026-02-01` | start date filter |
| `/session-scan --project myapp` | substring on `project_path` |
| `/session-scan --provider claude` | exact match on `provider` |
| `/session-scan --limit 20` | cap candidate count |
| `/session-scan --list` | discovery only, no scoring |
| `/session-scan --rescan` | recompute already-scanned sessions |
| `/session-scan --db /custom/path/to/sessions.db` | DB override |

`--provider` takes exact `sessions.provider` value from `--list`
output. Examples (`claude`, `codex`, `claude-code`) are illustrative
— filter is exact match.

## Main-Context Workflow

### 1. Parse Arguments

Pass `$ARGUMENTS` through to `scan-sessions.py`. Supported flags:

| Flag | Default |
|---|---|
| `--since DATE` | 7 days ago |
| `--project SUBSTR` | matches `sessions.project_path LIKE '%SUBSTR%'` |
| `--provider NAME` | exact match on `sessions.provider` |
| `--limit N` | 50 |
| `--list` | discovery only |
| `--rescan` | recompute scanned sessions |
| `--db PATH` | DB override |
| `--metrics-dir DIR` | `.claude/session-metrics` |
| `--min-messages N` | 5 (filter trivial ping/hi sessions) |

### 2. Invoke the Scanner

Run `python3 .claude/skills/session-scan/references/scan-sessions.py`
with the parsed flags.

### 3. Handle "DB Not Found"

Script exits code `2`:

| stderr says | Action |
|---|---|
| `Error: --db path does not exist` / `Error: --db path is not a file` | contributor-provided path is wrong; ask for correct DB path; re-run with `--db PATH` |
| (default candidates list) | ask contributor where their ccrider DB lives; re-run with `--db PATH` |
| contributor confirms no local DB | scan is impossible (ccrider not installed / not synced) |

### 4. Relay the Triage Table

Script prints Markdown table sorted by friction descending. Pass
through to contributor as-is. Add one-line summary with scanned /
skipped / error counts from stderr.

`Tier2-eligible > 0` reported → suggest `/session-deep-dive --from-scan`
for qualitative analysis.

### 5. Scan Metadata

Script writes `.claude/session-metrics/latest-scan.json` (scan
timestamp, filters used, counts, session-level errors). No
main-context action needed.

## Files

| File | Role |
|---|---|
| `references/scan-sessions.py` | end-to-end orchestrator (discovery, dedup, scoring, ledger append, table) |
| `references/compute-metrics.py` | canonical scorer; supports `--from-db SESSION_ID --db PATH` for manual single-session rescoring |
| `references/scoring-guide.md` | metric definitions |

## Iron Laws

1. Read-only SQL. NO `UPDATE`, `DELETE`, `INSERT`, `DROP`, or PRAGMA changes.
2. Transcript data NEVER enters main context — Python process reads rows + emits metrics; only small JSON metrics line and final table cross process boundaries.
3. `metrics.jsonl` is append-only. Dedup happens before scoring.
4. Use canonical scorer, NOT ad-hoc reimplementations of metric formulas.
5. Scan output = triage input, NOT release proof.
6. Honor `--provider` when contributor asks for provider-scoped view.

## Epistemic Posture

Direct language reporting raw heuristic output. Do NOT dress up
heuristics in confident framing. Low-sample sessions stay
low-confidence. No apology cascades, no hedge chains.
