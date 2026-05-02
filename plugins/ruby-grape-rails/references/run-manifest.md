# Run Manifest

Cross-session resume contract for parallel-fanout workflows.

## Path Convention

- Active manifest: `.claude/{namespace}/{slug}/RUN-CURRENT.json`
- Archive log: `.claude/{namespace}/{slug}/RUN-HISTORY.jsonl` (append-only)

Namespaces (path fragment under `.claude/`):

| Skill | Namespace | Slug source |
|---|---|---|
| `/rb:review` | `reviews/{review-slug}` | `{review-slug}` |
| `/rb:plan` (fanout) | `plans/{plan-slug}/research-fanout` | `research-fanout` |
| `/rb:brainstorm` | `plans/{plan-slug}/brainstorm-fanout` | `brainstorm-fanout` |

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
      "path": "/abs/repo/.claude/reviews/ruby-reviewer/feat-add-passport-20260502-153000.md",
      "status": "complete"
    },
    "iron-law-judge": {
      "path": "/abs/repo/.claude/reviews/iron-law-judge/feat-add-passport-20260502-153000.md",
      "status": "in-flight"
    }
  },
  "consolidated_path": "/abs/repo/.claude/reviews/feat-add-passport-20260502-153000.md"
}
```

Required fields (all skills): `skill`, `slug`, `datesuffix`,
`started_at`, `updated_at`, `status`, `agents`.

Required fields (review only — git-pinned skills): `branch`,
`branch_head_sha`, `base_ref`, `base_sha`. Optional for plan +
brainstorm (TTL-only staleness).

`base_sha` = output of `git merge-base HEAD "$BASE_REF"` at run start.
Stored to detect rebase drift on resume.

`status` enum: `in-flight` | `complete` | `archived`.

Per-agent `status` enum: `pending` | `in-flight` | `complete` |
`stub-replaced` | `recovered-from-return` | `stub-no-output`.

`agents.*.path` and `consolidated_path` MUST be absolute paths
(matches what main session passes to spawn prompts). Helper accepts
both forms for `prepare-respawn` backward-compatibility, but new
manifests use absolute.

## Lifecycle

### Run start

Main session:

1. Resolve `base_ref`, `base_sha`, `branch`, `branch_head_sha`.
2. Generate `datesuffix = date -u +%Y%m%d-%H%M%S`.
3. Build initial manifest JSON with `status: in-flight`, all agent
   `status: pending`.
4. Run
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run <path>
   --base="$MERGE_BASE" --initial-json="$INITIAL_JSON"`. Helper archives
   any prior manifest (stale, complete, or in-flight) and inits the
   fresh one in a single call.

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

Per-skill rules:

| Skill | TTL default | HEAD pin | Base pin | Branch pin |
|---|---|---|---|---|
| `/rb:review` | 24h | yes | yes | yes |
| `/rb:plan` | 168h (7d) | no | no | no |
| `/rb:brainstorm` | 168h (7d) | no | no | no |

Stale = ANY applicable rule triggers:

1. TTL: `now - updated_at > <skill TTL>` (override `RUN_MANIFEST_TTL_HOURS`, min 1h).
2. HEAD drift: `git rev-parse HEAD` ≠ manifest `branch_head_sha` (review only).
3. Base drift: current `base_sha` ≠ manifest `base_sha` (review only).
4. Branch switch: current branch ≠ manifest `branch` (review only).

Decision matrix (single-call `prepare-run` semantics):

| State | Action |
|---|---|
| absent | init fresh |
| stale | archive to `RUN-HISTORY.jsonl`, init fresh |
| fresh + `complete` | archive, init fresh |
| fresh + `in-flight` | archive, init fresh (one-workflow-per-branch constraint) |

Callers that want to surface in-flight state to the user before
starting a new run can invoke `resume-check` (read-only inspector)
first, prompt, then call `prepare-run` to commit.

## Atomic Write

All manifest mutations and stale-stub unlinks go through
`${CLAUDE_PLUGIN_ROOT}/bin/manifest-update`. Skill bodies and main
session NEVER call raw `mv`, `cp`, `rm`, or `jq -i` against manifest
or per-agent artifact paths.

Subcommands:

```bash
# Archive any existing manifest + init fresh from JSON. Single call
# replaces verdict + case dispatch. Default for spawn-fanout skills.
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run <path> \
  --base="$MERGE_BASE" --initial-json='<initial-json>'

# Create manifest (fails if exists). JSON literal as second arg.
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update init <path> '<initial-json>'

# Deep-merge JSON from stdin. Auto-stamps updated_at.
echo '<patch-json>' | ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch <path>

# Unlink stale stubs at manifest-tracked agent paths before re-spawn.
# Only unlinks files < 1000 bytes (real artifacts protected with warning).
# Only touches paths listed in manifest.agents.*.path.
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-respawn <path>

# Append current state to RUN-HISTORY.jsonl, unlink RUN-CURRENT.json.
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update archive <path>

# Read-only verdict (absent | stale | fresh-complete | fresh-in-flight).
${CLAUDE_PLUGIN_ROOT}/bin/manifest-update resume-check <path> [--base=SHA]

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
- `prepare-respawn` only unlinks files (a) listed in
  `manifest.agents.*.path`, (b) under `.claude/`, (c) below 1000 bytes,
  and (d) only when agent status is `pending` / `in-flight` /
  `stub-no-output`. Real artifacts are skipped with a warning.
- Fail-closed: any error exits non-zero before disk mutation.

## Agent Boundary

- Agents NEVER read the manifest.
- Agents NEVER write the manifest.
- Main session owns all manifest reads + writes.
- Agents receive their `path` via spawn prompt and write to that path only.

## Applicability

| Skill | Status | Namespace | Staleness rules |
|---|---|---|---|
| `/rb:review` | Active | `reviews/{review-slug}` | TTL + HEAD + base + branch |
| `/rb:plan` (research fanout) | Active | `plans/{plan-slug}/research-fanout` | TTL only (research iterates across days) |
| `/rb:brainstorm` | Active | `plans/{plan-slug}/brainstorm-fanout` | TTL only |
| `/rb:full` | N/A | — | Orchestrator; reads phase manifests, owns none |
| `/rb:work` | N/A | — | Tracks via plan `progress.md`, not manifest |
| `/rb:verify` | N/A | — | Subprocess, no agent fanout |
| `/rb:compound` | N/A | — | Single-author |
| `/rb:investigate`, `/rb:trace` | N/A | — | Single-agent dispatch |

## Resume Protocol (main session)

Single helper call. `prepare-run` archives any existing manifest
(stale, complete, or in-flight) and inits a fresh one with the
provided JSON. No bash branches.

```bash
MANIFEST="${REPO_ROOT}/.claude/${NAMESPACE}/${SLUG}/RUN-CURRENT.json"
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" prepare-run "$MANIFEST" \
  --base="$MERGE_BASE" --initial-json="$INITIAL_JSON"
```

`resume-check` (read-only inspector) is still available for callers
that want to surface in-flight state to the user before deciding.

## Implementation Notes

- `RUN-HISTORY.jsonl` git-ignored by default; project may add explicit gitignore exception.
- Concurrent CC sessions on same branch race on `RUN-CURRENT.json`. No cross-process lock. Constraint: one workflow per branch at a time.
