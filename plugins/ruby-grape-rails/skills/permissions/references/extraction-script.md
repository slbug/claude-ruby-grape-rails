# Session JSONL Extraction

Run the canonical Ruby extractor:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/extract-permissions --days 14
```

Optional machine-readable output:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/extract-permissions --days 14 --json
```

Other useful flags:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/extract-permissions --days 30 --limit 50 --include-global
```

Validation rules:

- `--days` must be `0` or greater.
- `--limit` must be greater than `0`.
- repo-local settings are the default scope.
- `--repo-only` is accepted for explicitness and keeps the default behavior.
- `--include-global` also loads `~/.claude/settings.json`.
- `--dry-run` is accepted for skill parity; the extractor is read-only either
  way.
- malformed-but-parseable settings/transcript entries are ignored and reported
  as invalid instead of crashing the extractor.

## What It Scans

- Claude session JSONL files for the current repo only:
  `~/.claude/projects/{project-slug}/*.jsonl`
- Override the transcript root when needed with:
  - `RUBY_PLUGIN_PERMISSIONS_PROJECTS_DIR`
  - or `CLAUDE_PROJECTS_DIR`
- Repo scope resolved from the current git root when available, otherwise from
  repo-local markers such as:
  - `.claude/settings.json`
  - `.claude/settings.local.json`
  - `Gemfile`
- Current permissions from:
  - `.claude/settings.json`
  - `.claude/settings.local.json`
  - and, when `--include-global` is set, `~/.claude/settings.json`

## What It Reports

- total session files scanned in the requested window
- uncovered Bash command groups not currently covered by `permissions.allow`
- example first-line command snippets (truncated to 300 characters) for each
  uncovered group
- deprecated `Bash(name:*)` patterns that should be rewritten
- obvious garbage permission entries
- duplicate permission entries
- scan truncation metadata when large session windows are capped
- the exact settings sources considered during the audit

## Output Notes

- Commands already covered by existing `allow` patterns are omitted.
- Commands explicitly matched by `deny` patterns are ignored as recommendation
  candidates; they should stay manually approved or denied.
- Grouping is heuristic and aimed at useful permission patterns, not exact
  command reconstruction.
- Large session windows are capped by default to the newest `200` session files
  and `10000` lines per file. Override with:
  - `RUBY_PLUGIN_PERMISSIONS_MAX_SESSION_FILES`
  - `RUBY_PLUGIN_PERMISSIONS_MAX_LINES_PER_FILE`
- When `--include-global` is used, check the reported settings-source list so
  personal `~/.claude/settings.json` policy does not get mistaken for
  repo-local defaults.

Use the extractor output as evidence, then classify the groups with
`risk-classification.md` before proposing settings changes.
