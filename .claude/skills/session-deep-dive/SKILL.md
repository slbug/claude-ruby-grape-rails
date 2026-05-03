---
name: session-deep-dive
description: Deep qualitative review of high-signal sessions. Use after /session-scan to inspect transcripts, validate heuristic metrics, and synthesize contributor-facing findings.
argument-hint: "<session-id> | --last | --from-scan [--provider NAME] [--compare PATH]"
disable-model-invocation: true
---

# Session Deep Dive (Tier 2)

## Audience: Agents, Not Humans

Imperative-only. NOT a replacement for deterministic evals.

## Requirements

- `ccrider` CLI on PATH (full transcript export; resolves DB path internally)
- populated `.claude/session-metrics/metrics.jsonl` from `/session-scan`

| Missing | Action |
|---|---|
| ledger | tell contributor to run `/session-scan` first |
| `ccrider` not on PATH | ask contributor to install (<https://github.com/neilberkman/ccrider>) |

## Usage

| Command | Behavior |
|---|---|
| `/session-deep-dive SESSION_ID` | analyze explicit session ID |
| `/session-deep-dive --last` | most recent session |
| `/session-deep-dive --from-scan` | sessions flagged by latest scan |
| `/session-deep-dive --from-scan --provider <NAME>` | scoped to provider |
| `/session-deep-dive --compare .claude/session-analysis/insights-2026-03-20.md` | comparison reference |

## Workflow

### 1. Resolve Target Sessions

Selectors: explicit session ID, `--last`, `--from-scan`, optional
`--provider NAME`, optional `--compare PATH`.

`--provider` present → only analyze ledger entries with matching `provider` field.

### 2. Load Existing Metrics as Hints

For each target session, load ledger entry. Treat these values as
starting hypotheses (NOT ground truth):

- friction score
- fingerprint
- plugin opportunity score
- tool profile
- skill-effectiveness hints

Confirm with transcript evidence before relying on them.

### 3. Export Transcripts via ccrider CLI

Use `ccrider export` — no MCP, no truncation, full session.

Per target:

1. `mkdir -p .claude/session-analysis`
2. `ccrider export SESSION_ID --output .claude/session-analysis/{short_id}-transcript.md`

Each exported file = complete session markdown (user, assistant, tool
messages). Main context does NOT read these files — only the analysis
subagent does.

Multiple sessions → loop selected IDs, invoke `ccrider export` per ID.
Avoids loading transcript bytes into main-context tool output.

### 4. Analyze Each Session

Read `${CLAUDE_SKILL_DIR}/references/analysis-template-v2.md`.

Spawn one analysis subagent per transcript. Include:

- transcript path
- pre-computed metrics block
- explicit instruction to mark evidence strength
- reminder that metrics are heuristic

Write each report to `.claude/session-analysis/{short_id}-report.md`.

### 5. Compress When Needed

3+ per-session reports → compress before synthesis. Keep:

- repeatable friction patterns
- repeated plugin-opportunity signals
- evidence-strength notes
- contradictions between metrics and transcript reality

### 6. Synthesize

Read `${CLAUDE_SKILL_DIR}/references/synthesis-template.md`.

Compare current session reports against:

- previous synthesis reports (if present)
- `--compare` file (if present)
- recent deterministic signals (`lab/eval`) when relevant

Do NOT depend on missing local artifacts (`MEMORY.md`, old report files).

### 7. Mark Deep-Dive Completion

Use scripted update path for `metrics.jsonl`. Do NOT hand-edit JSONL in
the prompt.

### 8. Write Output

- per-session reports
- optional consolidated summary
- final synthesis: `.claude/session-analysis/insights-{date}.md`

## Iron Laws

1. Transcript-derived metrics are hints, not proof.
2. Export full transcripts via `ccrider export`; do NOT use MCP `get_session_messages` (truncates large sessions).
3. One analysis subagent per session (haiku or sonnet). Subagent reads exported markdown; main context does NOT.
4. Validate scan heuristics against actual transcript evidence.
5. Avoid missing local dependencies (`MEMORY.md`).
6. Keep synthesis grounded in tracked files + explicit contributor notes.
7. Cite evidence strength for every meaningful finding.

## Epistemic Posture

Direct language for transcript-evidenced findings. State patterns
plainly with transcript-line evidence — do NOT soften into "the
assistant may have struggled". LOW-evidence observations stay
explicitly LOW-confidence. No apology cascades, no hedge chains.
