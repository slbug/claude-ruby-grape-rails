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

- `/docs-check`
- `/docs-check --quick`
- `/docs-check --focus=agents`
- `/docs-check --focus=skills`
- `/docs-check --focus=hooks`
- `/docs-check --focus=config`

## Execution Flow

### 1. Run the deterministic baseline first

Always start by running `claude plugin validate plugins/ruby-grape-rails`
to catch structural schema issues without any docs interpretation.

### 2. Refresh cached docs unless `--quick`

From repo root, run `bash ./scripts/fetch-claude-docs.sh` to refresh the
cached docs. The `--quick` flag skips fetching and limits the run to
structural drift checks against the existing cache.

### 3. Inventory plugin surfaces (main session)

Identify which plugin surfaces are in scope per `--focus` flag:

- `agents`: `plugins/ruby-grape-rails/agents/*.md`
- `skills`: `plugins/ruby-grape-rails/skills/*/SKILL.md`
- `hooks`: `plugins/ruby-grape-rails/hooks/hooks.json`
- `config`:
  - `plugins/ruby-grape-rails/.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json`

Without `--focus`, validate all surfaces.

### 4. Gather authoritative inputs (main session)

Read:

- `.claude/skills/docs-check/references/validation-rules.md`
- `.claude/skills/docs-check/references/doc-pages.md`

Map each validation question to the smallest cached-doc set:

| Surface | Cached docs |
|---|---|
| agents | `plugins-reference.md`, `sub-agents.md` |
| skills | `skills.md`, `hooks.md` (only if skill hooks matter) |
| hooks | `hooks.md`, `hooks-guide.md` |
| config | `plugins-reference.md`, `plugin-marketplaces.md`, `plugins.md`, `mcp.md` (if needed), `settings.md` (if needed) |

Do NOT paste full cached pages into worker prompts.

### 5. Spawn workers (main session, parallel)

Spawn one `Agent(docs-surface-validator)` per surface in scope, in a single
parallel block. Each call passes the surface name + cached doc paths +
plugin file paths via prompt input. The agent definition itself
(`.claude/agents/docs-surface-validator.md`) carries the validation
protocol; the call site only supplies inputs.

Per-call prompt input shape:

```text
Validate the {surface} surface for docs compatibility.

Cached docs:
- {doc_path_1}
- {doc_path_2}

Plugin files:
- {plugin_path_1}
- {plugin_path_2}

Write findings to .claude/docs-check/reports/{surface}-report.md
```

The named agent's body owns the rest (BLOCKER/WARNING/INFO/PASS
classification, "do not paste large docs" rule, "stop after returning")
so the call site stays minimal.

### 6. Structural baseline (always)

Always keep these results in view while synthesizing:

- `claude plugin validate plugins/ruby-grape-rails` (deterministic)
- basic file existence / JSON / markdown sanity checks

Do not let stale local rules override deterministic validator output.

### 7. Synthesize (main session)

If multiple workers ran:

- verify each expected per-surface report exists at
  `.claude/docs-check/reports/{component_type}-report.md`
- if a worker report is MISSING (write denied, agent crashed, no return):
  synthesize the finding from the worker's Agent return text and write
  the per-surface report yourself from main session. Note "recovered
  from worker return text" in the per-surface artifact.
- read all per-surface reports
- compress repeated evidence
- preserve exact doc-backed incompatibilities
- keep adoption ideas separate from breakage findings

Write the final contributor report to disk at
`.claude/docs-check/report-{YYYY-MM-DD}.md` (today's date). The skill
body owns this final write — workers never write it. Returning findings
only inline is a skill failure — the file is the contract for future
contributors and audit trails.

The report contains: summary, blockers, warnings, infos, follow-up
actions. If a dated existing report disagrees with current cached docs
or current `claude plugin validate` output, mark the older report as
stale instead of copying its warning forward.

## Iron Laws

1. Current cached docs are the source of truth for Claude feature support.
2. `claude plugin validate` remains the deterministic baseline.
3. Prefer targeted cached-doc snippets over pasting full pages into prompts.
4. Distinguish docs incompatibility from local repo recommendations.
5. Treat dated reports under `.claude/docs-check/` as historical snapshots; a
   stale warning in an old report is not current guidance if the cached docs
   and current validator disagree.

## Outputs

Main session MUST persist a contributor report to disk at
`.claude/docs-check/report-<YYYY-MM-DD>.md` (today's date). Returning
findings only inline in the chat response is a skill failure — the file
is the contract for future contributors and audit trails.

The report contains:

- a concise summary
- a clear split between:
  - actual compatibility problems
  - documented new capabilities
  - local repo recommendations that are not schema failures

The plugin's 22 Iron Laws (injected at runtime via `inject-rules.sh`
under `SubagentStart` and `SessionStart`) constrain Ruby/Rails/Grape
code shipped to end users; they do not forbid this contributor report
write.

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
