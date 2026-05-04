---
name: rb:review
description: "Use when you need code review of changed files with parallel specialist agents for correctness, security, testing, Active Record, Grape, and Sidekiq boundaries. Use after implementation before commit or PR."
when_to_use: "Triggers: \"review my changes\", \"code review\", \"review before commit\", \"check this PR\", \"review for security\". Does NOT handle: fixing code, full project audit, planning, verification/test runs."
argument-hint: "[test|security|sidekiq|deploy|iron-laws|all]"
effort: xhigh
---
# Review Ruby/Rails/Grape Code

Review changed code by spawning specialist agents. Review is **read-only** - never fix during review.

## Review Philosophy

Reviews catch issues before they reach production. Each specialist focuses on their domain:

- **Correctness**: Does it work? Handle edge cases?
- **Security**: Are there vulnerabilities? Input validation?
- **Maintainability**: Can others understand and modify this?
- **Performance**: Will it scale? Any N+1s?
- **Style**: Does it follow conventions?

## Collecting Changed Files

Resolve the base ref via `${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref`,
compute `$MERGE_BASE`, then capture in ONE shell session:

- `$CHANGED_FILES` (file list, `--name-only --diff-filter=ACMR`)
- `$DIFF_STAT` (`git diff --stat`)

Pass `$CHANGED_FILES`, `$BASE_REF`, `$MERGE_BASE`, and `$DIFF_STAT` to
every spawned reviewer. Reviewers scope analysis to `$CHANGED_FILES`
and NEVER scan unchanged files.

Reviewers own diff strategy.

For exact shell commands + reviewer diff discipline, see
`${CLAUDE_SKILL_DIR}/references/review-playbook.md` § "Diff Collection".

## Main-Session Fanout

`/rb:review` spawns specialist agents directly from the main session in
parallel. Subagents are leaf workers — they return findings; they do not
spawn further agents.

**MUST spawn in foreground.** Never pass `run_in_background: true` on
any Agent call. Use parallel via multiple Agent tool calls in a single
message.

### Fanout Pattern

1. Classify complexity (tier + critical-path escalation).
2. Select core + conditional reviewers per matrix below. Derive
   `review-slug`. Resolve `BASE_REF` via
   `${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref`.
3. Run
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run --skill=rb:review
   --slug="$REVIEW_SLUG" --base-ref="$BASE_REF" --agents=<csv-of-reviewer-slugs>`.
   Captures stdout as `$MANIFEST` (absolute manifest path). Helper
   archives any prior manifest, computes datesuffix, agent paths,
   consolidated path, git pins; writes fresh manifest atomically.
4. Run
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-respawn "$MANIFEST"`.
   Rotates existing files at manifest-tracked agent paths to
   `<agent-slug>.stale-<rename-ts>.md`.
5. For each agent, patch `status: in-flight` via
   `printf '{"agents":{"%s":{"status":"in-flight"}}}\n' "$AGENT_SLUG" |
   ${CLAUDE_PLUGIN_ROOT}/bin/manifest-update patch "$MANIFEST"`.
6. Spawn all reviewers in ONE parallel block. Read agent paths via
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update spawn-paths "$MANIFEST"`
   (tab-separated `agent_slug<TAB>absolute_path`). Pass each absolute
   path verbatim in the spawn prompt.
7. Wait for all reviewers to complete.
8. Apply Artifact Recovery (see below). Patch each agent's `status`
   field with its recovery-state value (`artifact` |
   `stub-replaced` | `recovered-from-return` | `stub-no-output`).
9. Read each verified artifact. Read consolidated path via
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update field "$MANIFEST" consolidated_path`.
   Write the consolidated review to that path.
10. Patch manifest `status: complete`.
11. Present verdict to the user.

### Artifact path rules

- Helper computes absolute paths from `--skill` + `--slug` +
  `--agents` + datesuffix.
- Skill body reads paths via `manifest-update spawn-paths "$MANIFEST"`.
- Pass each path verbatim in the spawn prompt.
- Agents use the exact path received. No filename invention,
  truncation, or extension change.
