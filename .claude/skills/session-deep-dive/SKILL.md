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

Requires `ccrider` MCP and a populated `.claude/session-metrics/metrics.jsonl`.

If the ledger does not exist, tell the contributor to run `/session-scan`
first.

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

### 3. Fetch One Transcript Per Subagent

Use one subagent per session. Main context should not pull multiple full
transcripts directly.

Use `Agent(...)`, not historical `Task(...)`, in contributor prompts.

Each fetch subagent should:

1. call ccrider for one session
2. write the transcript to `.claude/session-analysis/{short_id}-transcript.md`
3. report the transcript path and message count

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
2. Use one transcript-fetch subagent per session.
3. Validate scan heuristics against actual transcript evidence.
4. Avoid missing local dependencies such as `MEMORY.md`.
5. Keep synthesis grounded in tracked files and explicit contributor notes.
6. Cite evidence strength for every meaningful finding.

## Epistemic Posture

Session analytics report patterns directly. If a transcript shows a
real friction pattern, state it plainly with the transcript-line
evidence, don't soften into "the assistant may have struggled". Low-
evidence observations stay explicitly LOW-confidence rather than
padded into confident language. Apology cascades and hedge chains
inflate reports without signal — avoid them.
