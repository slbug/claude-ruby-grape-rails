---
name: docs-check
description: |
  CONTRIBUTOR TOOL - Check the plugin against current cached Claude Code docs.
  Use before releases or after Claude docs changes to separate real schema drift
  from stale local assumptions. Not part of the distributed plugin.
argument-hint: "[--quick|--focus=agents|skills|hooks|config]"
---

# Plugin Documentation Compatibility Check

## Audience: Agents, Not Humans

Imperative-only. Validate `plugins/ruby-grape-rails/` against current
cached Claude Code docs. Contributor maintenance — NOT user-facing.

## When to Use

| Question | Answer this skill gives |
|---|---|
| Did Claude docs change in a way that breaks our plugin? | yes |
| Is this warning a real compatibility issue or stale local guidance? | yes |
| What new Claude feature is now documented and relevant? | yes |
| Is naming style / line count / repo preference unrelated to docs? | NO — out of scope |

## Usage

| Command | Scope |
|---|---|
| `/docs-check` | all surfaces |
| `/docs-check --quick` | skip docs fetch, structural drift only |
| `/docs-check --focus=agents` | agents only |
| `/docs-check --focus=skills` | skills only |
| `/docs-check --focus=hooks` | hooks only |
| `/docs-check --focus=config` | plugin manifest + marketplace only |

## Execution Flow

### 1. Run Deterministic Baseline

Run `claude plugin validate plugins/ruby-grape-rails` to catch
structural schema issues without docs interpretation.

### 2. Refresh Cached Docs (Unless `--quick`)

From repo root: `bash ./scripts/fetch-claude-docs.sh`.

`--quick` skips fetching; limits run to structural drift checks against
existing cache.

### 3. Inventory Plugin Surfaces

Identify in-scope surfaces per `--focus`:

| Surface | Paths |
|---|---|
| `agents` | `plugins/ruby-grape-rails/agents/*.md` |
| `skills` | `plugins/ruby-grape-rails/skills/*/SKILL.md` |
| `hooks` | `plugins/ruby-grape-rails/hooks/hooks.json` |
| `config` | `plugins/ruby-grape-rails/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |

Without `--focus`: validate all surfaces.

### 4. Gather Authoritative Inputs

Read:

- `.claude/skills/docs-check/references/validation-rules.md`
- `.claude/skills/docs-check/references/doc-pages.md`

Map each validation question to smallest cached-doc set:

| Surface | Cached docs |
|---|---|
| agents | `plugins-reference.md`, `sub-agents.md` |
| skills | `skills.md`, `hooks.md` (only if skill hooks matter) |
| hooks | `hooks.md`, `hooks-guide.md` |
| config | `plugins-reference.md`, `plugin-marketplaces.md`, `plugins.md`, `mcp.md` (if needed), `settings.md` (if needed) |

Do NOT paste full cached pages into worker prompts.

### 5. Spawn Workers (Parallel)

Spawn one `Agent(docs-surface-validator)` per surface in scope, in a
single parallel block. Pass surface name + cached doc paths + plugin
file paths via prompt input. Agent body
(`.claude/agents/docs-surface-validator.md`) carries the validation
protocol; call site supplies inputs only.

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

Agent body owns BLOCKER/WARNING/INFO/PASS classification, "no large
docs paste" rule, "stop after returning". Call site stays minimal.

### 6. Structural Baseline (Always)

Keep these results in view while synthesizing:

- `claude plugin validate plugins/ruby-grape-rails` (deterministic)
- basic file existence / JSON / markdown sanity checks

Stale local rules MUST NOT override deterministic validator output.

### 7. Synthesize

If multiple workers ran:

1. Verify each per-surface report exists at `.claude/docs-check/reports/{component_type}-report.md`.
2. If a worker report is MISSING (write denied, agent crashed, no
   return) → synthesize from worker's Agent return text and write the
   per-surface report from main session. Note "recovered from worker
   return text" in the per-surface artifact.
3. Read all per-surface reports.
4. Compress repeated evidence.
5. Preserve exact doc-backed incompatibilities.
6. Keep adoption ideas separate from breakage findings.

Write final contributor report at `.claude/docs-check/report-{YYYY-MM-DD}.md`.
Skill body owns this final write — workers never write it. Returning
findings only inline is a skill failure.

Report contains: summary, blockers, warnings, infos, follow-up actions.
If a dated existing report disagrees with current cached docs / current
`claude plugin validate` output → mark older report as stale instead of
copying its warning forward.

## Iron Laws

1. Current cached docs are the source of truth for Claude feature support.
2. `claude plugin validate` is the deterministic baseline.
3. Prefer targeted cached-doc snippets over full pages in prompts.
4. Distinguish docs incompatibility from local repo recommendations.
5. Treat dated reports under `.claude/docs-check/` as historical snapshots — stale warning in old report is not current guidance if cached docs and current validator disagree.

## Outputs

Persist contributor report at `.claude/docs-check/report-{YYYY-MM-DD}.md`.
Returning findings only inline is a skill failure — file is the contract
for future contributors and audit trails.

Report contents:

- concise summary
- split between:
  - actual compatibility problems
  - documented new capabilities
  - local repo recommendations (not schema failures)

The plugin's 22 Iron Laws (injected at runtime via `inject-rules.sh`
under `SubagentStart` and `SessionStart`) constrain Ruby/Rails/Grape
code shipped to end users; they do not forbid this contributor report
write.

## Epistemic Posture

Direct language for drift findings. Docs + plugin incompatible →
state mismatch with exact cached-doc section + exact plugin file:line.
Not "seems stale" or "might be outdated". No apology cascades. Separate
deterministic validator output from subjective repo recommendations;
softer phrasing MUST NOT blur the two.

## References

- `references/validation-rules.md`
- `references/doc-pages.md`
