---
name: rb:permissions
description: Analyze recent Claude Code sessions and recommend safe Bash permission entries for Ruby/Rails/Grape workflows in settings.json. Use when permission prompts slow work, after repeated Bash approvals, or when the user says "fix permissions", "reduce prompts", "allow commands", "permission fatigue", "bash permission denied", "settings.json", or "stop asking me".
argument-hint: "[--days=14] [--dry-run]"
effort: low
---
# Permission Analyzer

Scan recent Claude session transcripts, find Ruby-project Bash commands that keep
requiring approval, compare them against current Claude `settings.json`
permissions, and recommend the safest missing entries.

**Primary goal**: Discover missing permissions from actual usage.
**Secondary goal**: Clean up deprecated, duplicate, or garbage permission rules.

## Usage

`/rb:permissions [--days=14] [--dry-run]` — Scans recent session JSONL files
for the current project, finds uncovered Bash commands, classifies risk, and
recommends `settings.json` changes. Use `--dry-run` to preview without
writing.

## Arguments

`$ARGUMENTS` — `--days=N` (default: 14), `--dry-run` (preview only).

## Iron Laws

1. **Never auto-allow RED commands.**
2. **Evidence-based only** — recommend commands actually approved in sessions.
3. **Show before writing** — present the diff, get explicit confirmation.
4. **Preserve existing settings** — merge, never overwrite.
5. **Prefer the narrowest safe scope** — project settings for Ruby app commands, user settings only for universal tools.

## Workflow

### Step 1: Extract Uncovered Bash Commands

Run the canonical extractor first:

```bash
ruby "${CLAUDE_SKILL_DIR}/scripts/extract_permissions.rb" --days "${DAYS:-14}"
```

See `${CLAUDE_SKILL_DIR}/references/extraction-script.md` for the output format.

Do not skip straight to writing settings. The extraction step is the evidence.

### Step 2: Classify and Normalize

For each uncovered command group:

1. Classify it as GREEN / YELLOW / RED using
   `${CLAUDE_SKILL_DIR}/references/risk-classification.md`.
2. Normalize it to the narrowest useful permission pattern:
   - `bundle exec rspec spec/models/user_spec.rb` →
     `Bash(bundle exec rspec *)`
   - `bundle exec rails test test/models/user_test.rb` →
     `Bash(bundle exec rails test *)`
   - `bundle exec rubocop app/models/user.rb` →
     `Bash(bundle exec rubocop *)`
   - `bundle exec rails db:migrate` →
     `Bash(bundle exec rails db:migrate *)`
   - `git status --short` → `Bash(git status *)`
3. Prefer specific project commands over broad umbrellas like `Bash(bundle *)`
   unless the user explicitly wants broad trust.
4. Also review the extractor output for:
   - deprecated `Bash(name:*)` patterns
   - exact duplicates
   - obvious garbage entries like heredoc fragments or `Bash(done)`

### Step 3: Interactive Triage

Unless `--dry-run` was requested, walk the user through the findings.

- Batch GREEN items first:
  - add all
  - pick individually
  - skip all
- Show YELLOW items individually with the exact command pattern and a short risk note.
- Never recommend RED items for auto-allow. Show them separately as "keep manual approval".
- Show cleanup candidates:
  - deprecated syntax to rewrite
  - duplicates to remove
  - garbage entries to remove

### Step 4: Apply Safely

Use `${CLAUDE_SKILL_DIR}/references/settings-format.md` for syntax and scope.

- Prefer `.claude/settings.json` for project-specific Ruby commands:
  - `bundle exec rspec *`
  - `bundle exec rails test *`
  - `bundle exec rubocop *`
  - `bundle exec brakeman *`
- Prefer `~/.claude/settings.json` only for universal developer tools:
  - `rg *`
  - `jq *`
  - `git status *`
- Use `.claude/settings.local.json` for personal/local-only preferences.

When writing:

1. Read the target settings file first.
2. Merge into `permissions.allow` / `permissions.deny`; do not replace unrelated keys.
3. Rewrite deprecated `:*` patterns to the modern space-before-wildcard form.
4. Show the final diff before writing unless the user explicitly asked for non-interactive application.

## References

- `${CLAUDE_SKILL_DIR}/references/extraction-script.md` — canonical extractor and output shape
- `${CLAUDE_SKILL_DIR}/references/risk-classification.md` — Ruby-specific risk model
- `${CLAUDE_SKILL_DIR}/references/settings-format.md` — Claude settings format and scope rules