- Path is per-second-unique (datesuffix). Always points at a
  non-existing target after `prepare-respawn`.
- Verify artifacts via the manifest. Never glob.

## Run Manifest

- Path: `.claude/reviews/{review-slug}/RUN-CURRENT.json`.
- Schema + write protocol: `${CLAUDE_PLUGIN_ROOT}/references/run-manifest.md`.
- All mutations go through `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update`
  (`prepare-run`, `field`, `spawn-paths`, `patch`, `prepare-respawn`,
  `archive`, `resume-check`, `status`, `init`). NEVER call raw `mv`,
  `cp`, `rm`, or `jq -i` against manifest or per-agent artifact paths.
- Main session owns reads + writes. Agents NEVER touch the manifest.
- `prepare-run` computes manifest path, datesuffix, agent paths,
  consolidated path, and (for review) git pins; archives any prior
  manifest; inits fresh in a single call.

## Complexity Classification

Classify the review before spawning agents. File count determines base tier;
critical-path files force escalation regardless of count.

| Tier | Files Changed | Depth | Agents |
|------|--------------|-------|--------|
| **Simple** | 1-3 | Core reviewers only, concise output | 4 |
| **Medium** | 4-10 | Core + conditional by file type | 4-8 |
| **Complex** | 11+ | All relevant reviewers, detailed output | 8-11 |

Log the classification in the consolidated review header:
`**Complexity**: Simple (2 files) | Medium (7 files) | Complex (15 files, escalated: db/migrate)`

## Reviewer Selection Matrix

Spawn from main session in single parallel block based on tier + file patterns:

### Core Reviewers (Always — all tiers)

- `ruby-reviewer` - Ruby idioms, syntax, correctness
- `security-analyzer` - Security vulnerabilities
- `testing-reviewer` - Test coverage and quality
- `verification-runner` - Automated checks pass

### Conditional Reviewers (Medium + Complex tiers)

- `iron-law-judge` - When diff is risky or touches critical paths
- `sidekiq-specialist` - When workers or jobs changed
- `deployment-validator` - When container or deploy config changed
- `rails-architect` - When service layer, Grape APIs, or architecture changed
- `ruby-runtime-advisor` - When performance, memory, or hot paths changed
- `data-integrity-reviewer` - When models, constraints, or transactions changed
- `migration-safety-reviewer` - When migrations add columns or modify tables

### Auto-escalation Triggers

When ANY changed file matches a pattern below, force Complex tier and add
the matching specialist to the spawn list (in addition to base tier):

| File pattern matched | Add specialist |
|---|---|
| `**/auth/**`, `**/authentication/**`, `**/authorization/**` | `iron-law-judge` (security-analyzer always already core) |
| `**/payment/**`, `**/billing/**`, `**/checkout/**` | `iron-law-judge` + `data-integrity-reviewer` |
| `db/migrate/**` | `migration-safety-reviewer` + `data-integrity-reviewer` |
| `config/routes*` | `rails-architect` |
| `config/initializers/devise*` | `iron-law-judge` (security-analyzer already core) |
| `**/middleware/**` | `rails-architect` (security-analyzer already core) |

### Worker Briefing Requirements

Every Agent() call must include in its prompt:

- Task: review the file list for the requested scope
- `$CHANGED_FILES` (the diff manifest from main session)
- `$BASE_REF` (from resolve-base-ref output)
- `$MERGE_BASE` (from `git merge-base HEAD "$BASE_REF"`)
- `$DIFF_STAT` (from `git diff --stat`)
- **Absolute artifact path** read from
  `manifest-update spawn-paths "$MANIFEST"` (one row per agent slug).
  Worker MUST use the exact path passed to it — do NOT invent,
  modify, shorten, or extension-change the filename.
- Required output: write artifact (always — even on PASS) and return summary
- Findings format: `file:line`, `Severity (Critical|Warning|Info)`,
  `Confidence (HIGH|MEDIUM|LOW)`, description, current code, suggested
  code. Synthesis maps Critical/Warning/Info into consolidated
  BLOCKER/WARNING/SUGGESTION per playbook § "Worker Severity Mapping".
