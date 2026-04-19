---
name: docs-check
description: |
  CONTRIBUTOR TOOL - Check the plugin against current cached Claude Code docs.
  Use before releases or after Claude docs changes to separate real schema drift
  from stale local assumptions. Not part of the distributed plugin.
argument-hint: "[--quick|--focus=agents|skills|hooks|config]"
---

# Plugin Documentation Compatibility Check

Validate `plugins/ruby-grape-rails/` against the current cached Claude Code
docs. This workflow is for contributor maintenance, not user-facing plugin use.

## What This Skill Is For

Use `/docs-check` when you need to answer questions like:

- "Did Claude docs change in a way that breaks our plugin?"
- "Is this warning a real compatibility issue or just stale local guidance?"
- "What new Claude feature is now documented and relevant to this repo?"

Do not use `/docs-check` as a style linter for naming, line counts, or repo
preferences unrelated to docs compatibility.

## Usage

```text
/docs-check
/docs-check --quick
/docs-check --focus=agents
/docs-check --focus=skills
/docs-check --focus=hooks
/docs-check --focus=config
```

## Execution Flow

### 1. Run the deterministic baseline first

Always start with:

```bash
claude plugin validate plugins/ruby-grape-rails
```

That catches structural schema issues without any docs interpretation.

### 2. Refresh cached docs unless `--quick`

From repo root:

```bash
bash ./scripts/fetch-claude-docs.sh
```

`--quick` skips fetching and limits the run to structural drift checks against
the existing cache.

### 3. Delegate to the orchestrator

Use the contributor agent:

```text
Agent(subagent_type: "docs-validation-orchestrator")
```

Pass through the user flags. The orchestrator should:

- inventory the relevant plugin surface
- open only the cached doc pages needed for that question
- compare only the file snippets needed for the finding
- classify results as blocker, warning, info, or pass

## Core Rules

1. Current cached docs are the source of truth for Claude feature support.
2. `claude plugin validate` remains the deterministic baseline.
3. Prefer targeted cached-doc snippets over pasting full pages into prompts.
4. Prefer `Agent(...)` terminology over historical `Task(...)` wording.
5. Distinguish docs incompatibility from local repo recommendations.
6. Treat dated reports under `.claude/docs-check/` as historical snapshots; a
   stale warning in an old report is not current guidance if the cached docs
   and current validator disagree.

## Outputs

Expected outputs are:

- a concise contributor report under `.claude/docs-check/`
- a clear split between:
  - actual compatibility problems
  - documented new capabilities
  - local repo recommendations that are not schema failures

## Epistemic Posture

Drift findings use direct language. If docs + plugin are incompatible,
state the mismatch plainly with the exact cached-doc section and the
exact plugin file/line — not "seems stale" or "might be outdated".
Apology cascades and hedge chains inflate the report without signal.
Separate deterministic validator output from subjective repo
recommendations; don't let softer phrasing blur the two.

## References

- `references/validation-rules.md`
- `references/doc-pages.md`
