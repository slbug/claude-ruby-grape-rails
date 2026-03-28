# Changelog

All notable changes to the Ruby/Rails/Grape Claude Code plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