- Constraint: stop after returning; do NOT call Agent() — leaf review

For full briefing template (verbatim text to use in prompts), see
`${CLAUDE_SKILL_DIR}/references/review-playbook.md` § "Worker Briefing Template".

## Iron Laws

1. **Never fix code inside `/rb:review`** - findings only, fixes later
2. **Focus on changed lines first** - label unchanged issues as pre-existing
3. **Deduplicate overlapping findings** - merge similar issues from different agents
4. **Keep noise low** - prefer findings a senior Ruby reviewer would care about
5. **Be specific** - cite line numbers, provide examples
6. **Prioritize** — workers emit `Critical | Warning | Info`; synthesis maps to `BLOCKER | WARNING | SUGGESTION` per playbook § "Worker Severity Mapping"
7. **Contextualize** - explain why it matters, not just what's wrong
8. **Identify package + ORM first** - do not apply flat Rails / Active Record advice to Sequel or modular packages

## Provenance Guard

Most review findings are code-local and can be justified directly from the diff.
Use `output-verifier` only when the review depends on external evidence,
versioned sources, or claims that need explicit verification, for example:

- "Rails 8.1 behavior changed here"
- "Sidekiq best practices require this pattern"
- "This gem feature is unsupported in the current version"

If the finding is already proven directly by changed code, line references in the
review itself are enough and no provenance sidecar is needed.

When used:

1. write the draft consolidated review
2. run `output-verifier` against the draft
3. save the result to `.claude/reviews/{review-slug}-{datesuffix}.provenance.md`
4. remove or soften unsupported external claims before presenting the final review

Use the shared provenance contract:

- `${CLAUDE_PLUGIN_ROOT}/references/output-verification/provenance-template.md`

Detailed reviewer focus areas, file-type checklists, and common Ruby
anti-patterns live in
`${CLAUDE_SKILL_DIR}/references/review-playbook.md`.

## Review Artifact Contract

Every `/rb:review` run produces two artifact layers:

- Per-reviewer artifacts: `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md`
- Consolidated review: `.claude/reviews/{review-slug}-{datesuffix}.md`
- Optional provenance sidecar when `output-verifier` is used:
  `.claude/reviews/{review-slug}-{datesuffix}.provenance.md`
- Run manifest (resume pointer): `.claude/reviews/{review-slug}/RUN-CURRENT.json`
- Manifest archive: `.claude/reviews/{review-slug}/RUN-HISTORY.jsonl`

Rules:

- Every spawned reviewer MUST leave an artifact, even on a clean pass
- Clean passes still write `PASS`, files reviewed, and why no findings were raised
- Review artifacts never live under `.claude/plans/...`
- If review is part of a plan, reference the consolidated review from the plan or progress log instead of nesting the report inside the plan namespace

## Synthesis

Read `${CLAUDE_SKILL_DIR}/references/review-playbook.md` § "Synthesis
Procedure" before writing the consolidated artifact. That section is
the canonical 5-step procedure: read playbook → read agent artifacts
→ normalize verdict text → map worker severity → compute verdict
deterministically → write. Skipping the read causes recurring drift
(non-canonical verdict pass-through, worker-form severity leak,
soft verdict despite present blockers).

Output path:
`${CLAUDE_PLUGIN_ROOT}/bin/manifest-update field "$MANIFEST" consolidated_path`.

## Artifact Recovery

For each manifest entry:

1. **CHECK pause signature first** per
   `${CLAUDE_PLUGIN_ROOT}/references/agent-resume.md`. If matched,
   apply that protocol (resume via `SendMessage` if available, else
   mark `stub-no-output`). The state machine below applies ONLY after
   the resume attempt resolves or is skipped.

2. **STAT the expected path.** Apply the state machine:

