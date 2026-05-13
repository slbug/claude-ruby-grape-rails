# Skill-Discovery Telemetry

Opt-in observation layer. Logs pattern-matched skill-suggestion candidates
from hook event inputs. Default OFF. Drives future tuning of the
intent-detection routing table.

## Opt-in

| Env var | Effect |
|---|---|
| `RUBY_PLUGIN_DISCOVERY_LOG=1` | Log metadata only (hook event, command, matched rule id, suggested skill, timestamp). Default OFF. |
| `RUBY_PLUGIN_DISCOVERY_LOG_EXCERPTS=1` | When `RUBY_PLUGIN_DISCOVERY_LOG=1` is also set, additionally include a 200-char redacted excerpt of the matched extractor field. Default OFF. |

## Privacy posture

- Excerpts: trimmed to 200 chars; `/Users/<name>` and `/home/<name>` paths replaced with `<redacted>`; uppercase `KEY=value` env-style tokens stripped.
- File mode `0o600` on `discovery.jsonl` and `discovery-cache.json` — owner-only read/write.
- No `additionalContext` injection. Log only — never modifies the hook chain or alters Claude's session.
- Fail-open: any error in the observer → silent `exit 0`; never blocks tool execution.

## Files

- `${CLAUDE_PLUGIN_DATA}/discovery.jsonl` — append-only log; rotates to `discovery.jsonl.N` when it exceeds 5 MiB.
- `${CLAUDE_PLUGIN_DATA}/discovery.jsonl.N` — rotated logs (numeric suffix).
- `${CLAUDE_PLUGIN_DATA}/discovery-cache.json` — throttle-simulation state (per-session-per-skill match counts). Used to compute `would_throttle` flags; never blocks logging.

## Report

Run `/rb:discovery-report` to draft a report from collected telemetry. The report skill is `disable-model-invocation: true` — invoke manually.

## Schema

Each row of `discovery.jsonl`:

```json
{
  "ts": "2026-05-14T12:00:00Z",
  "session_id": "<uuid>",
  "hook_event": "PostToolUse",
  "matched_rule": "rb-sidekiq-job-file-touched",
  "suggest": "sidekiq",
  "reason": "Job file touched — Sidekiq idempotency patterns available",
  "would_inject": true,
  "would_inject_chars": 124,
  "would_throttle": false,
  "throttle_reason": null,
  "session_skill_count": 3,
  "excerpt": "<only when RUBY_PLUGIN_DISCOVERY_LOG_EXCERPTS=1>"
}
```

Field meanings:

| Field | Purpose |
|---|---|
| `would_inject` | Would the active-injection layer (future spec) inject this match? Always `true` in current log-only layer. |
| `would_inject_chars` | Char count the active layer would have added to `additionalContext` (capped at 200). |
| `would_throttle` | `true` once the per-session-per-skill match count exceeds the cap (default 20). |
| `throttle_reason` | Human-readable explanation when `would_throttle` is `true`. |
| `session_skill_count` | Running count of matches for this (session_id, suggest) pair. |

When a rule's `suggest_list` carries multiple skills, the observer writes one row per skill so analytics can track each independently.
