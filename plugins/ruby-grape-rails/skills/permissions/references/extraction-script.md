# Session JSONL Extraction

Run the canonical Ruby extractor:

```bash
ruby "${CLAUDE_SKILL_DIR}/scripts/extract_permissions.rb" --days 14
```

Optional machine-readable output:

```bash
ruby "${CLAUDE_SKILL_DIR}/scripts/extract_permissions.rb" --days 14 --json
```

## What It Scans

- Claude session JSONL files for the current repo only:
  `~/.claude/projects/{project-slug}/*.jsonl`
- Current permissions from:
  - `~/.claude/settings.json`
  - `.claude/settings.json`
  - `.claude/settings.local.json`

## What It Reports

- total session files scanned in the requested window
- uncovered Bash command groups not currently covered by `permissions.allow`
- example full commands for each uncovered group
- deprecated `Bash(name:*)` patterns that should be rewritten
- obvious garbage permission entries
- duplicate permission entries

## Output Notes

- Commands already covered by existing `allow` patterns are omitted.
- Commands explicitly matched by `deny` patterns are ignored as recommendation
  candidates; they should stay manually approved or denied.
- Grouping is heuristic and aimed at useful permission patterns, not exact
  command reconstruction.

Use the extractor output as evidence, then classify the groups with
`risk-classification.md` before proposing settings changes.
