# Changelog

All notable changes to the Ruby/Rails/Grape Claude Code plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.16.6] - 2026-05-03

### Added

- `inject-rules.sh` payload now emits a `See:` line per preference
  and per Iron Law that has `reference_files` set. 15 paths total
  injected into `SessionStart` (main) + `SubagentStart` (subagent)
  contexts (9 Iron Laws + 6 preferences) so agents can open the
  companion docs via `${CLAUDE_PLUGIN_ROOT}/<path>` without
  guessing the root.
- Turn-budget rule on `rails-architect.md` (deadline 30) and
  `ruby-runtime-advisor.md` (deadline 26) for parity with the 10
  reviewer agents already covered.
- "Turn Budget Semantics" section in
  `.claude/rules/agent-development.md` clarifying that "turn" =
  model invocation (`stop_reason` set), NOT raw assistant-message
  jsonl line.
- `lab/eval/tests/test_runtime_scripts.py` `InjectRulesTests`:
  pinned 3 preferences `See:` line assertions (`context7-usage.md`,
  `epistemic-posture.md`, `tool-batching.md`) with
  `${CLAUDE_PLUGIN_ROOT}` prefix.

### Changed

- `plugins/ruby-grape-rails/references/research/` renamed to
  `references/preferences/` — contents (`context7-usage.md`,
  `epistemic-posture.md`, `tool-batching.md`) are 1:1 preference
  companion docs, never research output. `preferences.yml`
  `reference_files` paths + cross-references in CLAUDE.md,
  `.claude/rules/agent-development.md`,
  `.github/copilot-instructions.md`,
  `.github/instructions/plugin-review.instructions.md` updated.
- Reviewer-agent header `## CRITICAL: Save Findings File First`
  renamed to `## Findings File Is Primary Output` across all 12
  agents (10 reviewers + `rails-architect` +
  `ruby-runtime-advisor`). Old header implied "first action"; body
  says "complete analysis BY turn ~M, then Write" — mismatch
  resolved.
- `iron-laws.yml` `version` 1.1.0 → 1.2.0. Per-law
  `reference_files` entries audited per existence on disk; 9 paths
  corrected to point at real `skills/<name>/references/<doc>.md`
  files (Laws 3, 4, 5, 8, 9, 10, 13, 18, 21); 13 entries pointing
  at non-existent files removed (Laws 1, 2, 6, 7, 11, 12, 14, 15,
  16, 17, 19, 20, 22). Schema field remains optional for future
  expansion.
- `preferences.yml` `version` 1.2.0 → 1.3.0; `reference_files`
  paths now plugin-root-relative (`references/preferences/...`).
- Generator (`scripts/generate-iron-law-content.rb`) emits
  `${CLAUDE_PLUGIN_ROOT}/<r>` for each `reference_files` entry
  (paths in YAML are plugin-root-relative).

### Fixed

- Direct `references/research/tool-batching.md` references in
  `agents/call-tracer.md` + `skills/review/references/review-playbook.md`
  removed — injection delivers the path via the `See:` line;
  restating it in agent / skill bodies is duplication.

## [1.16.5] - 2026-05-03

### Added

- Preference #6 (`tooling`, "Bash Bodies Execute, Not Narrate"):
  forbids `#` thinking/checklist lines inside Bash command bodies.
  Wired into `inject-rules.sh` for both `SessionStart` and
  `SubagentStart`.
- `references/research/tool-batching.md`: new "Bash bodies execute,
  not narrate" section (BAD/GOOD pair).
- `lab/eval/tests/test_runtime_scripts.py` `InjectRulesTests`:
  pinned assertions for all 6 preferences + Iron Law 12 +
  Ruby-eval scope phrase. Catches generation drift.

### Changed

- Agent turn-budget rules rewritten as imperatives — complete
  analysis by ~75% of `maxTurns`, single `Write`, then summary
  (subagents cannot overwrite). Per-agent analysis deadlines:
  `data-integrity-reviewer` 45, `testing-reviewer` 45,
  `ruby-reviewer` 30, `iron-law-judge` 30,
  `deep-bug-investigator` 30, `security-analyzer` 26,
  `verification-runner` 26, `deployment-validator` 18,
  `migration-safety-reviewer` 18, `sidekiq-specialist` 18.
- Tool-name prose ("Read/Grep analysis") removed from agent bodies
  per `agent-development.md` "Bash Discipline" rule.
- `review/SKILL.md`, `plan/SKILL.md`, `brainstorm/SKILL.md`: replaced
  ambiguous "Patch each agent's recovery `status`" with explicit
  "Patch each agent's `status` field with its recovery-state value
  (`artifact` | `stub-replaced` | `recovered-from-return` |
  `stub-no-output`)".
- `preferences.yml` metadata: `version` 1.1.0 → 1.2.0,
  `last_updated` 2026-05-02 → 2026-05-03, `total_preferences`
  5 → 6, `tooling` category `preference_count` 1 → 2.

### Fixed

- Schema drift in `/rb:review` + `/rb:plan` + `/rb:brainstorm` skill
  bodies: ambiguous "recovery `status`" phrasing caused main-session
  manifest patches to emit an undocumented `recovery` field
  alongside `status`. Verified in ludwig session
  `040c3082-ad98-4ed6-aa38-218e93acfbc4` —
  `printf '{"agents":{"%s":{"status":"artifact","recovery":"artifact"}}}'`.
  Wording fix removes the parse path that produces the extra field.

## [1.16.4] - 2026-05-03

### Added

- `bin/manifest-update` (Ruby) — atomic manifest writer with
  path-allowlist gate, symlink-ancestor refusal, atomic temp file
  (`O_EXCL`) + fsync + POSIX rename + dir fsync. Subcommands:
  `prepare-run` (structured
  args: `--skill --slug --agents [--base-ref]`; helper computes
  manifest path, datesuffix, agent paths, consolidated path, git
  pins; archives any prior; outputs absolute manifest path),
  `field` (dotted-key extraction), `spawn-paths` (tab-separated
  agent slug + absolute path per line), `patch` (deep-merge from
  stdin), `prepare-respawn` (rotate manifest-tracked agent files to
  `<agent-slug>.stale-<rename-ts>.md`; refuses unless canonical-path
  match + containment + no symlinked ancestor + agent status
  `pending`/`in-flight`/`stub-no-output`), `resume-check` (read-only
  verdict), `archive`, `status`, `init` (low-level). All manifest
  mutations and stale-stub rotations go through this binary; raw
  `mv` / `cp` / `jq -i` / `rm` against manifest or per-agent artifact
  paths is forbidden.
- `lib/repo_root.rb` — shared `RubyGrapeRails::RepoRoot` module
  (find / canonical / git_toplevel) extracted from
  `bin/extract-permissions` and `bin/detect-stack`. Stdlib only.
- `lib/path_safety.rb` — shared `RubyGrapeRails::PathSafety` module
  (`reject_symlink_ancestors!`, `canonical_existing_or_deepest`,
  `path_within_root?`). Used by `bin/manifest-update` to refuse
  paths that traverse a symlinked ancestor. Stdlib only.
- `references/run-manifest.md` — cross-session resume schema for
  spawn-fanout workflows; JSON manifest at
  `.claude/{namespace}/RUN-CURRENT.json` (namespace per-skill);
  per-skill staleness rules (review: TTL + HEAD + base + branch;
  plan + brainstorm: TTL only, 168h default).
- `references/agent-resume.md` — protocol for resuming agents that
  paused at their `maxTurns` cap via `SendMessage`. Linked from
  `/rb:review`, `/rb:plan`, `/rb:brainstorm`, `/rb:investigate`
  recovery sections.
- `references/research/tool-batching.md` — BAD/GOOD examples for
  batched git/gem/find usage.
- Tool-batching preference in `preferences.yml` (new `tooling`
  category): prefer `Grep`/`Glob` tools when available; otherwise
  use `ugrep`/`bfs` (CC-embedded on native macOS/Linux 2.1.117+) over
  shell `grep -rn`/`find`. Use `Read` over `cat`/`head`/`tail`. Batch
  `git diff`/`git log` by path group. Injected via `inject-rules.sh`.
- Foreground-only dispatch rule for plugin agents in
  `agent-development.md` + `skill-development.md`.
- Recommended permission allowlist in `init/SKILL.md` + `README.md`:
  recursive `Write(**/.claude/<ns>/**)` rules + `Bash(*/bin/manifest-update *)`.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env-var recommendation in
  `README.md`, `init/SKILL.md`, `intro/SKILL.md`. Required for
  `SendMessage` availability in spawn-fanout recovery.
- Reviewer Coverage section in consolidated review template.

### Changed

- Review consolidated path: `{review-slug}-{datesuffix}.md` (was
  `{review-slug}.md`). Provenance sidecar matches.
- Artifact recovery: trust on-disk ≥ 1000 bytes; never copy
  prior-run artifacts; new `stub-no-output` state.
- `/rb:review` skill body: resume check + manifest writes through
  fanout/recovery/synthesis; passes `$DIFF_STAT` to each reviewer.
- Agent `maxTurns`: `ruby-reviewer` 40, `rails-architect` 40,
  `testing-reviewer` 60, `iron-law-judge` 40,
  `data-integrity-reviewer` 60, `verification-runner` 35,
  `security-analyzer` 35, `ruby-runtime-advisor` 35.
- `/rb:plan` + `/rb:review`: main session synthesizes directly
  (compression worker dropped).
- `/rb:brainstorm`, `/rb:plan`: dropped `run_in_background: true`.
- `/rb:plan` + `/rb:brainstorm` now wired to run-manifest contract
  (TTL-only freshness, 168h default).
- `/rb:full` `cycle-patterns.md` review path updated to datesuffix form.
- `agents/web-researcher.md`: dropped `background: true` frontmatter
  (conflicts with foreground-only dispatch rule).
- Manifest-update invocations in skill bodies + reference docs
  unquoted (`${CLAUDE_PLUGIN_ROOT}/bin/manifest-update args` instead
  of quoted form) for permission-pattern matchability.
- `/rb:review`, `/rb:plan`, `/rb:brainstorm` recovery sections:
  CHECK pause signature first (per `agent-resume.md`), state machine
  second.

### Fixed

- Symlink-ancestor traversal in `bin/manifest-update`
  (`validate_path`, `prepare-respawn`): caller-controlled
  `.claude/<ns>/...` path could traverse a symlinked ancestor and
  cause writes / unlinks outside the repo containment root. Now
  rejected via lexical ancestor walk.
- Cross-namespace data-loss vector in `prepare-respawn`: tampered
  manifest pointing at unrelated `.md` paths now refused via
  canonical-path equality check (computed from manifest's
  `skill`/`slug`/`datesuffix`/agent-slug per `SKILL_CONVENTIONS`).
- Replaced `Bash(${CLAUDE_PLUGIN_ROOT}/bin/manifest-update *)` with
  `Bash(*/bin/manifest-update *)` in recommended permission
  allowlists. Env-var substitution does not apply to permission
  patterns per CC docs.

### Removed

- `agents/context-supervisor.md` (orchestrator-cleanup follow-up).
- Context Supervisor Pattern sections in `CLAUDE.md` + `README.md`.
- Agent count: 20 → 19. Mechanical/Extraction tier: 3 → 2.

## [1.16.3] - 2026-05-02

### Fixed

- `verification-runner` agent: removed `background: true`. Background-launched
  agents cannot surface interactive Write permission prompts — agent
  silently failed to write its review artifact and returned findings
  inline. Now runs foreground like every other Write-capable reviewer.

### Changed

- `rails-architect`, `rails-patterns-analyst`, `ruby-runtime-advisor`:
  bumped `maxTurns` 15 → 25 for parity with other Write-capable
  reviewers. Multi-file review work was hitting the 15-turn cap mid-Write.

## [1.16.2] - 2026-05-02

### Changed

- `/rb:review` now runs main-session fanout: skill body spawns
  specialist reviewers directly. Reviewers run with fresh context
  (independent / unbiased findings). Compression input narrowed to
  exact current-run artifact paths (no stale cross-contamination).
  Skill body contains NO bash fenced blocks per repo policy; shell
  detail moves to `references/review-playbook.md`.
- `/rb:plan` now runs main-session fanout for research agents.
  `context-supervisor` is invoked as a leaf compression worker after
  fanout returns. New strict slug pre-bind detection: when
  `.claude/ACTIVE_PLAN` exists with explicit guards (file resolves to
  valid namespace, `progress.md` State INITIALIZING|DISCOVERING,
  `plan.md` absent), `/rb:plan` reuses the pre-bound namespace.
  Detection reads the marker file directly, bypassing
  `active-plan-marker.sh get` fallbacks. Bash detail moved to
  `references/planning-workflow.md`.
- `/rb:full` skill body absorbs the workflow state machine
  (INITIALIZING → ... → COMPLETED) and writes `**State**:` to
  `progress.md` at each transition. Skill body tracks `PLAN_DIR`
  locally as INTERNAL state for its own State writes only — NOT passed
  as CLI arg to `/rb:verify` or `/rb:review` (their interfaces don't
  accept it). Adds autonomous-mode skip in `plan-stop-reminder.sh`
  (previously dead — `**State**:` field had no writer).
  `full/SKILL.md` shrinks to ≤100 lines (NO bash fenced blocks); detail
  moves to new `references/state-machine.md`.
- `/docs-check` skill body absorbs `docs-validation-orchestrator`
  Phase 3 worker dispatch (main-session fanout). Workers are named
  contributor leaf agent `docs-surface-validator` (NEW), one parallel
  call per surface in scope. Standard contributor permission scope (NO
  `bypassPermissions`); user grants Write permission via standard CC
  permission flow on first run. Skill body contains NO bash fenced
  blocks per repo policy.
- `.claude/rules/agent-development.md` doctrine update: subagents are
  leaf workers, never declare or invoke `Agent` tool. Dead doctrine
  removed (Why-Orchestrators-Exceed section, 535 hard-limit, opus
  primary-orchestrator tier, parallel-reviewer Agent exemption).
  `context-supervisor` added to narrow-allowlist exception list.
- `CLAUDE.md` Context Supervisor Pattern section corrected (audit
  skill no longer falsely listed; describes skill-body invocation).
  Inline-subagent-prompts checklist item replaced with references-
  preferred guidance.
- `README.md` Agent Hierarchy redrawn (no orchestrator tier; 20
  agents organized by domain; correct model classification — 1 opus,
  16 sonnet, 3 haiku; haiku tier renamed "Mechanical / Extraction"
  to cover compression, verification, and web-research extraction).
  Agent count updated 23 → 20 across intro, dashboard, hierarchy
  diagram, agent table.
- `.github/copilot-instructions.md` cross-file checklist updated to
  reference skill-body fanout owners (including `/docs-check`).
- `.github/instructions/plugin-review.instructions.md` doctrine
  cleanup: no agent declares Agent tool; opus tier scope narrowed to
  security-critical; large-skill acceptability narrowed to
  routing-critical only; orchestrator memory:project guidance dropped.
- `.claude/skills/cc-changelog/references/analysis-rules.md` count
  and orchestrator-agent assumptions updated.
- `agents/context-supervisor.md` description: "for the parent
  orchestrator" → "for the calling skill body post-fanout".
