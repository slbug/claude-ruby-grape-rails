---
name: cc-changelog
description: |
  CONTRIBUTOR TOOL - Track CC changelog, extract new versions since last check,
  analyze impact on plugin (breaking changes, opportunities, deprecations).
  Run periodically or before releases. NOT part of the distributed plugin.
argument-hint: "[--all|--set=VERSION]"
effort: low
---

# Claude Code Changelog Assistant

## Audience: Agents, Not Humans

Imperative-only. Tables for category and shape lists.

## Usage

| Command | Purpose |
|---|---|
| `/cc-changelog` | check for new CC versions, analyze impact |
| `/cc-changelog --all` | re-analyze all versions (ignore last check) |
| `/cc-changelog --set=2.1.85` | reset last checked version, then re-run |

## Execution Flow

### Step 1: Fetch New Entries

Run `bash scripts/fetch-cc-changelog.sh` (or `--all` for full re-fetch).

| Output prefix | Action |
|---|---|
| `STATUS: UP_TO_DATE` | report "No new CC versions" and stop |
| `STATUS: NEW_VERSIONS` | continue with content below the header |

`--all` flag → `bash scripts/fetch-cc-changelog.sh --all`.
`--set=X` flag → `bash scripts/fetch-cc-changelog.sh --set=X`, then re-run without flag.

### Step 2: Analyze Impact

Read new changelog entries. Classify each into one category:

| Category | Meaning | Action |
|----------|---------|--------|
| **BREAKING** | may break existing plugin functionality | immediate fix required |
| **OPPORTUNITY** | new CC feature plugin could use | add to backlog/plan |
| **RELEVANT FIX** | CC fixed a bug we worked around | check if workaround removable |
| **DEPRECATION** | CC removing something we use | plan migration |
| **INFO** | good to know, no action needed | log only |

Cross-reference plugin components via `${CLAUDE_SKILL_DIR}/references/analysis-rules.md`.

### Step 3: Generate Report

Output structured report:

```markdown
## CC Changelog Analysis: v{last_checked} → v{latest}

### BREAKING (action required)
- [version] description → **Impact**: which plugin file/component
  **Fix**: specific action needed

### OPPORTUNITY (new features)
- [version] description → **Use case**: how plugin could benefit
  **Files**: which plugin files to update

### RELEVANT FIX (workaround removal)
- [version] description → **Current workaround**: what we do now
  **Action**: can we simplify?

### DEPRECATION (migration needed)
- [version] description → **We use this in**: file:line
  **Migration**: what to change

### INFO (no action)
- [version] brief summary (collapsed)
```

### Step 4: Update State

After user reviews the report, ask:

> "Update last checked version to {latest}? [Yes/No]"

If yes: run `bash scripts/fetch-cc-changelog.sh --set={latest}`.

If BREAKING or DEPRECATION found, offer to create a plan.

## Iron Laws

1. ALWAYS fetch before analyzing — never analyze stale cache.
2. NEVER auto-update state — user confirms after reviewing report.
3. ALWAYS cross-reference plugin files — map impact, not just summarize.
4. BREAKING changes are BLOCKERS — surface first, prominently.
5. State file is the source of truth for audit version.

## Epistemic Posture

Direct language for breaking-change analysis. CC version that removes
or renames a plugin API the repo uses → label BLOCKER without
softening. Deprecations labeled `deprecated` in the CC changelog →
direct flag, not "consider migrating eventually". No apology cascades,
no hedge chains.
