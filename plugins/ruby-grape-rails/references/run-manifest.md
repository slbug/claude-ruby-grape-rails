# Run Manifest

Cross-session resume contract for parallel-fanout workflows.

## Path Convention

- Active manifest: `.claude/{namespace}/RUN-CURRENT.json`
- Archive log: `.claude/{namespace}/RUN-HISTORY.jsonl` (append-only)

`{namespace}` is the per-skill path fragment under `.claude/`. It
already includes the skill-specific slug (review-slug for reviews,
plan-slug for plan/brainstorm), so the manifest path has no
additional `{slug}` segment.

| Skill | `{namespace}` |
|---|---|
| `/rb:review` | `reviews/{review-slug}` |
| `/rb:plan` (fanout) | `plans/{plan-slug}/research-fanout` |
| `/rb:brainstorm` | `plans/{plan-slug}/brainstorm-fanout` |

Resolved manifest paths:

- `/rb:review`: `.claude/reviews/{review-slug}/RUN-CURRENT.json`
- `/rb:plan`: `.claude/plans/{plan-slug}/research-fanout/RUN-CURRENT.json`
- `/rb:brainstorm`: `.claude/plans/{plan-slug}/brainstorm-fanout/RUN-CURRENT.json`

Per-agent artifact paths (computed by helper):

| Skill | Agent path template | Naming |
|---|---|---|
| `/rb:review` | `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md` | per-second-unique snapshot |
| `/rb:plan` | `.claude/plans/{plan-slug}/research/{agent-slug}.md` | stable canonical (no datesuffix; iterative across days) |
| `/rb:brainstorm` | `.claude/plans/{plan-slug}/research/{agent-slug}.md` | stable canonical |

Consolidated artifact paths (computed by helper, exposed as
`consolidated_path` field):

| Skill | Consolidated path |
|---|---|
| `/rb:review` | `.claude/reviews/{review-slug}-{datesuffix}.md` |
| `/rb:plan` | `.claude/plans/{plan-slug}/plan.md` |
| `/rb:brainstorm` | `.claude/plans/{plan-slug}/interview.md` |

`{agent-slug}` is the manifest entry key — for review it equals the
subagent_type (e.g. `ruby-reviewer`); for plan/brainstorm it equals
the research topic identifier (e.g. `active-record-patterns`).

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
`status`, `agents`, `consolidated_path`, `started_at`, `updated_at`.

Required fields (review only — git-pinned skills): `branch`,
`branch_head_sha`, `base_ref`, `base_sha`. Omitted for plan +
brainstorm (TTL-only staleness).

`base_sha` = output of `git merge-base HEAD "$BASE_REF"` at run start.
Stored to detect rebase drift on resume.

`status` enum: `in-flight` | `complete`.

Per-agent `status` enum: `pending` | `in-flight` | `complete` |
`stub-replaced` | `recovered-from-return` | `stub-no-output`.

`agents.*.path` and `consolidated_path` are absolute paths populated
by `bin/manifest-update prepare-run` (helper computes from skill +
slug + datesuffix per skill convention).

## Lifecycle

### Run start

Main session calls `prepare-run` once with structured args. Helper
computes everything: manifest path, datesuffix, agent paths,
consolidated path, git pins. Outputs absolute manifest path.

```bash
MANIFEST=$("${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" prepare-run \
  --skill=rb:review --slug="$SLUG" \
  --base-ref="$BASE_REF" \
  --agents="$AGENTS_CSV")
```

`$AGENTS_CSV` is computed by the calling skill at runtime from its
selection logic (e.g. `/rb:review` derives it from the Reviewer
Selection Matrix in `skills/review/SKILL.md`). It is NOT a fixed
default in the helper — every spawn-fanout skill computes its own
list per its own rules.

Plan/brainstorm omit `--base-ref` (TTL-only). For plan, agent slugs
are research topic identifiers (helper uses them as filename stems
under `.claude/plans/<slug>/research/<topic>.md`).

### Read agent paths

Skill body iterates `manifest-update spawn-paths "$MANIFEST"` to get
`<agent-slug>\t<absolute-path>` pairs. Pass the absolute path verbatim
in the agent spawn prompt.

### Per-agent spawn

Before spawning each agent, mark its status in-flight:

```bash
printf '{"agents":{"%s":{"status":"in-flight"}}}\n' "$AGENT_SLUG" \
  | "${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" patch "$MANIFEST"
```

Helper auto-stamps `updated_at`.

### Post-recovery

After Artifact Recovery decides each agent's outcome, patch its
`status` to one of `complete`, `stub-replaced`, `recovered-from-return`,
or `stub-no-output`:

```bash
printf '{"agents":{"%s":{"status":"%s"}}}\n' "$AGENT_SLUG" "$STATE" \
  | "${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" patch "$MANIFEST"
```

### Run complete

After consolidated artifact is written:

```bash
echo '{"status":"complete"}' \
  | "${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" patch "$MANIFEST"
```

The completed manifest stays at `RUN-CURRENT.json` until the next run
starts. Next-run `prepare-run` archives it automatically.

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
# Archive any existing manifest + init fresh. Helper computes path,
# datesuffix, agent paths, consolidated path, and (for review) git
# pins. Outputs absolute manifest path on stdout.
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" prepare-run \
  --skill=rb:review --slug=SLUG --agents=A,B,C [--base-ref=REF]

# Read field (dotted path supported, e.g. agents.ruby-reviewer.path).
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" field <manifest> <key>

# Tab-separated agent_slug<TAB>absolute_path per line.
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" spawn-paths <manifest>

# Deep-merge JSON from stdin. Auto-stamps updated_at.
printf '<patch-json>\n' | "${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" patch <manifest>

# Unlink stale stubs at manifest-tracked agent paths before re-spawn.
# Only unlinks files < 1000 bytes (real artifacts protected with warning).
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" prepare-respawn <manifest>

# Append current state to RUN-HISTORY.jsonl, unlink RUN-CURRENT.json.
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" archive <manifest>

# Read-only verdict (absent | stale | fresh-complete | fresh-in-flight).
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" resume-check <manifest>

# One-line summary (read-only).
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" status <manifest>

# Init manifest from raw JSON literal (low-level; fails if exists).
"${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" init <manifest> '<json>'
```

Helper enforces:

- Path allowlist: helper accepts only paths matching
  `<repo>/.claude/<namespace-fragment>/RUN-CURRENT.json` where
  `<namespace-fragment>` matches one of the per-skill namespace
  templates above. Any other path → exit 1 before touching disk.
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

Single `prepare-run` call. Helper computes manifest path, archives
any prior manifest, inits fresh, outputs the path on stdout. Skill
body uses output for subsequent `field` / `spawn-paths` / `patch` /
`prepare-respawn` calls.

```bash
MANIFEST=$("${CLAUDE_PLUGIN_ROOT}/bin/manifest-update" prepare-run \
  --skill=<rb:review|rb:plan|rb:brainstorm> --slug="$SLUG" \
  [--base-ref="$BASE_REF"] \
  --agents="$AGENTS_CSV")
```

The skill that invokes `prepare-run` selects its own agent slugs and
constructs `$AGENTS_CSV` at runtime. Helper does not know or
prescribe which agents to spawn.

`resume-check` (read-only inspector) is available for callers that
want to surface in-flight state to the user before invoking
`prepare-run`.

## Implementation Notes

- `RUN-HISTORY.jsonl` git-ignored by default; project may add explicit gitignore exception.
- Concurrent CC sessions on same branch race on `RUN-CURRENT.json`. No cross-process lock. Constraint: one workflow per branch at a time.
