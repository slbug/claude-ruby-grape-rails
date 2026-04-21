---
name: session-deep-dive
description: Deep qualitative review of high-signal sessions. Use after /session-scan to inspect transcripts, validate heuristic metrics, and synthesize contributor-facing findings.
argument-hint: "<session-id> | --last | --from-scan [--provider NAME] [--compare PATH]"
disable-model-invocation: true
---

# Session Deep Dive (Tier 2)

Qualitative analysis for sessions identified by `/session-scan`.

This workflow exists to validate or falsify scan heuristics with actual
transcript evidence. It is not a replacement for deterministic evals.

## Requirements

- `ccrider` CLI on PATH (for full transcript export — not MCP)
- readable local ccrider SQLite DB (session-scan resolves the path; reuse
  the same resolution order here)
- populated `.claude/session-metrics/metrics.jsonl` from `/session-scan`

If the ledger does not exist, tell the contributor to run `/session-scan`
first. If `ccrider` is not on PATH, ask the contributor to install it
(<https://github.com/neilberkman/ccrider>) before continuing.

## Usage

```text
/session-deep-dive SESSION_ID
/session-deep-dive --last
/session-deep-dive --from-scan
/session-deep-dive --from-scan --provider claude-code
/session-deep-dive --compare .claude/session-analysis/insights-2026-03-20.md
```

## Workflow

### 1. Resolve Target Sessions

Supported selectors:

- explicit session ID
- `--last`
- `--from-scan`
- optional `--provider NAME`
- optional `--compare PATH`

If `--provider` is present, only analyze ledger entries whose `provider` field
matches that value.

### 2. Load Existing Metrics as Hints

For each target session, load its ledger entry and treat these values as
starting hypotheses:

- friction score
- fingerprint
- plugin opportunity score
- tool profile
- skill-effectiveness hints

Do not assume they are correct until transcript evidence supports them.

### 3. Export Transcripts via ccrider CLI

Use the `ccrider export` command — no MCP, no truncation, full session.
Per target, run `mkdir -p .claude/session-analysis` and then
`ccrider export SESSION_ID --output .claude/session-analysis/{short_id}-transcript.md`.

Each exported file contains the complete session markdown with all user,
assistant, and tool messages. Main context does not need to read these
files — only the later analysis subagent does.

For multiple sessions, loop over the selected session IDs and invoke
`ccrider export` once per ID. This avoids loading transcript bytes into
main-context tool output.

### 4. Analyze Each Session with the Shared Template

Read:

- `${CLAUDE_SKILL_DIR}/references/analysis-template-v2.md`

Then spawn one analysis subagent per transcript. Include:

- transcript path
- the pre-computed metrics block
- explicit instruction to mark evidence strength
- reminder that the metrics are heuristic

Write each report to:

- `.claude/session-analysis/{short_id}-report.md`

### 5. Compress When Needed

If you have 3 or more per-session reports, compress them before synthesis.

Keep:

- repeatable friction patterns
- repeated plugin-opportunity signals
- evidence-strength notes
- contradictions between metrics and transcript reality

### 6. Synthesize Carefully

Read:

- `${CLAUDE_SKILL_DIR}/references/synthesis-template.md`

Compare the current session reports against:

- previous synthesis reports, if present
- the contributor-provided `--compare` file, if present
- recent deterministic signals such as `lab/eval`, if they are relevant

Do not depend on missing local artifacts like `MEMORY.md` or old report files.

### 7. Mark Deep-Dive Completion

When updating `metrics.jsonl`, use a scripted update path. Do not hand-edit
JSONL in the prompt.

### 8. Write Output

Write:

- per-session reports
- optional consolidated summary
- final synthesis:
  - `.claude/session-analysis/insights-{date}.md`

## Iron Laws

1. Transcript-derived metrics are hints, not proof.
2. Export full transcripts via `ccrider export`; do not rely on MCP
   `get_session_messages` (it truncates large sessions).
3. One analysis subagent per session (haiku or sonnet). The subagent reads
   the exported markdown file; main context does not.
4. Validate scan heuristics against actual transcript evidence.
5. Avoid missing local dependencies such as `MEMORY.md`.
6. Keep synthesis grounded in tracked files and explicit contributor notes.
7. Cite evidence strength for every meaningful finding.

## Epistemic Posture

Session analytics report patterns directly. If a transcript shows a
real friction pattern, state it plainly with the transcript-line
evidence, don't soften into "the assistant may have struggled". Low-
evidence observations stay explicitly LOW-confidence rather than
padded into confident language. Apology cascades and hedge chains
inflate reports without signal — avoid them.
