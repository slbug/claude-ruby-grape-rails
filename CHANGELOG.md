# Changelog

All notable changes to the Ruby/Rails/Grape Claude Code plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  `pytest.ini`, explicit `pytest` test commands, and a default eval-test
  wrapper that prefers `pytest` when installed while keeping the existing
  `unittest` path working.
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
  `skills/permissions/scripts/extract_permissions.rb`.

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

- `inject-iron-laws.sh` — Injects all 21 Iron Laws into spawned subagents

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

[1.0.4]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.4
[1.0.3]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.3
[1.0.2]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.2
[1.0.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.1
[1.0.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.0
