# Agent Resume Protocol

Spawn-fanout skill body MUST follow this protocol when an agent
pauses at `maxTurns` before producing its artifact.

## Pause signature

Agent paused at turn cap when ALL true in tool-result return text:

1. Contains `agentId: <id>` + `use SendMessage with to: '<id>' to continue this agent`.
2. Artifact path missing OR `< 1000 bytes`.
3. Reported `tool_uses` near agent's frontmatter `maxTurns`.

## Protocol

When signature detected:

1. If `SendMessage` tool unavailable in this session: skip resume.
   Emit user-visible warning naming the agent slug. Mark agent
   `stub-no-output`. Stop.

2. Call `SendMessage` once:
   - `to`: agentId from pause hint.
   - Prompt: `Continue. Save findings to <absolute-path> before
     stopping. Final turn MUST call Write.` Substitute
     `<absolute-path>` with manifest's per-agent path.

3. Wait for resumed agent return.

4. Re-apply calling skill's Artifact Recovery state machine on
   post-resume filesystem state. Final per-agent status: `complete` |
   `stub-replaced` | `recovered-from-return` | `stub-no-output`.

5. NEVER call `SendMessage` twice for the same agent in one run.
   If resumed agent paused again, mark `stub-no-output`.

## Constraint

Agent bodies MUST call `Write` only on final turn(s). Subagents
cannot overwrite existing files. Early `Write` blocks refinement.
Resume Protocol assumes pause occurred before final `Write`.
