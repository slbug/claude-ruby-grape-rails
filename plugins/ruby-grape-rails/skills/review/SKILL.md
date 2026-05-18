---
name: rb:review
description: "Reviewing Ruby/Rails/Grape changes via parallel specialists: correctness, security, tests, AR, Grape, Sidekiq. Triggers: \"review my changes\", \"code review\", \"check this PR\"."
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

Run `${CLAUDE_PLUGIN_ROOT}/bin/resolve-base-ref` → 3 `KEY=value` lines
on stdout (`BASE_REF`, `REMOTE`, `DEFAULT_BRANCH`). Use emitted values
as substitutions in subsequent commands. Then capture:

- `MERGE_BASE` via `git merge-base HEAD <BASE_REF>`
- `CHANGED_FILES` via `git diff --name-only --diff-filter=ACMR <MERGE_BASE>...HEAD`
- `DIFF_STAT` via `git diff --stat <MERGE_BASE>...HEAD`

Pass the captured `CHANGED_FILES`, `BASE_REF`, `MERGE_BASE`, and
`DIFF_STAT` values to every spawned reviewer. Reviewers scope
analysis to the file list and NEVER scan unchanged files.

Reviewers own diff strategy. For reviewer diff discipline, see
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
   `review-slug`. Use the `BASE_REF` value captured in §
   "Collecting Changed Files" — substitute literally into shell
   commands below (e.g. `--base-ref=<BASE_REF>`).