- `references/compression/README.md` lines 66-68: removed
  contributor-doctrine cross-reference ("the repo's own hook-development
  rule"); replaced with inline summary of `PostToolUse` stdout +
  `additionalContext` semantics.
- `hooks/scripts/active-plan-lib.sh` marker-lifecycle comment updated
  to reflect `/rb:full` pre-binding and Option A local PLAN_DIR.
- Plan-task annotation set canonicalized in
  `skills/plan/references/planning-workflow.md`: `[direct]`,
  `[active record]`, `[hotwire]`, `[sidekiq]`, `[concurrency]`,
  `[security]`, `[test]` (Set A). `skills/plan/SKILL.md:15` updated to
  match. `skills/work/SKILL.md` § Routing Hints reframed as prose-only
  Set B labels (NOT plan-task annotations).
  `skills/work/references/execution-guide.md` terminology normalized
  `[agent]` → `[annotation]` in task-format examples.

### Removed

- `parallel-reviewer`, `planning-orchestrator`, `workflow-orchestrator`
  shipped agents (broken wrapper-orchestrator pattern; CC blocks
  subagent → subagent recursion at runtime). `parallel-reviewer` was
  actively invoked by `/rb:review` and silently fell through to single-
  agent review; `planning-orchestrator` and `workflow-orchestrator` were
  dead code (never invoked from shipped skill bodies).
  Internal-mechanism change only — user-facing `/rb:*` commands and
  artifact paths unchanged. Treat as MINOR per repo SemVer policy unless
  external automation references the deleted agent names.
- `references/agent-playbooks/{planning,workflow}-orchestrator-playbook.md`
  (content absorbed into skill references). The
  `agent-playbooks/dependency-analysis-playbook.md` remains, used by
  `dependency-analyzer`.
- `.claude/agents/docs-validation-orchestrator.md` contributor agent
  (same broken pattern; logic absorbed into `/docs-check` skill body
  plus new named leaf agent `.claude/agents/docs-surface-validator.md`).

### Fixed

- `plan-stop-reminder.sh` autonomous-mode skip now functional during
  `/rb:full` runs. Previously dead because no writer of `**State**:`
  field existed; `/rb:full` skill body now writes it during phase
  transitions.

## [1.16.1] - 2026-05-01

### Added

- `duration_ms` field in `compression.jsonl` telemetry entries
  (`compress-verify-output.rb`). Captures the CC 2.1.119+
  PostToolUse wall-clock duration so downstream analysis can
  correlate compression ratio with verify runtime per command class.
- Single-line megastring middle-collapse pass in `VerifyCompression`.
  Lines exceeding `megastring.threshold_bytes` (default 2048) keep
  `keep_head` + `keep_tail` bytes from each end and elide the middle
  via the `collapse.megastring` template. Targets inline rspec
  expectation blobs (`to eq { ... }`, `to match (...)`) that
  line-oriented collapsers cannot reduce.

### Changed

- Compression triggers exclude commands containing `| tail` or
  `| head` (`triggers.yml`). Operator-pre-trimmed verify output is no
  longer recorded as a 0% sample inflating the underpowered-class
  denominator in compression-report.

## [1.16.0] - 2026-04-26

### Added

- Trust-state consumption in `/rb:plan --existing`, `/rb:triage`,
  `/rb:work`, and `/rb:review`. Each reads the `trust_state` of
  referenced sidecars: `clean` proceeds, `weak` warns, `missing` warns
  or tags `[unverified]`, `conflicted` halts.
- `/rb:provenance-scan` skill + `bin/provenance-scan` Ruby CLI. Walks
  `.claude/{research,reviews,audit,plans/*/{research,reviews}}`,
  classifies each `*.provenance.md` via the 4-state algorithm, writes
  a dated Markdown report under `.claude/provenance-scan/`.
- `inject-rules.sh` hook delivers Iron Laws + Advisory Preferences via
  `additionalContext` to both the main session (`SessionStart`) and
  subagents (`SubagentStart`). One generated script reads
  `hook_event_name` and echoes it back in
  `hookSpecificOutput.hookEventName`. End-user opt-out:
  `RUBY_PLUGIN_DISABLE_RULES_INJECTION=1` short-circuits before stdin
  read or helper sourcing.
- `block-dangerous-ops.sh` branches on `hook_event_name`:
  `PermissionRequest` emits `decision.behavior="deny"` with `message`
  and `decision.interrupt=false` (flipping to `true` under
  `RUBY_PLUGIN_STRICT_PERMS=1`), exit 0 in both cases.
  `PermissionDenied` appends `{ts, cmd, pattern, classifier_reason}`
  to `${CLAUDE_PLUGIN_DATA}/denied-commands.jsonl`, capturing the
  plugin pattern and CC's auto-mode classifier reason.
- `hooks.json`: `PermissionRequest` + `PermissionDenied` events
  registered against `block-dangerous-ops.sh`; `SessionStart` and
  `SubagentStart` both wired to `inject-rules.sh`.

### Changed

- Iron Laws + Advisory Preferences delivery moved from inline
  `CLAUDE.md` blocks to runtime hook injection. Existing installs run
  `/rb:init --update` to replace the managed block.
- Iron-laws generator (`scripts/generate-iron-law-content.rb`,
  `scripts/generate-iron-law-outputs.sh`) emits one unified
  `inject-rules.sh`. The `event_kind` parameter is gone; the single
  `injector` target dispatches on runtime `hook_event_name`.
- Several SKILL.md cross-references switched from
  `../../references/...` / `../<sibling>/...` to explicit
  `${CLAUDE_PLUGIN_ROOT}/...`, removing CWD dependence.
- `compression-report` and `provenance-scan` skill frontmatter drop
  `allowed-tools` (permission UX, not a restriction; Iron Laws are
  the behavioral boundary).
- New `collapse_repeated_blocks` compression rule (K=2..5) collapses
  consecutive identical multi-line stanzas (warn + caller frame pairs
  from `Dry::Core::Deprecations.warn`, multi-line gem warnings,
  repeated banners). K=1 excluded to avoid over-collapsing legitimate
  single-line repeats.
- `file_colon_line` preserve regex tightened to reject the
  `<path>:<line>:in '<method>'` warn-caller-frame suffix. Real
  file:line refs (rspec, rubocop) still match.

### Removed

- Legacy `inject-iron-laws.sh` (SubagentStart-only); replaced by
  `inject-rules.sh`.
- Generator dispatcher targets `injectable` + `preferences` and the
  `update_preferences_block` helper — runtime injection makes them
  obsolete.
- Inline `<!-- IRON_LAWS_START -->` / `<!-- PREFERENCES_START -->`
  blocks no longer ship in the init injectable template.

## [1.15.2] - 2026-04-26

### Changed

- Compression rule extension: `STACK_FRAME_RE` now matches the RSpec
  "outside of examples" formatter prefix (`# /path:line:in '...'`)
  in addition to the bare `from`/`at` Ruby backtrace prefixes.
  Boot-failure stacks (Sequel/PG connection errors, autoload
  crashes) now collapse beyond top-5 frames as intended.
- `file_colon_line` preserve regex updated to also reject hash-prefixed
  (`# /path:line`) file:line refs from being preserved when they belong
  to collapsed stack frames.
- New `collapse_bracket_warnings` rule collapses runs of consecutive
  identical gem-prefixed warning lines (e.g. `[dry-types] ...`,
  `[bundler] ...`) the same way `DEPRECATION WARNING` blocks are
  collapsed. New collapse template `repeated_warnings: "  [+{count}
  repeated]"` exposed in `rules.yml`.
- Trigger exclusion list extended to cover both `rake` and `rails`
  uniformly. `rails routes`, `rails db:drop`, `rails db:create`,
  `rails assets:`, `rails stats`, `rails notes` are now excluded
  alongside the equivalent `rake` subcommands.
- Trigger exclusion list now drops `--version` invocations across
  the whole verify-tool family (`rake`, `rails`, `rspec`, `rubocop`,
  `standardrb`, `brakeman`, `reek`). Static banners do not compress
  and skewed the underpowered-class denominator.
- `verify_commands.rake_verify_only` extended to accept `rails`
  alongside `rake` for the `(ci|test|spec|verify|lint|brakeman|...)`
  subcommands. Captures the Rails 5+ canonical form (`rails test`,
  `rails test:system`, `bin/rails test`).

### Removed

- Legacy `SubagentStop` hook + `.agent_metrics.jsonl` writer
  (`hooks/scripts/log-subagent-metrics.sh`). The writer had no
  consumer in the plugin or contributor tooling and the official
  `SubagentStopHookInput` payload does not expose the `duration_ms` /
  `tokenCount` fields the original design relied on. Superseded by
  the ccrider-driven session-scan + skill-monitor pipeline under
  `.claude/skills/session-scan/` and `.claude/skills/skill-monitor/`,
  which derives richer per-skill effectiveness data from session
  transcripts. Existing `${CLAUDE_PLUGIN_DATA}/.agent_metrics.jsonl`
  files left on disk by previous releases are inert; remove with
  plain `rm` when convenient.

## [1.15.1] - 2026-04-26

### Fixed

- Compression hook read `tool_response.output` for Bash; that key
  does not exist. Real shape is `{stdout, stderr, interrupted,
  isImage, noOutputExpected}`. Every Bash telemetry capture in 1.15.0
  silently produced 0 bytes; `compression.jsonl` was never written.
- Hook only registered on `PostToolUse:Bash`. Failed verify commands
  (rspec failures, brakeman exit 3, rubocop exit 1) route to
  `PostToolUseFailure` and were never captured — exactly the
  most-compressable cases. Now registered on both events; reads the
  top-level `error` field on failures.
- Hook opened raw-log file via `O_CREAT|O_EXCL` before checking the
  source had bytes. Empty `tool_response` materialized 0-byte
  orphans that the plugin never deletes by design. Empty-output
  short-circuit now runs before file creation.
- `/rb:compression-report` skill emitted `<owner>/<repo>` placeholder
  in the issue-URL footer. Skill now reads `repository` from
  `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`.
- Skip telemetry on user-interrupt (`tool_response.interrupted=true`
  or top-level `is_interrupt=true`). Partial output is not a
  representative compression sample.

### Changed

- `compress-verify-output.sh` (bash + jq + NUL-delimited shell
  parsing) replaced by `compress-verify-output.rb`. Plugin already
  requires Ruby. Drops jq dependency for this hook entirely.
- Hook calls `Triggers.matches?` and `VerifyCompression.compress` /
  `VerifyCompression.append_jsonl` directly via `require_relative`;
  no longer shells out to `bin/match-trigger` and `bin/compress-verify`.
  Saves two Ruby process spawns per Bash event.
- Successful events capture stdout AND stderr; some verify tools
  (rubocop deprecations, bundler warnings) split findings between the
  two streams.
- `bin/compress-verify` and `bin/match-trigger` moved from
  `plugins/ruby-grape-rails/bin/` to `lab/eval/bin/`. They were only
  consumed by `lab/eval/compression_eval.py` and Python subprocess
  tests; they were never end-user surfaces. End-user `bin/` now
  contains only the operator CLI (`compression-stats`) and the other
  shipped tools.
- `VerifyCompression.append_jsonl(log_path, entry)` extracted as the
  single source of truth for symlink-safe + flock'd jsonl writes.
  Hook and the contributor CLI share it.

## [1.15.0] - 2026-04-26

### Added

- **Verify-output compression telemetry (opt-in via
  `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1`).** Ruby runtime
  (`lib/verify_compression.rb`, `lib/triggers.rb`) + three CLIs
  (`bin/compress-verify`, `bin/match-trigger`, `bin/compression-stats`).
  `PostToolUse` hook on `Bash` appends to
  `${CLAUDE_PLUGIN_DATA}/compression.jsonl` and preserves raw stdout
  under `verify-raw/<uuid>.log`. Telemetry-only — the hook does NOT
  replace Bash tool output (PostToolUse cannot do that for non-MCP
  tools per the Anthropic hooks docs). See
  `references/compression/README.md`.
- `references/compression/{triggers.yml,rules.yml,README.md}` —
  trigger regexes (rspec / rubocop / standardrb / brakeman / reek /
  `rails db:*` / whitelisted rake; env-prefix and binstub tolerant;
  `rake_excluded` precedence), preserve patterns, advisory thresholds.
- `make eval-compression` / `npm run eval:compression` — fixture eval
  wired into `eval-ci-deterministic`. Current run: 73% mean ratio, 0
  violations.
- `bin/compression-stats` — reader on Bash tool PATH. Reports counts,
  mean / p50 / p95 per command class, weak-savings, violations,
  recommendation. `--redact` emits privacy-reduced JSON intended as
  intermediate input to the `/rb:compression-report` skill (NOT a
  final paste-anywhere artifact).
- `/rb:compression-report` skill — drafts a markdown report from the
  redacted aggregate plus selective raw-log reads. User reviews the
  markdown and decides whether to file it. Skill never auto-creates
  the issue or deletes telemetry.
- `hooks/scripts/compression-data-status.sh` — `SessionStart` advisory
  hook. Read-only. Surfaces the on-disk telemetry paths when
  thresholds (`rules.yml advisory.size_threshold_bytes` /
  `sample_threshold`) cross. Does not print literal `rm` / `rm -rf`
  command strings; the user composes cleanup themselves.
- Subprocess-driven Ruby-CLI tests under `lab/eval/tests/`.

### Notes

- Default OFF. Best-effort, fail-open. No destructive code path
  shipped — cleanup is the user's `rm`.
- Symlink discipline at every write site (`${CLAUDE_PLUGIN_DATA}`,
  `verify-raw/`, `compression.jsonl`); jsonl append uses
  `O_NOFOLLOW` + `lstat` precheck.
- Runtime: Ruby ≥ 3.4, stdlib only. CI workflow installs Ruby 3.4 so
  the deterministic eval gate is not environment-dependent.

## [1.14.0] - 2026-04-25

### Added

- `/rb:intro` tutorial: Section 7 (CC built-in features — `xhigh`, `/focus`,
  `/recap`, `/less-permission-prompts`, `/output-styles`) and Section 8
  (CLAUDE.md sizing teaching + scoped-rule pattern).
- Trust-state definitions (`clean` / `weak` / `conflicted` / `missing`) on
  provenance sidecars: `references/output-verification/trust-states.md`
  and `compute_trust_state` in `lab/eval/output_checks.py`. State is
  runtime-derived (not stored in the file). `make eval-output` emits a
  trust-state distribution table over all known sidecars.
- `make check-refs` / `npm run check:refs` validator for skill and agent
  cross-references (`/rb:<name>`, `skills/<name>`, `agents/<name>`).
  Resolves frontmatter aliases and directory names; skips fenced code
  blocks; tested via `lab/eval/tests/test_check_refs.py`.
- Testing and investigation discipline references:
  `skills/testing/references/discipline.md` and
  `skills/investigate/references/discipline.md` with cross-refs from parent
  SKILL.md files.
- `init` skill: CLAUDE.md sizing pointer to tutorial Section 8.
- `requirements-dev.txt`: pins `pyyaml` for `lab/eval/` contributor
  tooling. Tests run via stdlib `unittest`; no third-party test runner
  required.
- **`make eval-ci-deterministic` / `npm run eval:ci:deterministic`** —
  full deterministic CI gate: `eval-output` + `check-refs` +
  `lab/eval/run_eval.sh --ci` (lint, injection guard,
  skill / agent / trigger scoring, ablation, hygiene + context-budget
  advisory). Audited so it never transitively invokes any LLM provider
  (`behavioral_scorer`, `epistemic_suite`, `trigger_scorer --semantic`,
  `lab.tournament.*` are all excluded). Determinism guarantee enforced by
  `lab/eval/tests/test_eval_ci_determinism.py`.

### Changed

- `permissions/references/risk-classification.md`: narrow bare-`find`
  recommendations to `find -type f -name *`, `find . -path *`, and
  `find -maxdepth *` (CC 2.1.113 no longer auto-approves `-exec`/`-delete`
  under broad `find` patterns).
- Provenance sidecars migrated to YAML-frontmatter schema (`claims`,
  `sources`, `conflicts`). `compute_trust_state` reads only this canonical
  schema; sidecars without it (or with empty `claims`/`sources`) map to
  `missing`. No markdown-body fallback. Existing tracked fixtures
  (`research-good`, `research-bad`, `review-good`, `review-bad`) updated.
  `provenance-template.md` rewritten to show the YAML schema.
- `Makefile`: new `check-refs` target.
- **`deep-bug-investigator` agent now writes its report to a file.**
  Aligned with the sibling reviewer/analyzer convention (data-integrity,
  ruby, security, migration-safety reviewers). `Write` removed from
  `disallowedTools`; added "Save Findings File First" section with the
  same turn-budget rules as siblings (write a partial mid-run, overwrite
  later). Default output path:
  `.claude/investigations/deep-bug-investigator/{slug}-{datesuffix}.md`.
  Chat response capped at ≤300 words; the file is the real output.
  `maxTurns` raised 30 → 40 to give room for live evidence gathering
  (rspec / runner / psql / redis-cli) plus a final synthesis turn —
  reviewers run static analysis at 25, investigators iterate against a
  running app and need more turns. `skills/investigate/SKILL.md` and
  `skills/investigate/references/error-patterns.md` updated to instruct
  spawners to pass an output path.

### Removed

- **`make eval-ci` / `npm run eval:ci`** — renamed to
  `eval-ci-deterministic` / `eval:ci:deterministic` to make the
  determinism guarantee explicit in the name. No back-compat alias;
  external scripts and shell history calling the old name will break and
  must be updated. The GitHub workflow, top-level `make ci`, and
  top-level `npm run ci` already point at the new name.

## [1.13.4] - 2026-04-21

### Changed

- **Contributor-only `/session-scan` reworked as SQLite-direct scanner.**
  Drops dependency on `ccrider` MCP (which truncated transcripts via
  `MAX_MCP_OUTPUT_TOKENS` at ~25K tokens, producing meaningless scores for
  sessions >~40 messages). New `.claude/skills/session-scan/references/scan-sessions.py`
  reads the local ccrider SQLite DB read-only, runs the deterministic
  scorer, appends to `metrics.jsonl`, and prints the triage table — no
  subagents, no LLM, no MCP calls. Full scan of 24 sessions drops from
  ~5.8M tokens (MCP+subagent fan-out) to <100K main-context tokens and
  completes in seconds. DB path is resolved from a generic candidate list
  (`CCRIDER_DB` env, `$XDG_CONFIG_HOME`, `~/.config/ccrider/sessions.db`,
  macOS `Application Support`, Windows `APPDATA`); skill asks the user
  for an explicit `--db PATH` before hard-failing when no candidate is
  found. Pre-filters sessions with `message_count < 5` (configurable via
  `--min-messages`). `--provider` filter retained for multi-stack users.
- **`compute-metrics.py` gains `--from-db SESSION_ID --db PATH`** mode
  for manual single-session rescoring without going through the
  orchestrator.
- **`/session-deep-dive` switches to `ccrider export` CLI** for full
  transcript retrieval instead of MCP `get_session_messages`. Same
  truncation fix, applied to qualitative analysis.

## [1.13.3] - 2026-04-19

### Added

- **`behavioral` preferences category** in
  `plugins/ruby-grape-rails/references/preferences.yml` with 3 advisory
  rules (`challenge-false-premises`, `avoid-sycophancy-loops`,
  `prefer-positive-framing`). Propagates automatically to every subagent
  via existing `inject-iron-laws.sh` (SubagentStart hook) on 1.13.3
  install — no user action required. Also reaches end-user project
  `CLAUDE.md` via `injectable-template.md` regeneration; existing
  `check-plugin-version.sh` prompts users to run `/rb:init --update`.
- **`plugins/ruby-grape-rails/references/research/epistemic-posture.md`**
  — primary-source citations (Anthropic Constitution, Claude's Character,
  Sycophancy ICLR 2024, Claude 4 Best Practices) and canonical wording
  for the 3 posture rules. Explicitly lists folklore claims deliberately
  NOT acted on ("criticism spirals", "praise resets", "absorbs
  negativity from internet discourse").
- **`lab/eval/epistemic_suite.py`** — behavioral measurement suite:
  6 metrics (apology_density, hedge_cascade_rate, finding_recall,
  false_positive_rate, unsupported_agreement_rate,
  direct_contradiction_rate) over 10 scenarios. 4 regex metrics + 2
  LLM-judge. Provider-scoped cache (keyed by system-prompt hash so
  baseline-time and post-regen responses coexist). Judge verdicts also
  cached so `--cache` reruns are fully offline after first fresh run.
  Cache misses in `--cache` mode (and judge provider errors) propagate
  as skipped scores and are excluded from the aggregate mean — a
  missing verdict is not treated as DISAGREE, so it can't silently bias
  `unsupported_agreement_rate` / `direct_contradiction_rate` toward
  0.0. New targets: `make eval-epistemic` / `npm run eval:epistemic`.
- **`lab/eval/eval_logging.py`** and **`lab/eval/eval_auth.py`** —
  shared logging helpers (`emit_info`, `verbose_lock`) and auth-settings
  helpers (`resolve_settings_path`, `cleanup_settings`) extracted from
  `behavioral_scorer.py` so the epistemic suite, trigger_expand, and
  behavioral_scorer all share one source of truth for stderr formatting
  and bare-mode claude CLI auth.
- **`scripts/check-epistemic-baseline-drift.py`** — presence gate in
  `generate-iron-law-outputs.sh` that blocks regeneration when the
  active provider's epistemic baseline is missing, `python3` is not
  on PATH, or `python3` is older than 3.14 (repo floor for `lab/eval/`
  tooling); prints baseline timestamp + hash when present so
  contributors can judge staleness. Opt out entirely with
  `EPISTEMIC_BASELINE_CHECK=0` when no epistemic measurement is
  planned.

### Changed

- **`.github/copilot-instructions.md`** Review Priorities gain 2
  IMPORTANT bullets: treat unsupported agreement with author framing as
  a defect when evidence points elsewhere; prefer direct correction
  over soft alignment for HIGH-confidence findings.
- **Root `CLAUDE.md`** Behavioral Reminders section gains an
  **Epistemic Posture** block pointing at the reference doc so
  contributor main-conversation work stays aligned with what ships to
  subagents.
- **Contributor tier** — 2 agents (`skill-effectiveness-analyzer`,
  `docs-validation-orchestrator`) and 6 skills (`docs-check`,
  `cc-changelog`, `skill-monitor`, `session-deep-dive`, `session-scan`,
  `session-trends`) gain short posture notes matching the shipped
  contract: direct language for HIGH-confidence findings, no apology
  cascades, no hedge chains, no softening of real drift into
  diplomatic language.
- **Default local eval provider/model** bumped from `gemma4:latest`
  (E4B, ~10GB) to `gemma4:26b-a4b-it-q8_0` (26B MoE Q8, ~28GB). Judge
  metrics need more capable model; smaller is documented as low-RAM
  fallback via `RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest`. Updated
  in `lab/eval/results_dir.py`, `README.md`,
  `.claude/rules/eval-workflow.md`,
  `scripts/check-contributor-prereqs.sh`, plus related tests.
- **Ollama autostart env vars** extended in
  `behavioral_scorer._ensure_ollama_server`: adds
  `OLLAMA_NUM_PARALLEL=4` and `OLLAMA_MAX_LOADED_MODELS=1` so
  `--workers > 1` actually runs concurrent provider calls instead of
  queueing at the server. Warning emitted when ollama is already
  running externally (env vars don't apply).
- **Ollama fixture + judge calls** pass `reasoning_effort=none` to
  Gemma4 26b+ reasoning models so hidden thinking tokens don't consume
  the entire `max_tokens` budget (previously caused empty responses
  even under `reasoning_effort=low` on long fixtures like
  `apology-bait-aggressive` and `subtle-bugs-diff`).
- **`scripts/generate-iron-law-outputs.sh`** now invokes the epistemic
  baseline gate before regenerating; gate hard-fails on missing
  baseline, missing `python3`, or `python3 <3.14` (opt out with
  `EPISTEMIC_BASELINE_CHECK=0`).
- **`.github/workflows/lint.yml`** Python version bumped 3.11 → 3.14
  to match the repo-documented contributor floor.

### Fixed

- **PreCompact hook no longer blocks compaction**. Previously `exit 2`
  during active `/rb:work` or `/rb:full` stranded manual `/compact` with
  only an error message and no re-read path, because PreCompact has no
  context-injection channel. Now advisory-only (stderr warning);
  PostCompact continues to emit the re-read reminder Claude acts on.
  Supersedes the 1.13.0 "PreCompact blocks compaction" entry.

### Evidence

Claims backed by Anthropic primary sources. Skips unsupported viral
framing ("criticism spirals", "praise resets", "mood" language) that
primary sources do not document. Behavioral measurement ran on 3
providers (ollama gemma4:26b-a4b-it-q8_0, haiku, apfel); gate passes
on the 2 gate providers (ollama + haiku) with ±0.05 tolerance. Apfel
is kept in the provider set for future Apple Foundation Model context
expansion but is not a gate input today (4096-token context window
overflows on several fixtures, and the 4B model is too weak to serve
as a reliable LLM-judge).

## [1.13.2] - 2026-04-19

### Changed

- **`check-plugin-version.sh` message rephrased as imperative** so Claude
  surfaces the drift warning to the user at the start of the next response
  instead of silently reading the fact from SessionStart context. Per
  `hooks.md §SessionStart`, stdout is added to Claude's context — neutral
  phrasing meant the agent could read the warning without relaying it.
  New output is prefixed `[Ruby/Rails/Grape plugin — user action required]`
  and explicitly directs the agent to tell the user and recommend
  `/rb:init --update` (or warn about plugin downgrade for newer pins).

## [1.13.1] - 2026-04-18

### Added

- **SessionStart `check-plugin-version.sh` hook** — compares `plugin v<SEMVER>`
  pinned in project CLAUDE.md (between `<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->`
  and `<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->`) against the installed plugin
  version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`. Semver-aware
  ordering via `sort -V` when supported (natural version sort; commonly
  available via GNU coreutils — some environments may require GNU `sort`/`gsort`):
  pinned-outdated emits a refresh reminder, pinned-newer flags a possible
  downgrade, equal versions stay silent. Pre-release precedence honored per
  semver (e.g. `1.13.1-rc1 < 1.13.1`); build metadata (`+<build>`) stripped
  before compare per semver.org/#spec-item-10. Fires at most once per session
  via atomic per-session lock at
  `${CLAUDE_PLUGIN_DATA}/version-check/` (workspace
  `.claude/.hook-state/version-check/` fallback). Advisory fail-open on missing
  `CLAUDE.md`, missing marker, missing `plugin.json`, or tool unavailability.
  Registered under the `startup|resume` matcher alongside `check-resume.sh`.

### Changed

- **`/rb:init` injectable template** gains `{PLUGIN_VERSION}` placeholder
  in the managed-block header comment
  (`plugins/ruby-grape-rails/skills/init/references/injectable-template.md`).
  Substitution documented in `conditional-sections.md` and
  enforced in `init/SKILL.md` (sourced from
  `jq -r '.version // empty' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"`).
  The `check-plugin-version.sh` hook depends on this marker being
  deterministic.

## [1.13.0] - 2026-04-18

### Added

- **Advisory Preferences registry** (`plugins/ruby-grape-rails/references/preferences.yml`)
  parallel to `iron-laws.yml`. First entry: prefer Context7 MCP over WebFetch
  for library/gem docs when `mcp__*context7*__*` tools are available. Emitted
  into `injectable-template.md` via new `PREFERENCES_START/END` markers and
  appended to `inject-iron-laws.sh` subagent payload as an "Advisory
  Preferences" section. Advisory only — plugin never requires Context7
  installed.
- `plugins/ruby-grape-rails/references/research/context7-usage.md` detection +
  usage reference with WebFetch fallback guidance.
- `.claude/rules/iron-laws-governance.md` contributor rule — Iron Laws may
  only be added when repeated real incidents justify them. Auto-loads when
  editing `**/iron-laws.yml`.

### Changed

- `scripts/generate-iron-law-content.rb` + `scripts/generate-iron-law-outputs.sh`
  extended to load `preferences.yml`, emit the preferences injectable block,
  and append preferences to the subagent injector payload. New bash target:
  `preferences`.
- `effort: max` → `effort: xhigh` on 4 skills (`plan`, `audit`, `review`,
  `full`). Opus 4.7 recommended default; `max` prone to overthinking per CC
  docs.
- `lab/eval/behavioral_scorer.py` sets `OLLAMA_FLASH_ATTENTION=1` and
  `OLLAMA_KV_CACHE_TYPE=q8_0` on plugin-spawned `ollama serve` processes.
  `setdefault` respects contributor overrides.
- `skills/permissions/SKILL.md` + `skills/security/SKILL.md` document
  CC 2.1.113 `sandbox.network.deniedDomains` setting for infra-layer egress
  restriction.
- `.claude/rules/eval-workflow.md` notes `ENABLE_PROMPT_CACHING_1H=1` for
  long contributor eval runs.

### Fixed

- `.claude/skills/cc-changelog/references/analysis-rules.md:37` stale
  reference to 250-char description cap updated to 1,536 combined
  `description` + `when_to_use` cap (shipped 1.12.5).

## [1.12.10] - 2026-04-18

### Changed

- **Contributor tooling: `scripts/fetch-claude-docs.sh` cache extended from 29
  to 46 pages**, now supporting nested paths (`whats-new/`, `agent-sdk/`). Added
  coverage for `best-practices`, `security`, `ultraplan`, `ultrareview`,
  `changelog`, `checkpointing`, `whats-new/index`, `remote-control`,
  `model-config`, `fast-mode`, `output-styles`, `troubleshooting`,
  `common-workflows`, and four `agent-sdk/*` parity pages. `fetch_page()`
  creates nested cache subdirectories safely; `validate_cache_target` already
  permitted subdir targets.
- **`docs-check` skill `references/doc-pages.md`** updated to reflect the
  expanded cache: page count, table entries, and new "Which Pages To Read"
  buckets for CC Version Tracking, Remote Control, Effort Tiering, Plugin
  Best Practices, Security Baseline, File Checkpointing, and SDK Parity
  Checks.

## [1.12.9] - 2026-04-17

### Fixed

- **`install-statusline-wrapper.sh` macOS install path** now calls
  `chmod 0755 "$TMP"` without GNU-style `--`, allowing the SessionStart hook
  to create `~/.claude/ruby-grape-rails-subagent-statusline` on macOS
  instead of silently deleting the temp wrapper and exiting advisory-success.

## [1.12.8] - 2026-04-16

### Added

- **Plugin-level `subagentStatusLine`** — ships
  `plugins/ruby-grape-rails/settings.json` plus
  `bin/subagent-statusline`, overriding the default subagent panel row
  with `{emoji} {label}  {status_dot} {elapsed}  {tokens}  {cwd_tail}`.
  Emoji maps the task label to a role via stem-matching (review,
  orchestrat, investigat, analy, research, verif/runner, valid,
  architect/design, specialist/sidekiq, judge/iron-law,
  advisor/runtime, trace, supervis, explore, plan/planning, security,
  migration/deploy, test) with a generic fallback. Label source falls
  back across `.label // .description // .name` (real CC payload omits
  `.name` and only provides `.label` + `.description`). Status dot
  reflects `task.status`. Elapsed derives from `task.startTime`
  auto-detecting epoch milliseconds (13-digit), epoch seconds, or ISO
  8601 strings. Tokens are humanized (`8432` → `8.4k`,
  `1250000` → `1.2M`). `cwd_tail` shows the last path segment — useful
  when specialists run in parallel git worktrees. Advisory: empty
  stdout on any error falls back to CC's default row.
- **`install-statusline-wrapper.sh` SessionStart hook** — idempotently
  writes a small wrapper at
  `~/.claude/ruby-grape-rails-subagent-statusline` that `exec`s the
  current plugin's `bin/subagent-statusline`. Needed because plugin
  `settings.json` does NOT expand `${CLAUDE_PLUGIN_ROOT}` and CC does
  not export that variable to the statusline subprocess, nor does
  plugin `bin/` get added to the statusline subprocess PATH (all three
  confirmed via `claude --debug` diagnostic; see `plugins-reference.md`
  documented substitution scope). The wrapper is rewritten only when
  its content differs from the desired content, so version bumps
  refresh it and unchanged sessions are no-ops. Advisory: any error
  exits 0 silently.

### Changed

- **docs-check cached doc surface** expanded from 18 to 29 Claude Code doc
  pages. Added Tier 1 schema/contract pages (`claude-directory.md`,
  `commands.md`, `plugin-dependencies.md`, `env-vars.md`, `errors.md`) and
  Tier 2 context pages (`cli-reference.md`, `statusline.md`,
  `discover-plugins.md`, `sandboxing.md`, `context-window.md`,
  `code-review.md`).
- **`.claude/skills/docs-check/references/doc-pages.md`** indexes the new
  pages and adds routing sections for `.claude/` layout, hook runtime
  contract, CLI/statusline, and built-in feature overlap.

## [1.12.7] - 2026-04-16

### Fixed

- **`session-title.sh` hook** now enforces first-prompt-only titling via an
  in-script atomic per-session lock directory instead of the plugin-level
  `"once": true` field on the `UserPromptSubmit` handler. Current Claude
  Code docs restrict `once` to skill-scoped hooks; this switches to a
  documented mechanism without behavior change. Lock lives under
  `${CLAUDE_PLUGIN_DATA}/session-titles/` (or
  `${REPO_ROOT}/.claude/.hook-state/session-titles/` when the plugin data
  dir is unavailable).

## [1.12.6] - 2026-04-16

### Added

- **Ollama provider for behavioral eval** — local OpenAI-compatible routing
  calls with default model `gemma4:latest`, auto-started `ollama serve` for
  fresh runs, model-specific cache namespace (`gemma4` for
  `gemma4:latest`), and no prompt truncation.

### Changed

- **Behavioral eval default provider** switched from apfel to Ollama Gemma4;
  apfel and haiku remain available through `--provider` or
  `RUBY_PLUGIN_EVAL_PROVIDER`.
- **Behavioral routing prompts and deterministic confusable-pair analysis**
  now include both `description` and `when_to_use`. Apfel receives capped
  routing text (70 chars from each field) to fit its 4096-token context;
  Ollama and haiku receive the full routing text.

## [1.12.5] - 2026-04-16

### Added

- **SubagentStop hook** — async metrics logging to
  `${CLAUDE_PLUGIN_DATA}/.agent_metrics.jsonl` with agent_id, agent_type,
  timestamp. New hook event (12→13 events)
- **Review complexity tiering** — Simple (1-3 files), Medium (4-10),
  Complex (11+) with auto-escalation on critical paths (auth, payment,
  migrations, middleware)
- **Review confidence levels** — HIGH (code evidence), MEDIUM (pattern match),
  LOW (subjective) on all review findings
- **`when_to_use` frontmatter** on all 51 skills with trigger phrases and
  negative routing for overlap-prone skills
- **Top-level `description`** in hooks.json for `/hooks` menu display

### Changed

- **Skill description cap** raised from 250 to 1,536 characters across
  CLAUDE.md checklist, contributor rules, eval scorer, eval matchers, and
  all 51 eval JSON fixtures
- **All 51 skill descriptions** standardized with "Use when" prefix, trigger
  phrases via `when_to_use`, and negative routing on overlap-prone skills
  (review/audit/verify/challenge, investigate/trace/research,
  brainstorm/plan, compound/learn)
- **`effort: max`** (Opus 4.6) for heavy orchestrators: plan, audit,
  review, full (was `high`)
- **PreCompact hook** now blocks compaction (exit 2) during active `/rb:work`
  or `/rb:full` execution; planning phase still allows compaction with
  context warning
- **Review template** updated with Complexity header and Confidence column
  in summary table

## [1.12.4] - 2026-04-14

### Added

- **`bin/resolve-base-ref`** — shared script for resolving base branch remote
  ref. Handles custom remote names (not just `origin`), non-standard default
  branches, and fetches before resolving to prevent stale-ref diffs.

### Changed

- Skills and agents that compare branches now use `resolve-base-ref` instead
  of ad-hoc `origin/main` / `origin/master` fallback chains: `document`,
  `work`, `plan`, `verify`, `verification-runner`
- `verify/references/verification-profiles.md` pronto base-ref blocks updated

### Removed

- **`check-branch-freshness.sh`** — unwired utility script since v1.0.3,
  superseded by `bin/resolve-base-ref`

## [1.12.3] - 2026-04-13

### Added

- **Apfel provider for behavioral eval** — on-device Apple Foundation Model
  via `apfel --serve`. Zero API cost, ~1-2s per call. Enable with
  `--provider apfel` (default). Auto-starts server on non-`--cache` runs;
  skipped for cache-only. Connects via OpenAI Python SDK with connection-pool
  reuse. Supports remote endpoints via `APFEL_BASE_URL` (probe-only, no local
  spawn when non-loopback). Invalid `APFEL_PORT` values warn and fall back;
  invalid, empty, or malformed `APFEL_BASE_URL` values raise a
  `RuntimeError`. Full skill descriptions sent (no truncation); context
  overflow and guardrail rejections surface as typed failures. Results under
  `lab/eval/triggers/results/apfel/`; haiku results separate under
  `lab/eval/triggers/results/haiku/`.
- **Provider-aware behavioral dimension** — `RUBY_PLUGIN_EVAL_PROVIDER` env
  var selects which cached results (apfel/haiku) feed the behavioral eval.
  Invalid values warn and fall back.
- **Error classification in behavioral scorer** — canonical set:
  `budget`, `max_turns`, `parse_error`, `context_overflow`, `timeout`,
  `guardrail_blocked`, `server_unavailable`, `dependency_missing`,
  `rate_limited`, `unknown`. Both providers share `context_overflow`,
  `guardrail_blocked`, `timeout`, `dependency_missing`,
  `server_unavailable`, `unknown`. Haiku also emits `budget`, `max_turns`,
  `parse_error`, `rate_limited` (Claude-API/CLI-specific conditions that
  don't apply to on-device apfel). Surfaced per-skill in `failure_types`
  dict.
- **`--provider` flag on `neighbor_regression`** — switch routing provider
  for confusable-pair regression without setting env vars; parity with
  `behavioral_scorer`.
- **Local Python dev setup support for apfel provider** — `.venv/` and
  `.envrc` added to `.gitignore` (not shipped); documented install path
  `.venv/bin/pip install openai httpx` and optional direnv `.envrc`
  auto-activation for local dev environments.
- **Review agent "Save Findings File First" guidance** — all 9 review
  agents (ruby-reviewer, testing-reviewer, iron-law-judge, security-analyzer,
  sidekiq-specialist, deployment-validator, verification-runner,
  data-integrity-reviewer, migration-safety-reviewer) now instruct Claude
  to write findings file by turn ~15 with partial content if needed, then
  overwrite with final version. Fallback path matches orchestrator contract
  (`{review-slug}-{datesuffix}.md`). Pattern borrowed from
  claude-elixir-phoenix v2.8.1.

### Changed

- **Review agent `maxTurns: 15 → 25`** (verification-runner: 10 → 20) —
  more runway before hitting turn limit without writing findings.
- **`logging` module for behavioral scorer** — replaced scattered
  `print(..., file=sys.stderr)` + custom `_ts()` timestamp helper with
  standard Python `logging` (`%(asctime)s %(message)s` format). Per-thread
  log buffering preserved for parallel workers. Progress lines (`Testing X...
  SKIPPED (...)` and worker-failure summaries) stay on plain stderr in
  non-verbose mode to avoid timestamp interleaving.
- **Behavioral scorer argparse** — new `--provider {apfel,haiku}` flag.
- **Apfel response parser** — strips markdown code fences and deduplicates
  repeated skill names (both behaviors apfel occasionally produces).
- **Apfel server config** — launched with fixed `--max-concurrent 16`;
  `x_context_output_reserve: 64` to maximize input budget; `max_retries=0`
  on client to avoid SDK-level retry loops masking issues;
  `_ensure_apfel_server()` called once from `main()` before worker threads
  spawn.
- **Timeout retry for apfel** — up to 3 attempts on timeout (Apple FM can
  enter transient slow states). Other error types do not retry.
- **Cost summary shows active provider** — header
  `--- Cost Summary ({provider}) ---`; call-count labeled "Total successful
  calls" (apfel is on-device, not API).

### Fixed

- **"haiku call failed" log message** → `"{provider} call failed [{error_type}]"`
  — surfaces which provider and why.

## [1.12.2] - 2026-04-11

### Added

- **Service-layer `paths:` for `rails-idioms`** — policies, queries,
  decorators, presenters, validators, interactors, operations, commands,
  structs, value_objects with packwerk-aware variants.
- **`security` skill `paths:`** — app/policies for authorization auto-load.
- **Haml/Slim view support** — hotwire-patterns and hotwire-native now
  trigger on `.haml` and `.slim` templates.
- **Grape representers/serializers paths** — grape-idioms auto-loads for
  app/representers and app/serializers.
- **GitLab CI paths for `deploy`** — `.gitlab-ci.yml` and `.gitlab/**`.
- **Explicit packwerk/engine/component patterns** — all framework skills
  now include `{packs,engines,components}/*/{...}` and
  `app/{packages,packs}/*/{...}` for modular monolith layouts.

### Changed

- **Brace expansion across all skill paths** — consolidated patterns
  using picomatch `{a,b}` syntax.

### Fixed

- **security-reminder hook `config/*` → `config/**`** — now matches nested
  config paths (environments, initializers, credentials).
- **docs-check page inventory** — updated from 9 to 18 pages, matching
  current fetch-claude-docs.sh PAGES list.
- **cc-changelog analysis-rules stale paths** — fixed plugin-qualified
  paths for hook script references.
- **Contributor prereqs** — added cksum, cat, cp, find, mkdir, head, tr,
  wc to match hook runtime hard dependencies.
- **README pre-commit description** — added shellcheck lint mention.

## [1.12.1] - 2026-04-11

### Fixed

- **README dashboard counts** — Iron Laws 21→22, Events 11→12 to match
  canonical sources (iron-laws.yml, hooks.json).
- **CLAUDE.md iron-laws.yml path** — bare `iron-laws.yml` →
  `plugins/ruby-grape-rails/references/iron-laws.yml`.
- **work SKILL.md active-plan-marker path** — bare command → full
  `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/` path.
- **iron-law-judge grep recipes** — Law-18 `\s` in BRE → `[[:space:]]` with
  `-E`; method_missing unsafe xargs splitting → NUL-safe `while read` loop.
- **validate-yaml.sh Python fallback** — added PyYAML import check before
  selecting Python path; explicit UTF-8 encoding on open.
- **fetch-cc-changelog.sh GITHUB_TOKEN** — implemented optional Bearer auth
  header (was hinted in error message but not used).
- **Makefile .PHONY** — added `eval-behavioral-passk`,
  `eval-behavioral-rotations`, `eval-trigger-expand`.
- **iron-laws.yml comment** — removed hardcoded `(1-22)` ID range.
- **iron-law generator schema alignment** — added warnings for missing
  recommended fields (severity, applies_to, init_text, detector_id,
  reference_files). Injectable section now uses `init_text` with
  `summary_text` fallback.
- **check-contributor-prereqs.sh** — added grep, sed, awk, mktemp, readlink
  to required checks, aligning with README-documented hook dependencies.

## [1.12.0] - 2026-04-11

### Added

- **`paths:` frontmatter on 12 framework-specific skills** — rails-idioms,
  active-record-patterns, active-record-constraint-debug, ar-n1-check,
  grape-idioms, sidekiq, karafka, hotwire-patterns, hotwire-native,
  sequel-patterns, async-patterns, deploy. Uses `**/` packwerk-aware globs
  for modular monolith support (packs, packages, components, engines).
- **`.claude/rules/` path-scoped contributor rules** — agent-development,
  skill-development, hook-development load only when editing matching files.
  Always-loaded rules for development and eval workflow.
- **Context budget eval checks** (`lab/eval/context_budget.py`) — advisory
  CLAUDE.md line count and framework skill paths: coverage checks. Zero API
  cost, wired into `make eval`, `make eval-all`, `make eval-ci`.
- **Configurable hook timeouts** — env var overrides for slow sub-commands:
  `RUBY_PLUGIN_FORMATTER_TIMEOUT` (120s), `RUBY_PLUGIN_RUBY_CHECK_TIMEOUT`
  (30s), `RUBY_PLUGIN_BETTERLEAKS_TIMEOUT` (60s),
  `RUBY_PLUGIN_DETECT_STACK_TIMEOUT` (15s). Advisory hooks skip on timeout,
  security hooks fail closed.

### Changed

- **CLAUDE.md restructured from 873 to 185 lines** (79% reduction). Dropped
  end-user behavioral instructions block (already shipped via skills/agents/
  hooks). Moved contributor conventions to `.claude/rules/` files. Moved
  features tracking to local-only `features-under-evaluation.md`.
- **Raised hook timeout ceilings** — rubyish-post-edit 45s→600s,
  secret-scan 30s→180s, post-tool-use-failure 15s→30s. Prevents premature
  kills on large codebases.
- **macOS `timeout` compatibility** — hooks resolve `timeout` → `gtimeout` →
  no-timeout fallback via `run_with_timeout()` for stock macOS without
  coreutils.
- **Updated Copilot review instructions** — added context budget module,
  configurable timeouts, path-scoped rules, missing frontmatter fields.

## [1.11.8] - 2026-04-11

### Fixed

- **Corrected cost estimates from real verification runs.** Measured:
  avg ~$0.006/call (was $0.005, varies $0.005-0.007 by skill complexity),
  621 prompts across 51 skills (was 410). Updated docstrings in
  `behavioral_scorer.py` and `trigger_expand.py`. Real costs: baseline
  ~$3.70 (was ~$2), rotations N=5 ~$19 (was ~$4-6), samples N=3 ~$11
  (was ~$6), trigger expand ~$0.01/skill (was ~$0.005).
- **Semantic pairs timeout** — increased subprocess timeout from 60s to 120s.
  51 descriptions in one prompt needs more processing time than single-prompt
  routing calls.
- **Sharpened skill descriptions for routing accuracy** — Applied contrastive
  "When/When NOT" pattern (DiaFORGE method) to confusable skills:
  `intent-detection` now explicitly excludes intro territory,
  `intro` excludes intent-detection territory,
  `investigate` excludes perf and rb:trace territory.
  Improved investigate accuracy under rotations (83% → 92%).
- **Fixed investigate corpus defect** — Replaced self-referential prompt
  ("check if investigate needs updating") that all 5 rotations misrouted.
  Replaced with genuine investigation prompt. Investigate accuracy under
  rotations: 83% → 92%, hard tier: 50% → 75%.
- **Fixed intent-detection terse prompt** — "which command?" too ambiguous
  without task context, replaced with task-bearing variant.
- **Intent-detection remains ORDER-SENSITIVE** (range=0.15-0.23) — a
  structural limitation of meta-skills competing alongside the skills they
  route to. Contrastive "NOT for X" description worsened accuracy (69%);
  reverted to softer discriminator holding at 92%. Architectural fix
  (pre-filter stage or system prompt directive) deferred to future version.

## [1.11.7] - 2026-04-11

### Added

- **Order-bias control for behavioral eval** (`--rotations N`) — Cyclic
  rotation of the skill description list (BiasBusters method). Majority-vote
  per-prompt pass/fail across N rotations. Reports `per_rotation_accuracy`,
  `order_range`, `order_stddev`, `routing_consistency`. Flags order-sensitive
  skills when `order_range > 0.15`. Default 1 (backward compat), recommended 5.
  Strided offsets (BiasBusters method): 5 rotations over 51 skills uses
  offsets [0, 10, 20, 30, 40] for maximum positional spread.
- **pass@k routing robustness** (`--samples N`) — Independent routing
  samples measuring recoverability. Reports `pass_at_k` (at least 1 of N
  correct) and `sample_consistency` (all N agree, τ-bench pass^k analog).
  Flags inconsistent routing when `pass_at_k - accuracy > 0.15`.
  Mutually exclusive with `--rotations` (error if both > 1).
- **Semantic confusable pairs** (`--semantic` flag on trigger_scorer) —
  Single bare-mode Haiku call identifies semantically close skill pairs
  missed by token overlap. Merges with existing Jaccard pairs, deduplicates,
  caches by description content hash. Top 15 pairs returned.
- **Self-sampled trigger expansion** (`trigger_expand.py`) — Generates
  candidate trigger prompts via Haiku with style diversity constraints
  (frustrated dev, terse, typo, non-native, precise). Quality gates reject
  near-duplicates (>80% token overlap), description echoes (>50%), skill
  name leaks, and length violations. Output to `candidates/` for mandatory
  manual review — never auto-merged.
- **New eval targets**: `make eval-behavioral-passk`, `make eval-behavioral-rotations`,
  `make eval-trigger-expand SKILL=x`, and npm equivalents.

## [1.11.6] - 2026-04-11

### Added

- **Artifact recovery for parallel-reviewer** — Explicit fallback when
  background subagents fail to write review artifacts (known CC platform
  limitation). Orchestrator checks each expected artifact path after agent
  completion, extracts findings from agent conversation result, and writes
  the file itself instead of relying on CC's unpredictable recovery cascade.
- **Context-supervisor write fallback in planning-orchestrator** — Same
  pattern: if context-supervisor fails to write `consolidated.md`, the
  orchestrator reads the agent result and writes the summary itself.
- **Agent Dispatch notes on confusable skills** — `rb:trace` and
  `rb:investigate` skills now include explicit "this is a skill, not an
  agent" guidance with correct `subagent_type` references (`call-tracer`,
  `deep-bug-investigator`). Prevents CC from trying to spawn skill names
  via the Agent tool.

### Changed

- **CLAUDE.md trimmed below 40k char threshold** — Removed duplicate
  Reference Auto-Loading section, compressed Colon in Skill Names
  divergence notes, removed redundant hooks.json JSON skeleton, and
  compressed PreToolUse variant enumeration. No information loss.

### Fixed

- **Skill/agent confusion causing "Agent type not found" errors** —
  Claude sometimes tried to spawn `rb-trace` as an agent instead of using
  the `call-tracer` agent or invoking the `/rb:trace` skill. Agent Dispatch
  sections disambiguate the two highest-risk skill/agent pairs.

## [1.11.5] - 2026-04-10

### Added

- **Parallel workers for behavioral eval** — `--workers N` flag for
  `behavioral_scorer.py`. Uses `ThreadPoolExecutor` to parallelize
  independent `run_haiku()` calls. Workers return `CallResult` objects,
  cost aggregated in main thread after collection. Signal handler for
  clean Ctrl+C shutdown (cancels pending futures, waits for running
  workers). Default 1 for backward compat, recommended 4 for ~3-4x
  speedup on full runs.

## [1.11.4] - 2026-04-10

### Added

- **Iron Law #22: Surgical Changes Only** — "Every changed line should trace
  directly to the user's request." Adds concrete line-count test ("if you
  write 200 lines and it could be 50, rewrite it") to the canonical registry.
- **Difficulty-stratified behavioral reporting** — Behavioral scorer now
  reads `hard_should_trigger` / `hard_should_not_trigger` buckets and reports
  `easy_accuracy`, `hard_accuracy`, tier counts. Summary shows tiered breakdown.
  Behavioral dimension adds easy-tier (>=90%, blocking) and hard-tier (>=50%,
  advisory) assertions.
- **Fork/lock trigger classification** — Trigger corpora accept optional
  `routing` ("fork"/"lock") and `valid_skills` fields. Fork prompts score
  correct if any returned skill is in `valid_skills`. Core 6 skills annotated
  (plan/brainstorm confusables marked fork). Trigger scorer validates fork
  prompts have `valid_skills`. Behavioral scorer reports `fork_accuracy` and
  `lock_accuracy`.
- **Failure triage annotation schema** — Separate
  `triggers/annotations/{skill}_annotations.json` for manual failure
  attribution (`router_defect`, `corpus_defect`, `ambiguity_mislabel`,
  `judge_artifact`, `unknown`). Keyed by `(prompt, expected)` pairs.
- **Fork/lock routing modes in intent-detection** — Routing modes section
  with Lock (act immediately), Fork (don't pick silently — present options),
  and Trivial (just do it). Behavior steps updated.
- **Error critic fork/lock awareness** — `LOCK_PATTERNS` for high-confidence
  single-fix errors (SyntaxError, LoadError, Zeitwerk, NoDatabaseError).
  `SOFT_LOCK_PATTERNS` for errors that are lock-like on repeat (NameError,
  NoMethodError). Fork errors escalate to `/rb:investigate`.
- **Eval-set sensitivity analysis** — New `lab/eval/eval_sensitivity.py`
  with leave-one-out metric fragility, 4-tier prompt classification
  (high-leverage, drag, redundant, contributing). $0 cost, pure recomputation.
  New `make eval-sensitivity` / `npm run eval:sensitivity` targets.

### Changed

- **Skill/agent wording hardening** — Ruby reviewer and challenge agents add
  simplicity self-check ("would a senior engineer say this is overcomplicated?").
  Plan skill mandates `→ verify:` criteria per checkbox. Intent-detection fork
  guidance: "don't pick silently."

## [1.11.3] - 2026-04-09

### Added

- **Auto session titles via `UserPromptSubmit` hook** — Sessions are
  automatically named from the first prompt. `/rb:plan build auth` becomes
  `"rb:plan — build auth"`, `/rb:work .claude/plans/auth-system/plan.md`
  becomes `"rb:work — auth-system"`, and free-form prompts use the first
  ~60 characters. Uses `hookSpecificOutput.sessionTitle` (CC v2.1.94+).
  Fires once per session via `"once": true`. Improves session history
  navigation and `--resume` discoverability.

### Changed

- **Hardened `bin/` executable paths in skills** — `detect-stack` and
  `extract-permissions` invocations now use explicit
  `${CLAUDE_PLUGIN_ROOT}/bin/` paths instead of bare command names. Prevents
  model path-conflation when skills also reference `${CLAUDE_SKILL_DIR}`.
- **Downgraded colon-naming compatibility risk** — Rewritten from "risk" to
  "documented behavior divergence" after CC 2.1.94 stabilized
  frontmatter-name-based invocation for plugin skills.
- **Rewrote Features Under Evaluation** — Marked `UserPromptSubmit` +
  `sessionTitle` as adopted; moved `keep-coding-instructions` to Output Styles
  (was misclassified under Skills); noted per-skill YAML frontmatter hooks
  are now documented and available; corrected plugin `settings.json` guidance.

### Removed

- **Removed `plugins/ruby-grape-rails/settings.json`** — Both shipped keys
  (`"effort": "medium"` and `"showTurnDuration": true`) were silently ignored
  by Claude Code. Plugin-root `settings.json` only supports the `agent` key.

## [1.11.2] - 2026-04-04

### Fixed

- Fixed `extract-permissions` project slug detection — was appending a SHA256
  hash suffix that Claude Code doesn't use, causing 0 sessions found. Now
  detects the actual project directory by scanning `~/.claude/projects/`.

## [1.11.1] - 2026-04-04

### Fixed

- Behavioral scorer passes prompt via stdin instead of CLI argument to avoid
  `ARG_MAX` limits and process list exposure.
- Behavioral scorer uses JSON output format for per-call cost and token
  reporting in verbose mode.
- Raised `--max-budget-usd` from 0.02 to 0.10 — Claude CLI injects a ~44k
  token system prompt, making $0.02 insufficient for even one haiku call.
- Verbose output shows skill name in bracket prefix and full prompt text
  without redundant prompt dump.
- Improved 9 trigger corpora for better routing accuracy: replaced ambiguous
  should_not_trigger prompts and strengthened should_trigger prompts. 49/51
  skills now at 100% behavioral accuracy.

## [1.11.0] - 2026-04-04

### Added

- **Matcher ablation tooling** — leave-one-out analysis identifying signal vs
  guardrail vs noise matchers across all 51 skills. New commands:
  `make eval-ablation` / `npm run eval:ablation`.
- **Neighbor regression tooling** — detects routing theft between confusable
  skill pairs when descriptions change. Builds bidirectional neighbor map from
  confusable pairs, flags accuracy drops >10%. New commands:
  `make eval-neighbor` / `npm run eval:neighbor`.
- **Contamination hygiene checks** — reusable scanner for trigger corpus leaks
  (command refs, multi-word skill names, description echo, hard-corpus quality).
  New commands: `make eval-hygiene` / `npm run eval:hygiene`.

### Changed

- Improved behavioral accuracy for 15 underperforming skills. Removed 43
  generic "Help me with X patterns" trigger prompts (test contamination).
  Tuned descriptions for `full`, `intent-detection`, and `quick` to improve
  routing recall. All 3 critical skills rose from 62-75% to 100% accuracy.

## [1.10.0] - 2026-04-04

### Added

- **`/cc-changelog` contributor skill** — Track Claude Code version changes
  against plugin surfaces (hooks, agents, skills, config). Fetches releases
  from GitHub API, classifies entries as BREAKING/OPPORTUNITY/RELEVANT
  FIX/DEPRECATION/INFO, and cross-references impact against hooks.json events,
  skill/agent frontmatter, plugin.json manifest, and settings.json keys.
  Includes `scripts/fetch-cc-changelog.sh` for GitHub releases API with
  `--all` and `--set=VERSION` flags. State tracked in
  `.claude/cc-changelog/last-checked-version.txt`.
- **Behavioral eval dimension** — LLM-based trigger routing tests using Haiku.
  Sends test prompts against all 51 skill descriptions, haiku picks 1-3 most
  relevant skills, computes accuracy/precision/recall per skill. Results cached
  in `lab/eval/triggers/results/` with content-hash invalidation. Activated
  with `--behavioral` flag on scorer. New commands: `make eval-behavioral` /
  `npm run eval:behavioral` (cache-only), `eval-behavioral-verbose` (with
  prompt/response debug), `eval-behavioral-fresh` (force re-run), and
  `eval-behavioral-fresh-verbose`. Uses a configured weight of `0.08` when
  enabled. Returns neutral 1.0 for skills without cached results.

## [1.9.0] - 2026-04-03

### Added

- **`/rb:learn` upgraded to full learn-from-fix workflow** — Replaced 14-line
  stub with 5-step workflow: identify root cause, check for duplicates across
  4 knowledge stores (common-mistakes.md, project CLAUDE.md, .claude/solutions/,
  auto-memory), decide destination based on scope, write lesson in standardized
  format, suggest future detection. Supports three output destinations: project
  CLAUDE.md for project-specific conventions, auto-memory for cross-project
  lessons (with user consent), and .claude/solutions/ via /rb:compound for
  complex fix stories. New `learn-workflow.md` reference with detailed guidance.
- **Plugin settings.json** — Adds plugin-root `settings.json` with
  `effort: medium` and `showTurnDuration: true`.
- **Full 51/51 eval coverage** — Added 44 eval definitions covering all shipped
  skills. Wave 1 covers 18 workflow and diagnostic skills with heavier evals.
  Wave 2 covers 16 domain-reference skills with frontmatter and reference
  checks. Wave 3 covers 10 small/stub skills with minimal evals. Achieves
  Elixir-level eval parity (100% skill coverage).
- **Full 51/51 trigger corpora** — Added 44 trigger files with should_trigger,
  should_not_trigger, hard_should_trigger, and hard_should_not_trigger prompts
  for routing quality regression detection.

### Changed

- **PostToolUse `security-reminder.sh` narrowed with declarative `if` filter** —
  Now fires only on code and config files (*.rb,*.rake, *Gemfile, *Rakefile,
  config/*,*.yml, *.env*, *.json) instead of all Edit|Write operations.
  Editing markdown or documentation files no longer triggers the security
  reminder. `secret-scan.sh` and `log-progress.sh` remain broad.

## [1.8.1] - 2026-04-03

### Changed

- **Agent tool access migrated from allowlist to denylist pattern** — Removed
  explicit `tools:` allowlists from 17 specialist agents and switched to
  `disallowedTools:` only (denylist). This follows Claude Code's built-in agent
  pattern (Explore, Plan, Verification) where agents inherit all tools
  implicitly. All specialists also block
  `Agent, EnterWorktree, ExitWorktree, Skill` — tools not covered by hooks or
  shellfirm. Bash stays available because `block-dangerous-ops.sh` and
  shellfirm guard shell commands. Artifact-writing agents use
  `disallowedTools: Edit, NotebookEdit, Agent, EnterWorktree, ExitWorktree, Skill`.
  Conversation-only agents add `Write`.
  `parallel-reviewer` keeps `Agent` for spawning sub-reviewers. Agents with
  intentionally narrow tool sets (web-researcher, output-verifier,
  ruby-gem-researcher) keep `tools:` allowlists.
- **Agent eval tooling updated for denylist-only pattern** — `tools_present`,
  `read_only_tools_coherent`, and `omit_claudemd_coherent` matchers now
  correctly handle agents without a `tools:` field. `read_only_tools_coherent`
  requires `Edit` and `NotebookEdit` in the denylist. Six new unit tests cover
  the denylist-only code paths.

## [1.8.0] - 2026-04-03

### Added

- **`/rb:brainstorm` — Adaptive requirements gathering** — New command skill
  implementing an interview-research-synthesis loop for ideation before
  planning. Asks context-aware questions across 6 dimensions (What, Why, Scope,
  Where, How, Edge), runs codebase scans between questions, and offers parallel
  research via `rails-patterns-analyst` + `web-researcher`. Produces
  `interview.md` that `/rb:plan` consumes to skip clarification.
- **`/rb:plan` interview detection** — Skips clarification when brainstorm
  `interview.md` found with `Status: COMPLETE`.

### Changed

- **`disableSkillShellExecution` resilience** — All executable bash blocks in
  SKILL.md files converted from fenced code blocks to inline prose instructions.
  Skills now instruct Claude via prose ("Run `bundle exec rspec`", "Use Grep to
  search...") instead of bash blocks. Works with CC v2.1.91's
  `disableSkillShellExecution` setting. Documentation/example blocks converted
  to plain fenced blocks. Shell commands preserved in backticks; tool-replaceable
  commands (grep, find) converted to Claude tool references (Grep, Glob).
- **Removed `disable-model-invocation` from plan, work, review, investigate** —
  Unblocks programmatic `Skill()` calls during workflow transitions
  (brainstorm→plan, work→review). Kept on research, pr-review, perf where
  unwanted auto-loading is a real risk.

## [1.7.4] - 2026-04-03

### Changed

- **Skill scripts moved to `bin/` for bare-command invocation** — `detect-stack`
  and `extract-permissions` are now shipped under `plugins/ruby-grape-rails/bin/`
  and added to the Bash tool's PATH when the plugin is enabled (CC v2.1.91+).
  Skills invoke them as bare commands (`detect-stack`, `extract-permissions`)
  instead of requiring `ruby "${CLAUDE_PLUGIN_ROOT}/scripts/..."` or
  `ruby "${CLAUDE_SKILL_DIR}/scripts/..."` path resolution. Hook scripts that
  call `detect-stack` use the updated relative path. Empty `scripts/`
  directories removed.

## [1.7.3] - 2026-04-02

### Changed

- Adjust shell redirection patterns in hook scripts and documentation to improve
  compatibility with shellfirm security tooling.

## [1.7.2] - 2026-04-02

### Changed

- **Read-only agent context is leaner and more predictable** — shipped skill and
  agent evals now enforce Claude's practical `250`-character description
  budget, contributor docs call it out explicitly, and read-only specialist
  agents now opt into `omitClaudeMd: true` so they keep product/runtime context
  while skipping contributor-only guidance.
- **Session startup now feels faster without dropping runtime awareness** —
  startup writes a fast `.runtime_env` snapshot first, pushes slower helper
  probing into an async background refresh, and initializes missing scratchpads
  earlier for active or resumable plans.
- **Hook routing is more selective on the hot path** — Ruby-ish post-edit work
  now flows through `rubyish-post-edit.sh` for Iron Law verification,
  formatting, syntax checks, and debug-statement warnings, progress logging is
  async, the plan STOP reminder runs only for `Write(*plan.md)`, and
  `PostToolUseFailure` stays narrowed to Ruby-relevant Bash command families.
- **Runtime and contributor failure paths are clearer under degraded conditions** —
  `detect-runtime.sh` now warns when runtime state directories cannot be
  prepared, `error-critic.sh` warns when hook-state storage or updates fail,
  `run_eval.sh` now distinguishes the scoring gate from runtime tests and emits
  explicit temporary-file errors, and changed-mode eval no longer treats
  deleted or moved changed skills/agents as note-only skips.
- **Contributor integrity checks are stricter and less lossy** —
  fallback dynamic-injection scans now fail when coverage is partial, the
  permissions extractor no longer relies on glob-interpolated transcript paths
  and now reports malformed JSONL lines, and contributor verification docs now
  point at concrete output fixtures instead of only the parent directory.
- **Contributor validation is now wired into the main quality gates** —
  local `ci` entrypoints now include `claude plugin validate`, and the GitHub
  Actions workflow now runs a dedicated plugin-structure validation job instead
  of relying on docs or manual contributor discipline alone.
- **Background-agent orchestration guidance now matches current Claude Code
  behavior** — stale `TaskOutput` instructions were removed from the planning
  workflow, and the contributor guidance now consistently treats background
  agent completion as notification-driven with explicit reads of written output
  files.
- **Agent turn limits are now explicit across the shipped specialist set** —
  the remaining Ruby agents now declare `maxTurns`, which makes runaway-agent
  protection more consistent beyond the core orchestrators.
- **Permission extraction is more robust and shell-aware** — the permissions
  extractor now supports transcript-root overrides for contributor analysis,
  rejects malformed settings/transcript shapes without crashing, and uses
  parser-backed shell splitting when `shfmt` is available while preserving the
  safer fallback behavior when it is not.

## [1.7.1] - 2026-03-29

### Changed

- **Search-tool guidance now prefers built-in repository tools first** —
  orchestrator and init prompts now recommend `Grep` / `Glob` before shell
  search, prefer `ag` or `rg` when shell search is needed, and explicitly say
  Ruby type filters should use `ag --ruby` or `rg --type ruby`, never `rb`.

## [1.7.0] - 2026-03-28

### Added

- **Deterministic research/review output eval** — `lab/eval/artifact_scorer.py`
  now scores tracked research/review fixture artifacts, and contributors can run
  it directly via `make eval-output` / `npm run eval:output`.
- **Shared provenance contract references** — added
  `plugins/ruby-grape-rails/references/output-verification/provenance-template.md`
  so research/review provenance sidecars have a canonical documented structure
  instead of only path conventions.

### Changed

- **Research/review provenance guidance is now explicit and aligned** —
  `output-verifier`, `research`, `review`, and `parallel-reviewer` now all
  point to the same shared provenance contract, distinguish when provenance is
  required vs optional, and describe how verified findings should be applied
  back to the final artifact.
- **Output-verification evals are stricter and more deterministic** — the
  research/review artifact checks now enforce the shared provenance contract
  more precisely, handle CRLF and UTF-8 input consistently, and cover the
  contract with dedicated regression tests instead of relying on looser
  fixture-only validation.
- **Contributor-only output-verification guidance now lives under `.claude/`**
  — the shipped plugin keeps the provenance template, while the contributor
  checklist moved to
  `.claude/skills/plugin-dev-workflow/references/output-verification-checklist.md`.
- **Contributor eval and docs-cache tooling now fail more predictably** —
  `run_eval.sh --changed` is tracked-only by default, reports deleted changed
  skills/agents explicitly, and adds `--include-untracked` for opt-in local
  work, while `fetch-claude-docs.sh` now fails incomplete refreshes by default
  and reserves `--allow-partial` for best-effort refreshes.
- **Hosted and local contributor gates now use the same stricter eval surface** —
  the GitHub Actions workflow now runs the eval CI gate, JSON validation uses
  tracked file manifests, `check-dynamic-injection.sh` covers `.claude-plugin`
  too, and agent evals fail with explicit missing-file errors instead of bare
  tracebacks.
- **Destructive-operation and contributor entrypoint hardening continued** —
  the dangerous-ops hook now blocks plain `rails` and `rake` destructive DB
  commands too, and the contributor pre-commit / lint entrypoints were updated
  to use path-safe file handling instead of brittle whitespace-splitting loops.
- **Dangerous-op blocking and Ruby hook detection are now more consistent** —
  the destructive-op hook now covers quoted and namespaced DB tasks,
  `git -c ... push --force`, common `bash -lc` / `sh -lc` wrappers, several
  common `ruby -e` inline execution forms (`system(...)`, backticks, `%q/%Q`,
  `%x{...}`, `exec(...)`), and Redis flushes under stock macOS Bash, while
  Ruby gem detection now understands `gem(...)` and gemspec-driven repos
  across the runtime detector, stack detector, and formatter. The Ruby-ish
  post-edit hook surface was also collapsed behind a shared wrapper to reduce
  repeated wiring drift.
- **Secret scanning, runtime detection, and permission extraction are more
  consistent under degraded conditions** — Betterleaks runtime failures are now
  surfaced instead of silently passing, runtime detection no longer needs the
  `just` binary just to parse a justfile and uses consistent full-Rails
  fallbacks, the permissions extractor uses safer repo-root heuristics plus
  explicit transcript caps, and the Iron Law output generator no longer depends
  on the Ruby helper having an executable bit.
- **Iron Law projection updates now fail closed when bounded markers are
  missing** — `generate-iron-law-outputs.sh` no longer warns-and-skips missing
  bounded sections for README or judge projections, which reduces silent
  partial-regeneration risk.
- **Full Rails app detection is more conservative without depending only on
  `bin/rails`** — runtime fallback and verifier guidance now treat a repo as a
  runnable full Rails app only when it has a real Rails entrypoint or the
  standard runnable app layout, instead of assuming stray config files alone are
  enough.

## [1.6.3] - 2026-03-28

### Changed

- **Marketplace-installed specialist agents now rely on explicit permission
  allowlists instead of ignored plugin-agent `permissionMode` fields** — all
  shipped plugin agents dropped `permissionMode: bypassPermissions`, and the
  user-facing docs now point users to project `permissions.allow` rules such as
  `Bash(bundle *)`, `Bash(rails *)`, `Bash(rake *)`, `Read(*)`, `Grep(*)`, and
  `Glob(*)`.
- **Runtime detection now refreshes on directory changes too** — `CwdChanged`
  now reuses the same quiet runtime refresh wrapper as `FileChanged`, so
  `.claude/.runtime_env` stays aligned when the session moves between repos or
  package roots mid-run.
- **Compound knowledge flow now relies on explicit references instead of an
  undocumented skill-to-skill preload** — `/rb:compound` now points directly to
  the `compound-docs` schema/template references, `compound-docs` is framed as
  a reusable background reference skill, and `/rb:plan` / `planning-orchestrator`
  now consult `.claude/solutions/` explicitly instead of referring to a
  nonexistent `compound-docs` agent.
- **Dead `MultiEdit` branches were removed from the current shipped hook
  surface** — hook matchers now target `Edit|Write`, stale `MultiEdit` handler
  groups are gone, and current-facing contributor docs no longer describe it as
  an active edit tool in the shipped runtime surface.

## [1.6.2] - 2026-03-28

### Changed

- **Docs-check stale-warning handling is tighter** — contributor docs-check
  guidance now treats dated reports as historical snapshots, and the archived
  `report-2026-03-28` explicitly marks its old `MultiEdit` warning as
  superseded by newer Claude docs.
- **Post-edit hook spawning is narrower on the hottest Ruby paths** —
  `format-ruby`, `verify-ruby`, and `debug-statement-warning` now use
  handler-level `if` filters so they only spawn for Ruby-ish file edits instead
  of every `Edit|MultiEdit|Write`.
- **Runtime detection now refreshes mid-session when core project files
  change** — `FileChanged` now reruns `detect-runtime.sh` for `Gemfile`,
  `Gemfile.lock`, `Rakefile`, `lefthook.yml`, `justfile`, and `*.gemspec`,
  while using a dedicated quiet wrapper for refreshes instead of branching on
  untrusted hook input.
- **Hook narrowing now applies consistently across Ruby-ish file edits** —
  quiet runtime refreshes no longer leak status output, `debug-statement-warning`
  no longer runs twice from both broad and filtered hook groups, `config.ru`
  now gets the same debug-statement coverage as the other Ruby-ish targets, and
  the `FileChanged` lefthook matcher now covers the same config variants that
  runtime detection already recognizes.
- **Selective skill `paths:` adoption started conservatively** —
  `safe-migrations` now narrows to migration/schema files and `testing` narrows
  to `spec/**` and `test/**`, while broader auto-loading constraints remain
  deferred.

## [1.6.1] - 2026-03-28

### Added

- **Agent playbooks for leaner orchestration docs** — moved long-form
  dependency-analysis, planning, and workflow examples into
  `plugins/ruby-grape-rails/references/agent-playbooks/` so the main agent
  routing surfaces stay concise without losing the detailed contributor
  guidance.

### Changed

- **`dependency-analyzer` is now a focused routing surface instead of a giant
  example dump** — the agent description is more discriminative, the main file
  is much shorter, and the detailed command/report examples now live in a
  dedicated playbook.
- **Core workflow descriptions were tightened to reduce trigger overlap** —
  `plan`, `work`, `review`, and `verify` now use more boundary-specific
  descriptions and less repetitive stack-keyword padding.
- **Trigger corpora were sharpened without adding answer leakage** — the
  `plan`, `work`, and `verify` trigger sets now separate design, execution, and
  final-check intent more clearly while preserving human-realistic prompts.
- **Secondary agent descriptions are now more discriminative** —
  `context-supervisor`, `data-integrity-reviewer`, `migration-safety-reviewer`,
  and `ruby-gem-researcher` now state their boundaries more concretely instead
  of relying on generic repo-wide keywords.
- **Oversized orchestrators were slimmed down materially** —
  `planning-orchestrator` and `workflow-orchestrator` now keep the state
  machine and hard rules in the agent file while delegating bulky templates and
  examples to playbooks.
- **Deterministic eval results improved across the board** — all 23 shipped
  agents now score `1.0`, and the hottest overlap pairs dropped materially:
  `plan` vs `work` (`0.1739 -> 0.1209`), `review` vs `verify`
  (`0.1717 -> 0.1319`), and `verify` vs `work` (`0.1648 -> 0.1059`).
- **Contributor docs-check now tracks the real cached Claude feature surface
  more closely** — local docs-check guidance now uses `claude plugin validate`
  as the baseline, prefers targeted cached-doc snippets over pasted megacontext,
  prefers `Agent(...)` terminology, and recognizes current fields/events such
  as skill `paths` / `shell`, hook `FileChanged`, and plugin `userConfig` /
  `channels`.
- **Contributor session analytics are now framed more honestly and scoped more
  cleanly** — session-scan, deep-dive, trends, and skill-monitor now treat
  transcript-derived metrics as exploratory, remove stale `MEMORY.md` /
  historical-report dependencies, support provider-scoped analysis guidance,
  and stop implying session chaining or fixed adoption baselines that the
  current tooling does not actually implement.
- **Session trend scoring is less noisy and more explicit about tiny ledgers**
  — shipped command detection now normalizes both `/rb:*` and
  `/ruby-grape-rails:*`, contributor analyzer commands are excluded from
  adoption metrics, retry-loop friction now requires nearby failure evidence,
  and trend output now exposes `immature_ledger`, `distinct_dates`, and
  `time_series_signal` so early snapshots are not misread as meaningful
  time-series trends.
- **Contributor session-scan metrics now handle more real transcript shapes**
  — plugin opportunity checks now tolerate both bare and prefixed command
  forms, nested `edits` payloads contribute to edited-file metrics, and
  same-message Bash `tool_result` failures are recognized when scoring retry
  loops.
- **Broad raw `rm` examples were reduced further** — the docs-cache fetcher now
  validates cache-file cleanup before deleting failed downloads, and the deploy
  docs now prefer `apt-get clean`, `bundle clean --force`, and Rails cleanup
  tasks over broad recursive `rm -rf` examples.
- **Session-scan now sees Bash activity in ccrider-style text transcripts**
  — text-mode shell commands are now inferred into real Bash command entries,
  which lets plugin-opportunity heuristics and retry-loop friction scoring work
  even when transcripts do not preserve structured `tool_use` blocks.
- **Docs fetch cleanup is now best-effort and assistant failure detection is
  less trigger-happy** — refused cache-file cleanup no longer aborts the docs
  fetch flow under `set -e`, and session-scan now avoids counting generic
  assistant prose like “if you see an error” as real failure evidence while
  still catching stronger signals such as exit codes and explicit error lines.
- **User-side failure detection is narrower, and docs-check wording is more
  explicit about ignored agent fields** — session-scan no longer treats generic
  user phrases like “without error” as real failure evidence, and docs-check
  now states that `hooks`, `mcpServers`, and `permissionMode` are unsupported
  and ignored for plugin-shipped agents.
- **Command-alias analytics are now consistent and covered by tests** —
  session-scan normalizes `/ruby-grape-rails:*` to `/rb:*` in skill
  effectiveness as well as adoption metrics, trend date parsing now avoids
  duplicate work, and new Python tests cover command extraction, placeholder
  filtering, and alias normalization.
- **Per-skill analytics now reuse the same text-mode tool inference path** —
  ccrider-style Bash commands in assistant text now contribute consistently to
  skill-effectiveness windows, and the focused session-scan test module now
  fails with an explicit import error instead of relying on a bare `assert`.
- **`/rb:investigate` opportunity suggestions now use the same retry-loop logic
  as friction scoring** — plugin-opportunity scoring no longer relies on a
  coarser adjacent-command heuristic, and it now suppresses `investigate`
  suggestions when that command was already used.
- **Contributor command snippets are more copy-safe again** — the session
  trends `rg` example no longer over-escapes JSON brackets, and the Docker
  cleanup example now runs `rails tmp:clear` under `RAILS_ENV=production` with
  a dummy secret key so it still boots correctly in deployment-mode bundles.
- **Session-scan tool inference is stricter and less prose-sensitive** —
  ccrider-style text transcripts now infer tools only from tool-like forms such
  as backticked names, `tool:Name`, or `Name(...)`, so ordinary English uses of
  words like `Agent` and `Task` no longer inflate tool counts, while the
  focused session-scan tests now fail earlier with a clearer import error if the
  metrics module is missing.

## [1.6.0] - 2026-03-28

### Added

- **Deterministic contributor eval foundation (`lab/eval/`)** — added a
  stdlib-only Python scoring framework for contributor use, including skill
  scoring, agent scoring, trigger corpus validation, baselines, comparison,
  confusable-pair analysis, hard-corpus generation, and deterministic stress
  checks.
- **Core skill eval definitions** — shipped dedicated eval JSON files for the
  highest-leverage skills: `plan`, `work`, `review`, `verify`, `permissions`,
  and `research`.
- **Trigger corpora for core workflows** — added deterministic trigger sets for
  the same six skills, plus tooling to validate them and surface confusable
  pairs.
- **Contributor entrypoints** — added `Makefile` targets and matching
  `package.json` scripts for eval, baseline creation, comparison, overlap
  analysis, hard-corpus generation, stress checks, and eval tests.
- **Dynamic context injection guard** — added
  `scripts/check-dynamic-injection.sh` plus contributor entrypoints to block
  tracked plugin files from using `!\`command\`` context injection syntax.

### Changed

- **Contributor docs now describe the eval workflow explicitly** — README,
  CLAUDE, and `plugin-dev-workflow` now point contributors to the `lab/eval`
  commands and clarify that this is contributor-only infrastructure, not a new
  shipped runtime feature.
- **Core skill routing surfaces were tightened from eval findings** —
  `plan`, `work`, `review`, `verify`, `permissions`, and `research` now have
  stronger trigger descriptions, corrected references, explicit Iron Laws where
  expected, and leaner main skill bodies. Large verification/checklist examples
  moved into references so the primary routing surface stays focused.
- **Eval runner ergonomics now match the contributor workflow better** —
  `npm run eval` / `make eval` now lint tracked Markdown, run the injection
  guard, and score changed surfaces by default, while `eval-all`, `eval-ci`,
  `eval-skills`, `eval-agents`, and `eval-triggers` expose clearer targeted
  modes.
- **Contributor eval tests now support pytest cleanly** — the repo now ships
  `pytest.ini`, explicit `pytest` test commands, and a deterministic default
  eval-test wrapper based on `unittest` while keeping the explicit `pytest`
  path available.
- **`/rb:state-audit` examples now prefer `rg` over brittle `grep -r`
  patterns** — state-audit guidance now avoids shell-globstar-dependent
  examples and uses faster ripgrep commands instead.
- **Secret scan missing-tool behavior now surfaces real gaps more clearly** —
  secret scanning still soft-fails when Betterleaks is absent, but strict mode
  or secret-looking edits now emit an explicit warning instead of skipping
  silently.
- **Tutorial section anchors are now renderer-stable** — the `/rb:intro`
  tutorial content now uses `and`-based headings and matching links instead of
  `&`-dependent anchor slugs.
- **Eval safety checks now catch more real issues** — the eval harness now
  detects `rm -rf /`-style patterns correctly, the dynamic-injection guard
  flags `!\`command\`` inside tracked JSON as well as Markdown, and agent
  tool-coherence scoring can now fail for read-oriented agents that forgot to
  block write-capable tools.
- **Contributor scripts are now harder to misuse** — the Iron Laws content
  generator now uses `YAML.safe_load` with explicit top-level shape checks, the
  secret-scan hook no longer calls helper logic before it is defined, and the
  eval-test wrapper is directly executable as well as callable via `bash`.
- **Eval contributor tooling is now more deterministic and less redundant** —
  trigger prompt normalization now sorts tokens before duplicate comparison,
  and contributor `ci` entrypoints no longer run lint and injection checks
  twice when `eval:ci` already covers them.
- **Eval contributor flows now fail and document prerequisites more cleanly** —
  the changed-surface eval marker only persists after a successful run, review
  guidance now points to the real `/rb:learn` command, and contributor docs now
  state that `lab/eval/` requires Python 3.10+.
- **Internal skill layout is now more consistent for `/rb:learn`** — the
  shipped skill directory was renamed from `learn-from-fix` to `learn` while
  keeping the user-facing command as `/rb:learn`.
- **Eval frontmatter parsing and Python prerequisites are now clearer** — the
  eval parser now understands inline comma-separated list fields used in agent
  frontmatter, coverage includes that form explicitly, and both eval entrypoint
  scripts now fail fast with a clear Python 3.10+ requirement message.
- **Eval frontmatter parsing now treats empty list-like keys correctly** —
  empty `tools`, `disallowedTools`, and `skills` fields now parse as empty
  lists instead of empty strings, so agent checks do not miscount blank
  frontmatter as present configuration.
- **Environment support is now stated explicitly** — README and contributor
  docs now say the plugin/tooling is validated on macOS, Linux, and WSL, and
  that native Windows is not currently supported.
- **Eval test execution is now less cwd-sensitive** — the eval-test wrapper now
  resolves the repo root before running and uses an explicit unittest top-level
  path, so the non-pytest fallback works more reliably outside the repository
  root.
- **Permissions extraction now rejects invalid scan windows and limits** — the
  canonical `/rb:permissions` extractor now fails fast when `--days` is
  negative or `--limit` is zero/non-positive, and the reference doc now
  documents those constraints explicitly.

## [1.5.0] - 2026-03-28

### Added

- **Structured scratchpad template + hook support** — active plans now use a
  canonical scratchpad structure with `Dead Ends`, `Decisions`,
  `Hypotheses`, `Open Questions`, and `Handoff`, and the hook layer now
  initializes missing scratchpads, highlights dead ends on resume, and
  preserves dead-end context across compaction.
- **T1-T5 source-quality tiers for web research** — `web-researcher` and
  `/rb:research` now classify sources from authoritative (`T1`) through
  rejected (`T5`), require visible tier tags in research output, and call out
  source-quality mix in synthesis.
- **`output-verifier` agent** — new internal verifier agent for
  provenance-checking research briefs and review findings when they rely on
  external or version-specific claims.
- **Contributor `plugin-dev-workflow` skill** — new local `.claude` skill
  documenting how to validate shipped plugin changes, keep release metadata
  aligned, and maintain audit/roadmap files in this repo.

### Changed

- **Research and review workflows now support provenance sidecars** —
  high-impact research and externally sourced review claims can now be checked
  with `output-verifier` and saved as adjacent `.provenance.md` reports.
- **Scratchpad guidance is now canonical across planning/workflow docs** —
  planning, work, brief, and compound guidance now use the same section model
  instead of mixed ad-hoc `DEAD-END` / `DECISION` entry styles.
- **Scratchpad dead-end handling is now more precise** — hook-level dead-end
  counts now track top-level entries instead of nested detail bullets, and the
  compound/planning docs now point to the correct scratchpad template and a
  working section-extraction example.
- **Scratchpad examples are now less ambiguous** — multi-plan scratchpad
  extraction examples label which file a block came from, and dead-end
  examples now show only the entry body to reinforce appending under the
  existing `## Dead Ends` section.
- **Scratchpad handoff insertion now preserves literal note content** —
  hook-written handoff notes no longer route arbitrary text through `awk -v`,
  avoiding backslash escape corruption in persisted scratchpad context.
- **Scratchpad creation now refuses non-regular existing targets** —
  `ensure_scratchpad_file()` now bails if `scratchpad.md` already exists as a
  directory, FIFO, or other non-file path instead of letting `mv -f` behave
  unexpectedly.
- **`ACTIVE_PLAN` marker writes now apply the same non-regular-path guard** —
  the active-plan marker now refuses existing directory/FIFO-style targets
  before replacing the marker file.
- **Shell cleanup paths are now more defensive** — shipped hook scripts now
  validate temp-file/temp-dir prefixes before deleting, refuse non-regular
  existing targets for exact/temp file cleanup, prefer exact-path cleanup for
  plugin-owned markers, and the verification examples now show the same safer
  cleanup style.
- **Cleanup hardening now avoids brittle trap quoting** — temp cleanup traps
  now use local cleanup functions instead of embedded quoted path patterns, and
  symlinked `ACTIVE_PLAN` markers are surfaced as manual-cleanup warnings
  rather than silently mishandled.
- **Strict secret scans now use a visible file budget instead of silent truncation** —
  the no-file-path strict-mode secret scan now uses a configurable file cap
  (`RUBY_PLUGIN_SECRET_SCAN_MAX_FILES`, default `200`) and emits a warning
  when coverage is truncated.
- **Workspace path canonicalization now follows symlink targets fully** —
  helper path checks now resolve the actual target path instead of only
  normalizing the parent directory.
- **Active-plan marker read failures now fall back correctly** — transient
  `.claude/ACTIVE_PLAN` read issues no longer suppress the normal plan-state
  fallback heuristics.
- **Symlinked `ACTIVE_PLAN` markers no longer disable plan auto-detection** —
  the hook layer still warns about manual cleanup, but now continues into the
  normal fallback heuristics instead of short-circuiting active-plan lookup.
- **Resume progress summaries now count both `- [x]` and `- [X]`** —
  checked-task reporting no longer undercounts uppercase Markdown checkboxes.
- **SessionStart scratchpad checks are now read-only** — startup/resume no
  longer auto-creates missing `scratchpad.md` files just to report plan state.
- **PreCompact no longer injects raw scratchpad dead-end text into system context** —
  compaction hints now reference dead-end counts and the scratchpad path while
  explicitly treating scratchpad content as untrusted repo notes.
- **`scratchpad-lib.sh` now requires `workspace-root-lib.sh` explicitly** —
  the shared scratchpad library no longer pretends to support standalone
  temp-cleanup fallbacks when the root helper library is unavailable.
- **Debug references no longer default to nuclear rebuilds** — investigate
  quick-command docs now prefer staged cache-clear / install / precompile
  steps instead of recommending broad `rm -rf` cleanup by default.
- **Release/docs metadata now reflects the expanded shipped surface** — the
  plugin now ships `23` agents, `50` skills, `152` skill references, and `25`
  hook scripts, and README / CLAUDE / intro content were updated to match.

## [1.4.0] - 2026-03-27

### Added

- **`/rb:permissions`** — new permission-analysis skill that scans recent
  Claude session JSONL files, compares real Bash usage against current
  `settings.json` rules, classifies risk, and recommends safer Ruby-project
  permission entries instead of broad guesswork. The skill now ships with a
  canonical Ruby extractor under
  `plugins/ruby-grape-rails/skills/permissions/scripts/extract_permissions.rb`.

### Changed

- **`/rb:verify` is now more project-aware** — runtime detection and
  verification guidance now surface and prefer clear repo-native composite
  verification entrypoints such as `./bin/check`, `./bin/ci`, `make ci`, and
  `bundle exec rake ci` before falling back to the direct lint/security/test
  sequence.
- **Runtime state now persists verify-wrapper hints** —
  `.claude/.runtime_env` can now expose `VERIFY_COMPOSITE_AVAILABLE`,
  `VERIFY_COMPOSITE_COMMAND`, and `VERIFY_COMPOSITE_SOURCE` alongside the
  existing direct-tool booleans.
- **User-facing docs now include permission tuning as a first-class workflow**
  — README, intro/tutorial content, injected template quick reference, and
  contributor command guidance now point users to `/rb:permissions` when
  approval prompts become noisy.
- **`/rb:verify` now treats cached verify-wrapper commands as untrusted hints**
  — user-facing verification guidance and agent instructions now re-detect any
  repo-native composite wrapper from the working tree before execution instead
  of running a raw command string from `.claude/.runtime_env`.
- **`/rb:permissions` extractor docs now match actual output** — the extractor
  reports first-line command snippets truncated to 300 characters, and the
  reference docs now say so explicitly.

## [1.3.1] - 2026-03-26

### Changed

- **CLI-first parsing is now recommended across the main user-facing workflow surface** —
  the injected `CLAUDE.md` block and core orchestrators now recommend
  preferring CLI tools such as `jq`, `yq`, `rg`, `ag`, `awk`, `sed`, `sort`,
  `cut`, and `uniq` for parsing/filtering work, then Ruby, and only using
  ad-hoc Python as a last resort.

## [1.3.0] - 2026-03-25

### Changed

- **Planning now reuses fresh research cache more deliberately** —
  `/rb:plan` and `planning-orchestrator` now check `.claude/research/`
  and prior plan research before respawning duplicate gem/tool/community
  research, using in-file `Date:` / `Last Updated:` metadata for
  deterministic freshness checks, while still requiring live
  code-discovery agents for the current repo.
- **Planning now compresses reused and fresh research before
  synthesis** — `planning-orchestrator` runs `context-supervisor`
  against plan-local research plus any reused cached files, then plans
  from `summaries/consolidated.md` instead of pulling every raw report
  into context.
- **SessionStart now pre-creates `.claude/research/`** — reusable
  research has a stable top-level home instead of depending on each plan
  namespace to exist first.

## [1.2.0] - 2026-03-24

### Changed

- **Verification tool detection is now first-class** — `detect-runtime.sh`
  now exports dedicated state for `standardrb`, `rubocop`, `brakeman`,
  `lefthook`, and `pronto`, instead of treating verification only as an
  implicit docs-level convention.
- **Lefthook policy is now explicit** — the plugin keeps direct tools as the
  source of truth and only treats Lefthook as a wrapper when its detected
  config covers both lint and security/static-analysis checks. Tests remain
  separate.
- **Pronto policy is now explicit** — Pronto is treated as an optional final
  diff-scoped pass, not as a replacement for direct lint or security
  verification.
- **Init docs no longer hardcode stale tool version examples** — `/rb:init`
  now prefers detector/runtime output instead of frozen sample versions for
  stack/tool guidance.
- **Verification workflows now consume cached tool state more explicitly** —
  `/rb:verify`, `verification-runner`, and the injected template now key their
  command-selection guidance off `.claude/.runtime_env` booleans instead of
  vague “if configured” phrasing alone.
- **Verification examples now degrade more safely without runtime cache** —
  the injected template and `/rb:verify` example scripts fall back to repo
  detection when `.claude/.runtime_env` is missing, guard Rails-only database
  checks, and only run Pronto when it is actually configured.
- **Verification examples now handle optional checks more explicitly** —
  fallback full-Rails detection no longer depends on executable `bin/rails`,
  Sorbet is skipped only when it truly appears unconfigured, and optional
  Pronto runs now log non-blocking failures instead of silently masking them.
- **Lefthook diff-lint coverage is now modeled separately** —
  `LEFTHOOK_DIFF_LINT_COVERED=true` captures Pronto + `pronto-rubocop` style
  diff-scoped lint coverage without pretending that it replaces full direct
  lint execution.
- **Lefthook lint coverage detection now recognizes `standard`** — configs that
  invoke StandardRB via `standard` are now treated as lint-covered, not just
  those using `standardrb` or `rubocop`.
- **Verification enforcement text is now conditional instead of universal** —
  injected/init/plan/work/review orchestration docs no longer imply that
  `zeitwerk:check`, `standardrb`, `rubocop`, or `brakeman` are always
  available in every repo.

## [1.1.1] - 2026-03-24

### Changed

- **RTK guidance is now external-integration only** — removed the long
  injected RTK command-preference section from `/rb:init` output and agent
  guidance. The plugin now treats RTK as an optional external Claude setup and
  asks users whether they want to enable it before pointing them to
  `rtk init -g`, instead of implying RTK detection alone can enforce command
  rewriting.

## [1.1.0] - 2026-03-23

### Added

- **Skill `effort` frontmatter across all 49 shipped skills** — Workflow
  skills now use higher effort where orchestration matters, while lightweight
  skills use lower effort for cheaper, faster execution.
- **`PostCompact` hook (`postcompact-verify.sh`)** — Adds an advisory
  post-compaction reminder that points Claude back to active plan, scratchpad,
  and progress artifacts when needed.
- **`StopFailure` hook (`stop-failure-log.sh`)** — Persists normalized API
  failure context into the active plan scratchpad so resume flows can recover
  with better context.
- **Mixed-ORM and package-layout detection** — `detect-stack.rb` and
  `detect-runtime.sh` now emit and persist `DETECTED_ORMS`, `PRIMARY_ORM`,
  `PACKAGE_LAYOUT`, `PACKAGE_LOCATIONS`, `PACKAGE_QUERY_NEEDED`, and
  `HAS_PACKWERK` for init/workflow guidance.

### Changed

- **`/rb:init` stack detection** now relies on `detect-stack.rb` as the single
  source of truth instead of ad-hoc inline parsing.
- **Init / plan / research / work / review guidance** now identifies package
  ownership and the active ORM before recommending migration, callback, review,
  or enqueue behavior.
- **Iron Laws and injected guidance are now ORM-aware** for commit-safe
  enqueueing, distinguishing Active Record `after_commit` advice from Sequel
  transaction-hook patterns.
- **Packwerk and modular-monolith workflows** are now first-class in init and
  planning flows, including explicit user questioning when explicit package
  roots like `packages/*`, `packs/*`, `app/packages/*`, or `app/packs/*` are
  detected without explicit Packwerk signals.
- **Stack detection now distinguishes Rails components from a full Rails app**
  via `RAILS_COMPONENTS=true|false` and `FULL_RAILS_APP=true|false`, which
  helps mixed Grape + Rails-component repos avoid being mislabeled as full
  Rails apps.
- **Modular package detection is now more conservative and package-root
  focused** — discovery now keys off explicit package roots like `packages/*`,
  `packs/*`, `app/packages/*`, and `app/packs/*`, while avoiding broad nested
  Rails namespacing roots that produced false positives in ordinary apps. Once
  inside those explicit roots, detection is intentionally softer so lightweight
  packages still trigger ownership/boundary questions. Explicit Packwerk
  detection now depends on `packwerk.yml` rather than generic package
  manifests.
- **`StopFailure` recovery notes are phase-aware** — planning-phase failures now
  point back to `research/` and `scratchpad.md`, while work-phase failures keep
  the `plan.md` / `progress.md` resume flow.
- **Planning-phase recovery no longer depends solely on `ACTIVE_PLAN`** —
  active-plan fallback can now rediscover `research/`-only planning work when
  the marker file is missing or stale.
- **Sidekiq summary guidance is now ORM-scoped end-to-end** — the condensed
  checklist no longer reverts to unconditional Active Record / Active Job
  advice in mixed-ORM repos.
- **Explicit-root package detection is softer but still package-shaped** —
  supported roots now require actual code/package evidence instead of treating
  any arbitrary child directory as a package candidate.
- **Init template modular triggers now match detector policy** — generic
  `package.yml` alone no longer implies modular-boundary support outside the
  detector's explicit roots.
- **Runtime detection now persists `PRIMARY_ORM`** in `.claude/.runtime_env`,
  keeping the cached runtime state aligned with the detector output contract.
- **`${CLAUDE_SKILL_DIR}` adoption** was added selectively in workflow skills
  where explicit local reference paths improve reliability across plugin cache
  and install contexts.
- **`/rb:intro` tutorial wording** now clearly separates hook-backed automation
  from behavioral file-pattern guidance, so context-aware references are no
  longer described like guaranteed plugin infrastructure.
- **Contributor authoring guidance** now treats skill/agent length limits as
  targets rather than hard constraints, matching the practical size of some
  shipped orchestrators and deep reference-heavy skills.

### Fixed

- Normalized `file_path` handling across remaining validation/warning hooks so
  repo-relative hook payload paths resolve against the workspace root instead of
  silently no-oping outside the repo cwd.
- Hardened `/rb:document` pre-check guidance for shallow/new repos so the
  “recent Ruby files” gate no longer relies on a brittle `HEAD~5` pipeline.
- Made Iron Law regeneration fail when bounded replacement markers are malformed
  instead of logging success on unchanged content.
- Tightened explicit-root modular detection so supported roots require
  package-shaped evidence while still recognizing lighter Ruby/Grape package
  layouts.
- Rebalanced active-plan fallback so actionable work plans beat stale
  planning-phase directories when the `ACTIVE_PLAN` marker is missing.
- Improved planning-phase rediscovery recency so fallback uses real planning
  activity under `research/` and `scratchpad.md`, not just the `research/`
  directory node mtime.
- Aligned SessionStart stack reporting with `detect-stack.rb`, eliminating raw
  Gemfile grep false positives from commented-out gems.
- Added a minimal exact-Gemfile fallback in `detect-runtime.sh` so SessionStart
  still reports obvious stack/ORM signals when the Ruby-based detector cannot
  run.
- Tightened degraded-mode Rails detection so `detect-runtime.sh` no longer
  treats `gem 'rails'` alone as proof of a full Rails app when the Ruby
  detector cannot run.
- Removed misleading `zeitwerk:check --resolve` guidance from `/rb:verify`.
- Corrected `/rb:document` “new Ruby files” guidance to use added-file
  detection (`--diff-filter=A`) instead of matching any modified Ruby file.
- Expanded the float-for-money Iron Law detector to catch both `t.float` and
  `add_column ..., :float` migration forms, including parenthesized
  `add_column(...)` style.
- Rebalanced `security-reminder.sh` path matching so common security-sensitive
  filenames like `access_token.rb`, `payment_*`, and `permission_*` still
  trigger reminders while broad false positives like `tokenizer` /
  `administer` no longer do.
- Aligned pending-plan detection between startup and stop hooks by making
  `check-pending-plans.sh` look for real unchecked task lines instead of any
  unchecked checkbox text.
- Removed duplicate generic startup messaging by dropping the extra
  `check-resume.sh` fallback banner when SessionStart already prints the
  standard plugin-loaded message.
- Restored signal-safe cleanup for temporary `ACTIVE_PLAN.XXXXXX` marker files
  during `set_active_plan()` writes.
- Made `stop-failure-log.sh` self-heal stale lock directories after a short
  TTL, preventing abandoned locks from suppressing future failure logging.
- Scoped `debug-statement-warning.sh` away from the plugin's own generator and
  detector script directories so intentional `puts`-based tool output is not
  treated like production debug code.
- Closed unbalanced Markdown fences in `rb:research` output examples and the
  Ruby 3.4 features reference.
- Fixed generated/documented Iron Law references and examples:
  `generate-iron-law-outputs.sh` now supports `--help`, rejects unknown
  targets, and the canonical registry now links to the real YAML source;
  research/compound example docs no longer contain placeholder broken links;
  generated injector output no longer churns on wall-clock timestamps; and the
  generated README now points “full registry” at the canonical registry markdown
  instead of raw YAML.

## [1.0.4] - 2026-03-23

### Fixed

- **`/rb:init` stack detection** — Switched init stack/version parsing to exact
  gem-name matches so Rails no longer falsely resolves from gems like
  `rubocop-rails`. `detect-stack.rb` now emits resolved `GRAPE_VERSION`,
  `SIDEKIQ_VERSION`, `KARAFKA_VERSION`, and related version fields so injected
  `CLAUDE.md` headers prefer exact locked versions over degrading to plain
  `detected`.

## [1.0.3] - 2026-03-23

### Changed

- Merged `detect-runtime.sh`, `detect-betterleaks.sh`, and `detect-rtk.sh` into one SessionStart detector that exports runtime, tool, and hook-mode state
- Added hook modes: `default` for quieter startup / targeted secret scanning, `strict` for broader secret checks
- Fixed hook workspace-root resolution so installed plugins use the active project workspace instead of the plugin cache for `.claude/` state, formatter detection, and resume/plan tracking
- Promoted nested launch directories to the actual project root via git/worktree detection, with `Gemfile` / `.claude` ancestor fallback for non-git cases
- Refused filesystem root (`/`) as a valid workspace root and added non-empty root guards before `.claude` writes
- Threaded hook stdin payloads consistently into workspace-root resolution so `.cwd` from hook JSON is honored across SessionStart, resume, formatting, and active-plan flows
- Expanded post-write hook coverage from `Edit|Write` to `Edit|MultiEdit|Write`
- Hardened hook path handling, `.runtime_env` persistence, and sourceable runtime state generation
- Hardened active-plan state handling with tighter `.claude` confinement and safer marker access
- Clarified contributor testing guidance: `claude --plugin-dir ...` is the primary local working-tree workflow, while local marketplace install validates marketplace distribution behavior
- Added MySQL detection (`mysql2`) alongside PostgreSQL in runtime and init stack detection
- Switched marketplace plugin source to `git-subdir` so URL-based marketplace distribution can target `plugins/ruby-grape-rails/`
- Pinned the `git-subdir` marketplace source to `ref: v1.0.3` so marketplace installs fetch the released plugin revision instead of the moving default branch

## [1.0.2] - 2026-03-23

## [1.0.1] - 2026-03-23

### Changed

**Review Artifacts** — Standardized review output paths and follow-up workflow:

- Reviewer agents now write per-agent artifacts to `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md`
- Consolidated review output now lives at `.claude/reviews/{review-slug}.md`
- `/rb:triage` now consumes consolidated review output and generates a follow-up plan at `.claude/plans/{slug}/plan.md`
- Review, triage, and root documentation were updated to reflect the standalone-review plus plan-follow-up model

## [1.0.0] - 2026-03-22

### Added

**Initial release of the Ruby/Rails/Grape plugin** — A comprehensive development toolkit for Ruby ecosystems with specialist agents, Iron Laws, and verification workflows.

#### Core Workflow Commands

- **`/rb:plan`** — Creates implementation plans by spawning Ruby specialists in parallel. Outputs structured plans with task checkboxes to `.claude/plans/{slug}/`
- **`/rb:work`** — Executes plans task-by-task with verification checkpoints. Resumes automatically from first unchecked task
- **`/rb:review`** — 4-agent parallel code review (ruby-reviewer, security-analyzer, testing-reviewer, verification-runner)
- **`/rb:compound`** — Captures solved problems as reusable knowledge in `.claude/solutions/`
- **`/rb:full`** — Autonomous cycle: plan → work → verify → review → compound

#### Workflow Support Commands

- **`/rb:brief`** — Interactive plan walkthrough with visual formatting
- **`/rb:triage`** — Interactive review finding triage
- **`/rb:quick`** — Fast implementation for small changes (<100 lines)
- **`/rb:verify`** — Full verification: format (StandardRB or RuboCop), tests (RSpec/Minitest), and Rails-specific checks (zeitwerk:check)
- **`/rb:init`** — Initialize plugin in project (injects rules into CLAUDE.md)

#### Investigation & Debug Commands

- **`/rb:investigate`** — 4-track parallel bug investigation (state, code, dependencies, root cause)
- **`/rb:trace`** — Build call trees to trace method flow
- **`/rb:n1-check`** — Detect N+1 query patterns in Active Record
- **`/rb:constraint-debug`** — Debug ActiveRecord constraint violations

#### Analysis Commands

- **`/rb:audit`** — 5-agent project health audit (architecture, security, tests, dependencies, performance)
- **`/rb:perf`** — Performance analysis with specialist agents
- **`/rb:boundaries`** — Analyze Rails service/context boundaries
- **`/rb:techdebt`** — Technical debt and refactoring opportunity detection
- **`/rb:pr-review`** — Address PR review comments systematically
- **`/rb:challenge`** — Rigorous review mode with adversarial questioning
- **`/rb:state-audit`** — Audit request state, CurrentAttributes, caching
- **`/rb:runtime`** — Runtime tooling integration (Tidewave, etc.)
- **`/rb:secrets`** — Scan for leaked secrets and API keys

#### Research & Knowledge Commands

- **`/rb:research`** — Research Ruby topics with parallel workers, prefers Tidewave when available
- **`/rb:document`** — Generate YARD/RDoc, README sections, ADRs
- **`/rb:learn`** — Capture lessons learned from fixes
- **`/rb:examples`** — Practical pattern walkthroughs and examples

#### 22 Specialist Agents

**Orchestrators (opus):**

- `workflow-orchestrator` — Full cycle coordination
- `planning-orchestrator` — Parallel research agent coordination
- `parallel-reviewer` — 4-agent parallel code review coordination

**Reviewers (sonnet):**

- `ruby-reviewer` — Ruby idioms, patterns, conventions
- `testing-reviewer` — RSpec, Minitest, factory patterns
- `security-analyzer` — OWASP vulnerability scanning
- `iron-law-judge` — Pattern-based Iron Law detection
- `data-integrity-reviewer` — Data consistency and constraint validation
- `migration-safety-reviewer` — Migration safety and rollback review

**Architecture (sonnet):**

- `rails-architect` — Service structure, Hotwire/Turbo patterns
- `active-record-schema-designer` — Migrations, data models, queries
- `rails-patterns-analyst` — Codebase pattern discovery

**Investigation (sonnet/haiku):**

- `deep-bug-investigator` — 4-track parallel bug investigation
- `call-tracer` — Call tree tracing
- `dependency-analyzer` — Module dependency and dead code analysis
- `verification-runner` — zeitwerk:check, format, test execution

**Domain Specialists (sonnet):**

- `sidekiq-specialist` — Job idempotency, error handling, queue config
- `ruby-runtime-advisor` — Performance, memory, concurrency
- `deployment-validator` — Docker, Kubernetes, Fly.io config
- `ruby-gem-researcher` — RubyGems library evaluation
- `web-researcher` — Ruby Weekly, docs, GitHub research

**Infrastructure (haiku):**

- `context-supervisor` — Multi-agent output compression and deduplication

#### 49 Skills

**Workflow Skills:** plan, work, review, compound, full, quick, brief, triage, verify

**Investigation Skills:** investigate, n1-check, constraint-debug, trace

**Analysis Skills:** audit, perf, boundaries, techdebt, pr-review, challenge, state-audit, runtime, secrets

**Knowledge Skills:** research, document, learn-from-fix, examples, compound-docs, intro, init, intent-detection

**Domain Pattern Skills:**

- `ruby-idioms` — Ruby language patterns and conventions
- `rails-contexts` — Rails controllers, routing, service objects
- `active-record-patterns` — Models, migrations, queries, validations
- `hotwire-patterns` — Turbo, Stimulus, streams, frames
- `hotwire-native` — Hotwire Native mobile patterns
- `sidekiq` — Background jobs, workers, queue configuration
- `grape-idioms` — Grape API framework patterns
- `sequel-patterns` — Sequel ORM patterns (alternative to Active Record)
- `dry-rb-patterns` — dry-rb ecosystem patterns
- `karafka` — Kafka integration with Karafka
- `async-patterns` — Async/await and concurrent Ruby patterns
- `safe-migrations` — Zero-downtime migration patterns
- `rails-idioms` — Rails-specific conventions
- `ruby-contexts` — Ruby service/context object patterns
- `runtime-integration` — Tidewave and runtime tooling integration
- `testing` — RSpec, Minitest, factory patterns
- `security` — Authentication, authorization, security best practices
- `deploy` — Deployment configurations

**Utility Skills:** rubydoc-fetcher

#### 21 registered hook command invocations

**PreToolUse:**

- `block-dangerous-ops.sh` — Blocks `rails db:drop/reset`, `git push --force`, `RAILS_ENV=production`

**PostToolUse (on Edit/Write):**

- `format-ruby.sh` — Runs `standardrb --fix` when configured, else `rubocop -a`
- `verify-ruby.sh` — Ruby syntax verification via `ruby -c`
- `iron-law-verifier.sh` — Programmatic Iron Law violation scanning
- `security-reminder.sh` — Security Iron Laws for auth files
- `log-progress.sh` — Async progress logging to `.claude/plans/{slug}/progress.md`
- `plan-stop-reminder.sh` — STOP reminder when plan.md is written
- `debug-statement-warning.sh` — Detects `puts`, `debugger`, `p` in production code
- `secret-scan.sh` — Scans for accidentally committed secrets

**PostToolUseFailure:**

- `ruby-failure-hints.sh` — Ruby-specific debugging hints for bundle/rails failures
- `error-critic.sh` — Detects repeated failures and escalates to structured analysis

**SubagentStart:**

- `inject-iron-laws.sh` — Injects all Iron Laws into spawned subagents

**SessionStart:**

- `setup-dirs.sh` — Creates `.claude/` directory structure
- `detect-runtime.sh` — Detects Ruby/Rails version, stack gems, Tidewave, and available tools
- `detect-betterleaks.sh` — Detects betterleaks executable availability
- `detect-rtk.sh` — Detects RTK executable availability
- `check-scratchpad.sh` — Checks for existing scratchpad decisions
- `check-resume.sh` — Detects resumable workflows
- `check-branch-freshness.sh` — Utility script (not currently wired in hooks.json) for branch freshness checks

**PreCompact:**

- `precompact-rules.sh` — Re-injects workflow rules before context compaction

**Stop:**

- `check-pending-plans.sh` — Warns if plans have unchecked tasks on session end

#### Key Features

**Context Supervisor Pattern** — When orchestrators spawn multiple agents,
the context-supervisor (haiku) compresses worker output before synthesis.
Prevents context exhaustion with 3 compression strategies
(index/compress/aggressive) based on output size.

**Auto-Loaded Skills** — Skills load automatically based on file context:

- `.rb` files → ruby-idioms
- `*_controller.rb` → rails-contexts
- `app/models/*.rb` → active-record-patterns
- `app/views/*.erb` → hotwire-patterns
- `*_spec.rb` → testing
- `app/jobs/*` → sidekiq

**Plan Namespaces** — Each plan owns all artifacts in `.claude/plans/{slug}/`:

- `plan.md` — The plan with checkboxes as state
- `research/` — Research agent output
- `reviews/` — Individual review agent findings
- `summaries/` — Compressed multi-agent output
- `progress.md` — Session progress log
- `scratchpad.md` — Decisions, dead-ends, handoffs

**Runtime Tooling Integration** — Tidewave Rails integration for runtime operations:

- `mcp__tidewave__get_docs` — Version-exact documentation
- `mcp__tidewave__project_eval` — Execute code in running app
- `mcp__tidewave__execute_sql_query` — Direct database queries
- `mcp__tidewave__get_logs` — Read application logs
- `mcp__tidewave__get_models` — List application modules
- `mcp__tidewave__get_source_location` — Find source locations

**Filesystem as State Machine** — Each workflow phase reads from the previous phase's output:

```
/rb:plan → /rb:work → /rb:verify → /rb:review → /rb:compound
```

**Skill Effectiveness Monitoring** — `/skill-monitor` command computes per-skill metrics
(action rate, friction, corrections) and identifies degrading skills for improvement.

#### Documentation

- Comprehensive README with architecture diagrams
- CLAUDE.md with development conventions and behavioral instructions
- Interactive tutorial (`/rb:intro`) with 6 sections
- 100+ reference documents across all skill domains
- Plugin development guide with size guidelines and checklists

[Unreleased]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.6...HEAD
[1.16.6]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.5...v1.16.6
[1.16.5]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.4...v1.16.5
[1.16.4]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.3...v1.16.4
[1.16.3]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.2...v1.16.3
[1.16.2]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.1...v1.16.2
[1.16.1]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.16.0...v1.16.1
[1.16.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.15.2...v1.16.0
[1.15.2]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.15.1...v1.15.2
[1.15.1]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.15.0...v1.15.1
[1.15.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.14.0...v1.15.0
[1.14.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.13.4...v1.14.0
[1.13.4]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.13.3...v1.13.4
[1.13.3]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.13.2...v1.13.3
[1.13.2]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.13.1...v1.13.2
[1.13.1]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.13.0...v1.13.1
[1.13.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.10...v1.13.0
[1.12.10]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.9...v1.12.10
[1.12.9]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.8...v1.12.9
[1.12.8]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.7...v1.12.8
[1.12.7]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.6...v1.12.7
[1.12.6]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.5...v1.12.6
[1.12.5]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.4...v1.12.5
[1.12.4]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.3...v1.12.4
[1.12.3]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.2...v1.12.3
[1.12.2]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.1...v1.12.2
[1.12.1]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.12.0...v1.12.1
[1.12.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.8...v1.12.0
[1.11.8]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.7...v1.11.8
[1.11.7]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.6...v1.11.7
[1.11.6]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.5...v1.11.6
[1.11.5]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.4...v1.11.5
[1.11.4]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.3...v1.11.4
[1.11.3]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.2...v1.11.3
[1.11.2]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.1...v1.11.2
[1.11.1]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.11.0...v1.11.1
[1.11.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/slbug/claude-ruby-grape-rails/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.9.0
[1.8.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.8.1
[1.8.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.8.0
[1.7.4]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.7.4
[1.7.3]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.7.3
[1.7.2]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.7.2
[1.7.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.7.1
[1.7.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.7.0
[1.6.3]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.6.3
[1.6.2]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.6.2
[1.6.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.6.1
[1.6.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.6.0
[1.5.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.5.0
[1.4.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.4.0
[1.3.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.3.1
[1.3.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.3.0
[1.2.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.2.0
[1.1.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.1.1
[1.1.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.1.0
[1.0.4]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.4
[1.0.3]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.3
[1.0.2]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.2
[1.0.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.1
[1.0.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.0
