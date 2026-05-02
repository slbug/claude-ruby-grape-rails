# Run Manifest

Cross-session resume contract for parallel-fanout workflows.

## Path Convention

- Active manifest: `.claude/{namespace}/{slug}/RUN-CURRENT.json`
- Archive log: `.claude/{namespace}/{slug}/RUN-HISTORY.jsonl` (append-only)

Namespaces:

| Skill | Namespace | Slug source |
|---|---|---|
| `/rb:review` | `reviews` | `{review-slug}` |
| `/rb:plan` (fanout) | `plans/{plan-slug}` | `research-fanout` |
| `/rb:full` | `plans/{plan-slug}` | `full-cycle` |

## Schema

```json
{
  "skill": "rb:review",
  "slug": "feat-add-passport",
  "datesuffix": "20260502-153000",
  "branch": "feat/add-passport",
  "branch_head_sha": "abc123def456...",
  "base_ref": "origin/main",
  "base_sha": "789abc012def...",
  "started_at": "2026-05-02T15:30:00Z",
  "updated_at": "2026-05-02T15:31:42Z",
  "status": "in-flight",
  "agents": {
    "ruby-reviewer": {
      "path": ".claude/reviews/ruby-reviewer/feat-add-passport-20260502-153000.md",
      "status": "complete"
    },
    "iron-law-judge": {
      "path": ".claude/reviews/iron-law-judge/feat-add-passport-20260502-153000.md",
      "status": "in-flight"
    }
  },
  "consolidated_path": ".claude/reviews/feat-add-passport-20260502-153000.md"
}
```

Required fields: `skill`, `slug`, `datesuffix`, `branch`,
`branch_head_sha`, `base_ref`, `base_sha`, `started_at`, `updated_at`,
`status`, `agents`.

`status` enum: `in-flight` | `complete` | `archived`.

Per-agent `status` enum: `pending` | `in-flight` | `complete` |
`stub-replaced` | `recovered-from-return` | `stub-no-output`.

## Lifecycle

### Run start

Main session:

1. Resolve `base_ref`, `base_sha`, `branch`, `branch_head_sha`.
2. Generate `datesuffix = date -u +%Y%m%d-%H%M%S`.
3. Read existing `RUN-CURRENT.json` if present.
4. If present and stale (see Staleness): archive to `RUN-HISTORY.jsonl`,
   delete `RUN-CURRENT.json`.
5. If present and fresh: prompt user — "found in-flight run from
   `{updated_at}`, resume or start fresh?". Default = **fresh**.
6. On resume: reuse `datesuffix` + `agents` map; skip already-complete agents.
7. On fresh: build new manifest, set `status: in-flight`,
   `started_at = updated_at = now`, all agent `status: pending`.
8. Write `RUN-CURRENT.json` via
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update init <path> '<json>'`.

### Per-agent spawn

Before spawning each agent, mark its status in-flight:

```bash
echo '{"agents":{"<agent-slug>":{"status":"in-flight"}}}' \
  | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch <path>
```

Helper auto-stamps `updated_at`. Pass the agent's `path` from
manifest verbatim into the spawn prompt.

### Post-recovery

After Artifact Recovery decides each agent's outcome, patch its
`status` to one of `complete`, `stub-replaced`, `recovered-from-return`,
or `stub-no-output`:

```bash
echo '{"agents":{"<agent-slug>":{"status":"<state>"}}}' \
  | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch <path>
```

### Run complete

After consolidated artifact is written:

```bash
echo '{"status":"complete"}' \
  | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch <path>