- Exists, `size_bytes >= 1000` → trust. Do NOT overwrite.
- Exists, `size_bytes < 1000`, return text substantially larger AND
  parses as findings → replace stub with extracted findings.
- Exists, `size_bytes < 1000`, return text empty/unusable → keep
  stub, treat as coverage gap (`stub-no-output`).
- Missing, return text usable → extract findings from return text and write.
- Missing, return text empty/unusable → write a stub with heading
  `# {agent-slug} — recovery stub` and body `Run produced no
  artifact and no usable return text. Reviewer coverage gap.`

NEVER copy or symlink prior-run artifacts to the current-run path.
Each run owns a per-second-unique path. Decide from the filesystem;
ignore Agent return text denial claims. Never re-spawn.

Full table + manifest status mapping:
`${CLAUDE_SKILL_DIR}/references/review-playbook.md` § "Artifact Recovery".

## Confidence Levels

Every finding MUST include a confidence label
(`HIGH | MEDIUM | LOW`). Level definitions, examples, and
deduplication strategy live in
`${CLAUDE_SKILL_DIR}/references/review-playbook.md`
§ "Confidence Levels".

## Review Output Location

Write artifacts to:

- `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md` for each reviewer
- `.claude/reviews/{review-slug}-{datesuffix}.md` for the synthesized output

`review-slug` must be filesystem-safe:

- lowercase
- replace `/` and whitespace with `-`
- strip characters outside `[a-z0-9._-]`
- collapse repeated `-`

Use the current branch name only after slugifying it. If the branch name is not meaningful, derive the slug from the reviewed diff or user-supplied target.

## After Review

Emit exactly one verdict from the canonical 4-set:

- `PASS`
- `PASS WITH WARNINGS`
- `REQUIRES CHANGES`
- `BLOCKED`

Verdict text is load-bearing — manifest writers, eval gates, intro
tutorial citations, and downstream tooling parse the literal string.
Emit each verdict VERBATIM. Do NOT abbreviate, hyphenate, paraphrase,
or compress for terseness:

| Reject | Use |
|---|---|
| `PASS WARN`, `PASS-WITH-WARNS`, `PWW` | `PASS WITH WARNINGS` |
| `BLOCK`, `BLK`, `BLOCKER` (verdict, not severity tag) | `BLOCKED` |
| `REQ-CHANGES`, `RC`, `Needs fixes` | `REQUIRES CHANGES` |
| `OK`, `LGTM`, `Approved` | `PASS` |

Same rule for manifest status enum (`pending`, `in-flight`,
`artifact`, `stub-replaced`, `recovered-from-return`, `stub-no-output`,
`complete`) and severity buckets (`BLOCKER`, `WARNING`, `SUGGESTION`)
— canonical strings only. `bin/manifest-update` validates `status`
against the enum and rejects compressed forms.

Decision rules + chat scripts:
`${CLAUDE_SKILL_DIR}/references/review-playbook.md`
§ "Verdict Decision Rules" + § "Review Outcomes (chat scripts)".

## Integration with Workflow

Review happens after `/rb:work` and before commit. Standard order:
`/rb:plan → /rb:work → /rb:review → /rb:triage` (if issues) → commit/PR.
Reviews can also be triggered standalone for existing code audits.

## Trust States

When a finding cites a sidecar, read the sidecar's `trust_state` (see
`${CLAUDE_PLUGIN_ROOT}/references/output-verification/trust-states.md`):

- `conflicted`: escalate severity by one level.
- `missing`: tag the finding `[unverified]`; do not gate merge.
- `weak`: keep severity; add a provenance note.
- `clean`: proceed silently.

## References

| Need | Reference |
|---|---|
| reviewer focus areas, file-type checklists, anti-patterns, severity, verdict, mandatory finding table, chat scripts, deduplication | `${CLAUDE_SKILL_DIR}/references/review-playbook.md` |
| review-slug derivation + filesystem-safe slug rules | `${CLAUDE_SKILL_DIR}/references/conventions.md` |
| worked example of consolidated review output | `${CLAUDE_SKILL_DIR}/references/example-review.md` |