3. Run
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update prepare-run --skill=rb:review
   --slug=<REVIEW_SLUG> --base-ref=<BASE_REF> --agents=<csv-of-reviewer-slugs>`.
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
8. Apply Artifact Recovery per
   `${CLAUDE_PLUGIN_ROOT}/references/artifact-recovery.md` (coverage-noun
   `Reviewer`). Patch each agent's `status`
   field with its recovery-state value (`artifact` |
   `stub-replaced` | `recovered-from-return` | `stub-no-output`).
9. Read each verified artifact directly via the absolute path from
   `manifest-update spawn-paths "$MANIFEST"`. Issue one `Read` per
   path. Do NOT `cat` artifacts into a combined stream — bulk-cat
   overflows the Read token cap on > 5 reviewers and forces
   offset/limit pagination. Read consolidated path via
   `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update field "$MANIFEST" consolidated_path`.
   Write the consolidated review to that path.
10. Patch manifest `status: complete`.
11. Present verdict to the user.

### Artifact path rules

- Helper computes absolute paths from `--skill` + `--slug` +
  `--agents` + datesuffix.
- Skill body reads paths via `manifest-update spawn-paths "$MANIFEST"`.
- Pass each absolute path verbatim in the spawn prompt.
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

Classify the review before spawning agents. Tier = `max(file_tier, loc_tier)`.
Critical-path files force escalation regardless of count or LOC.

| Tier | Files Changed | Diff LOC | Depth | Agents |
|------|--------------|----------|-------|--------|
| **Simple** | 1-3 | ≤ 200 | Lean: correctness + security only | 2 |
| **Medium** | 4-10 | 201-1000 | Core + conditional by file type | 4-8 |
| **Complex** | 11+ | > 1000 | All relevant reviewers, detailed output | 8-11 |

Compute `DIFF_LOC = git diff --shortstat <MERGE_BASE>...HEAD | awk '{n=$4+$6} END{print n+0}'`.
Columns 4 + 6 are insertions + deletions. `END{print n+0}` emits `0`
on empty diff. Range matches `$DIFF_STAT` and `$CHANGED_FILES`.

Log the classification in the consolidated review header:
`**Complexity**: Simple (2 files, 87 LOC) | Medium (7 files, 412 LOC) | Complex (15 files, 1834 LOC, escalated: db/migrate)`

## Reviewer Selection Matrix

Spawn from main session in single parallel block based on tier + file patterns:

### Lean Reviewers (Simple tier minimum)

- `ruby-reviewer` - Ruby idioms, syntax, correctness
- `security-analyzer` - Security vulnerabilities

### Core Reviewers (added at Medium + Complex tiers)

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
- `BASE_REF` value (from resolve-base-ref stdout)
- `MERGE_BASE` value (from `git merge-base HEAD <BASE_REF>`)
- `$DIFF_STAT` (from `git diff --stat`)
- **Absolute artifact path** read from
  `manifest-update spawn-paths "$MANIFEST"` (one row per agent slug).
  Worker MUST use the exact path passed to it — do NOT invent,
  modify, shorten, or extension-change the filename.
- Required output: write artifact (always — even on PASS) and return summary
- Findings format: `file:line`, `Severity (blocker|warning|suggestion)`,
  `Confidence (HIGH|MEDIUM|LOW)`, description, current code, suggested
  code. Synthesis applies diff-status filter only (new vs pre-existing)
  per playbook § "Worker Severity Mapping".
- Constraint: stop after returning; do NOT call Agent() — leaf review

For full briefing template (verbatim text to use in prompts), see
`${CLAUDE_SKILL_DIR}/references/review-playbook.md` § "Worker Briefing Template".

## Iron Laws

1. **Never fix code inside `/rb:review`** - findings only, fixes later
2. **Focus on changed lines first** - label unchanged issues as pre-existing
3. **Deduplicate overlapping findings** - merge similar issues from different agents
4. **Keep noise low** - prefer findings a senior Ruby reviewer would care about
5. **Be specific** - cite line numbers, provide examples
6. **Prioritize** — title case singular `Blocker | Warning |
   Suggestion` in per-finding `Severity:` tags + Counts prefix +
   Reviewer Coverage row count + At-a-Glance Severity column; title
   case plural `Blockers | Warnings | Suggestions` in consolidated
   section headers + Summary table category column; verdict 4-set
   (`PASS | PASS WITH WARNINGS | REQUIRES CHANGES | BLOCKED`) stays
   UPPERCASE
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
Procedure" before writing the consolidated artifact. Apply the 5-step
procedure verbatim.

Output path:
`${CLAUDE_PLUGIN_ROOT}/bin/manifest-update field "$MANIFEST" consolidated_path`.

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
- ensure leading char is `[a-z0-9]` (helper rejects leading `.`, `-`, `_`)

Use the current branch name only after slugifying it. If the branch name is not meaningful, derive the slug from the reviewed diff or user-supplied target.

## After Review

Emit exactly one verdict from the canonical 4-set:

- `PASS`
- `PASS WITH WARNINGS`
- `REQUIRES CHANGES`
- `BLOCKED`

Emit each verdict VERBATIM. Do NOT abbreviate, hyphenate, paraphrase,
or compress:

| Reject | Use |
|---|---|
| `PASS WARN`, `PASS-WITH-WARNS`, `PWW` | `PASS WITH WARNINGS` |
| `BLOCK`, `BLK`, `BLOCKER` (verdict, not severity tag) | `BLOCKED` |
| `REQ-CHANGES`, `RC` | `REQUIRES CHANGES` (only when actual test-coverage gap on NEW public behavior; see playbook § "Verdict Decision Rules") |
| `OK`, `LGTM`, `Approved` | `PASS` |

`Needs fixes` does NOT auto-route to `REQUIRES CHANGES` — infer per
worker counts (any `Blocker` → `BLOCKED`; else any `Warning` →
`PASS WITH WARNINGS`; else `PASS`).

Use canonical strings only for manifest status enum (`pending`,
`in-flight`, `artifact`, `stub-replaced`, `recovered-from-return`,
`stub-no-output`, `complete`) and severity tags (`Blocker`,
`Warning`, `Suggestion`). The synthesizing skill body owns this
discipline; `bin/manifest-update` does not validate enums on patch.

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

## Gotchas

- Per-reviewer manifest path confusion. Per-agent artifact at
  `.claude/reviews/<agent-slug>/<review-slug>-<datesuffix>.md`.
  Consolidated at `.claude/reviews/<review-slug>-<datesuffix>.md`.
  Consolidation reads per-agent. Downstream (compound, triage,
  follow-up) reads consolidated only.
- Stale base-ref. Run-manifest pins `base_ref` at fanout start. User
  rebase mid-review → recovery state mismatch. Re-fanout if base shifts.
- Recovery-state misclassification. `stub-no-output` (agent ran but
  produced empty file) is NOT `pending` (agent never ran). Distinguish
  before retry vs respawn.
- Missing `**Counts:**` line. Reviewers MUST emit Counts: first.
  Missing line breaks consolidator severity-bucket counts.
- Bulk-cat of artifacts. Reviewer artifacts run ~6-8KB each;
  up to 11 reviewers ≈ 65-90KB combined. Combined stream overflows
  Read token cap. Use one Read per artifact path from `spawn-paths`.

## References

| Need | Reference |
|---|---|
| reviewer focus areas, file-type checklists, anti-patterns, severity, verdict, mandatory finding table, chat scripts, deduplication | `${CLAUDE_SKILL_DIR}/references/review-playbook.md` |
| review-slug derivation + filesystem-safe slug rules | `${CLAUDE_SKILL_DIR}/references/conventions.md` |
| worked example of consolidated review output | `${CLAUDE_SKILL_DIR}/references/example-review.md` |
| production-incident review context (when review covers a live failure) | `${CLAUDE_PLUGIN_ROOT}/skills/investigate/references/incident-playbook.md` |

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Adversarial review needed → `/rb:challenge` (adversarial-mode review)
- API or internal docs needed → `/rb:document` (post-implementation docs)
- Mistake worth capturing as a rule → `/rb:learn` (in-flight lesson capture)
- Slow / latency / memory regression → `/rb:perf` (performance analysis)
- PR review comments to address → `/rb:pr-review` (PR review-comment handling)
- Pre-push secret check → `/rb:secrets` (pre-push secret scan)
- Codebase health snapshot → `/rb:audit` (project-wide audit)
- Research trust / source-quality audit → `/rb:provenance-scan` (research-trust audit)
- Adjacent debt noticed but out of scope → `/rb:techdebt` (tech-debt logging)
<!-- END-GENERATED related-footer -->
