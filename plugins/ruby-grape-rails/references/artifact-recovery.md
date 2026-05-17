# Artifact Recovery State Machine

Shared by `/rb:plan`, `/rb:review`, `/rb:brainstorm`, `/rb:research`.
Applied per manifest agent entry after fanout completes.

## Order

1. **CHECK pause signature first** per sibling `agent-resume.md`. If
   matched, apply that protocol (resume via `SendMessage` if
   available, else mark `stub-no-output`). State machine below applies
   ONLY after the resume attempt resolves or is skipped.

2. **STAT the expected path.** Read agent paths via:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update spawn-paths "$MANIFEST"
```

## State machine

| Filesystem state | Action | Manifest `status` |
|---|---|---|
| Exists, `size_bytes >= 1000` | Trust. Do NOT overwrite. | `artifact` |
| Exists, `size_bytes < 1000`, return text substantially larger AND parses as findings | Replace stub with extracted content. Add header `recovery: stub replaced from inline return`. | `stub-replaced` |
| Exists, `size_bytes < 1000`, return text empty/unusable | Keep stub. Add header `recovery: stub kept — return text unusable`. Treat as coverage gap. | `stub-no-output` |
| Missing, return text usable | Extract content from return text and write. Add header `recovery: recovered from inline return — Write failed`. | `recovered-from-return` |
| Missing, return text empty/unusable | Write stub with heading `# {agent-slug} — recovery stub` and body `Run produced no artifact and no usable return text. {Coverage-noun} coverage gap.` Add header `recovery: stub written — agent produced nothing`. | `stub-no-output` |

`{agent-slug}` = manifest entry key (review: reviewer subagent_type;
plan/brainstorm: research topic; research: aspect identifier).

`{Coverage-noun}` per skill:

| Skill | Coverage-noun |
|---|---|
| `/rb:review` | `Reviewer` |
| `/rb:plan` | `Research` |
| `/rb:brainstorm` | `Research` |
| `/rb:research` | `Aspect` |

## Rules

- Decide from the filesystem, not Agent return-text claims.
- NEVER copy or symlink prior-run artifacts to the current-run path.
- Never re-spawn.
- After each entry's recovery decision, patch its `status`:

```bash
printf '{"agents":{"%s":{"status":"%s"}}}\n' "$AGENT_SLUG" "$STATE" \
  | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch "$MANIFEST"
```

NEVER edit `RUN-CURRENT.json` directly.

- Synthesis runs on the verified manifest.