```

The completed manifest stays at `RUN-CURRENT.json` until the next run
starts. Next-run start archives it via
`${CLAUDE_PLUGIN_ROOT}/bin/manifest-update archive <path>` (regardless
of staleness verdict — completed manifests are archived too) and
clears the active slot.

## Staleness

Stale = ANY of:

1. TTL: `now - updated_at > 24h` (override `RUN_MANIFEST_TTL_HOURS`, min 1h).
2. HEAD drift: `git rev-parse HEAD` ≠ manifest `branch_head_sha`.
3. Base drift: current `base_sha` ≠ manifest `base_sha`.
4. Branch switch: current branch ≠ manifest `branch`.

Decision matrix:

| State | Action |
|---|---|
| stale | archive to `RUN-HISTORY.jsonl`, fresh run, no prompt |
| fresh + `complete` | archive, fresh run |
| fresh + `in-flight` | prompt user, default fresh |
| absent | fresh run |

## Atomic Write

All manifest mutations go through `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update`.
Skill bodies and main session NEVER call raw `mv`, `jq -i`, or `cp` against
manifest paths.

Subcommands:

```bash
# Create manifest (fails if exists). JSON literal as second arg.
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update init   <path> '<initial-json>'

# Deep-merge JSON from stdin. Auto-stamps updated_at.
echo '<patch-json>' | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch <path>

# Append current state to RUN-HISTORY.jsonl, unlink RUN-CURRENT.json.
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update archive <path>

# One-line summary (read-only).
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update status <path>
```

Helper enforces:

- Path allowlist: `<...>/.claude/<ns>/<slug>/RUN-CURRENT.json` only.
  Any other path → exit 1 before touching disk.
- Symlink refusal on target and parent dir.
- JSON validation on input AND merged result.
- Atomic rename via Ruby `File.rename` (POSIX `rename(2)`), preceded
  by `fsync` of the temp file and followed by directory `fsync`.
- Tmp-file cleanup on failure (`ensure` block).
- Fail-closed: any error exits non-zero before disk mutation.

## Agent Boundary

- Agents NEVER read the manifest.
- Agents NEVER write the manifest.
- Main session owns all manifest reads + writes.
- Agents receive their `path` via spawn prompt and write to that path only.

## Applicability

| Skill | Status | Staleness rules |
|---|---|---|
| `/rb:review` | Active | TTL + HEAD + base + branch |
| `/rb:plan` (research fanout) | Deferred | Stable canonical paths + multi-day iterative work; needs TTL-only policy |
| `/rb:full` | Deferred | Inherits review + plan |
| `/rb:work` | N/A | Single-author |
| `/rb:verify` | N/A | Subprocess, no agent fanout |
| `/rb:compound` | N/A | Single-author |
| `/rb:brainstorm` | N/A | Single-agent |

## Resume Protocol (main session)

Reads via `jq`. Writes via `bin/manifest-update`.

```bash
MANIFEST="${REPO_ROOT}/.claude/${NAMESPACE}/${SLUG}/RUN-CURRENT.json"

if [[ -f "$MANIFEST" ]]; then
  STATUS=$(jq -r '.status' "$MANIFEST")
  UPDATED=$(jq -r '.updated_at' "$MANIFEST")
  HEAD_PIN=$(jq -r '.branch_head_sha' "$MANIFEST")
  BASE_PIN=$(jq -r '.base_sha' "$MANIFEST")
  BRANCH_PIN=$(jq -r '.branch' "$MANIFEST")

  CUR_HEAD=$(git rev-parse HEAD)
  CUR_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  AGE_S=$(( $(date -u +%s) - $(date -u -d "$UPDATED" +%s 2>/dev/null || echo 0) ))
  TTL_S=$(( ${RUN_MANIFEST_TTL_HOURS:-24} * 3600 ))

  if [[ "$CUR_HEAD" != "$HEAD_PIN" || "$CUR_BRANCH" != "$BRANCH_PIN" \
        || "$BASE_SHA" != "$BASE_PIN" || $AGE_S -gt $TTL_S ]]; then
    "${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" archive "$MANIFEST"
  elif [[ "$STATUS" == "in-flight" ]]; then
    # Prompt user; default fresh
    :
  fi
fi
```

## Implementation Notes

- `jq` required for reads.
- `RUN-HISTORY.jsonl` git-ignored by default; project may add explicit gitignore exception.
- Concurrent CC sessions on same branch race on `RUN-CURRENT.json`. No cross-process lock. Constraint: one workflow per branch at a time.
