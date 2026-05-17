# Agent Resume Protocol

Spawn-fanout skill body protocol for agents that paused at `maxTurns`
before producing an artifact.

## Prerequisite

`SendMessage` requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

- Flag absent → tool unloaded; `ToolSearch select:SendMessage` empty.
- Flag absent → fall through to filesystem + return-text path. Write-capable
  agent paused mid-task is unrecoverable; mark `stub-no-output`.
- Flag set + Write-capable agent paused → resume preferred.
- Flag exposure documented in `/rb:intro`.

## Return-text cap

Subagent final-message return text is hard-capped at 32K output tokens
(~24K words ≈ ~120-150KB markdown). Cap is hardcoded in Claude Code;
not configurable via `CLAUDE_CODE_MAX_OUTPUT_TOKENS`.

Implications:

- Write-capable agent: artifact content rides Write tool call → file,
  not return text. Cap does not bound artifact size.
- Convo-only agent: artifact content rides return text. Cap bounds artifact.
  Oversized return truncates → recovery sees partial markdown.
- `SendMessage` resume does NOT bypass cap. Next stop is still bound.

## Pause signature

Pause when ALL true in return text:

1. Contains `agentId: <id>` + `use SendMessage with to: '<id>' to continue this agent`.
2. Artifact path missing OR `< 1000 bytes`.
3. Reported `tool_uses` near agent's frontmatter `maxTurns`.

## Agent classification

| Class | Detection | Resume value | Primary recovery |
|---|---|---|---|
| Write-capable | denylist style; `Write` NOT in `disallowedTools` | High — finishes proper Write to canonical path | `SendMessage` resume |
| Convo-only | allowlist `tools:` without `Write` (`web-researcher`, `ruby-gem-researcher`, `output-verifier`) | Zero — no Write tool to call | Return-text extraction |

## Protocol

When pause signature matches:

1. Classify agent (table above).
2. Write-capable + `SendMessage` available → call ONCE:
   - `to`: agentId from pause hint.
   - Prompt: `Continue. Save findings to <absolute-path> before stopping.
     Final turn MUST call Write.` Substitute path from manifest.
   - After resume returns → re-apply step 4 on post-resume filesystem state.
3. Write-capable + `SendMessage` unavailable → skip resume; fall through to step 4.
4. Convo-only → skip resume; fall through to step 4.
5. Filesystem + return-text state machine (calling skill's Artifact
   Recovery section). Output: `artifact` | `stub-replaced` |
   `recovered-from-return` | `stub-no-output`.
6. NEVER call `SendMessage` twice for the same agent in one run.
   Re-paused → fall through to step 5.

## Constraint

Write-capable agents call `Write` only on final turn(s). Subagents
cannot overwrite existing files; early `Write` blocks refinement.
Resume protocol assumes pause occurred before final `Write`. Convo-only
agents never call `Write`; return-text extraction IS the contract.
