# Changelog

All notable changes to the Ruby/Rails/Grape Claude Code plugin.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-03-23

### Changed

- Merged `detect-runtime.sh`, `detect-betterleaks.sh`, and `detect-rtk.sh` into one SessionStart detector that exports runtime, tool, and hook-mode state
- Added hook modes: `default` for quieter startup / targeted secret scanning, `strict` for broader secret checks
- Switched marketplace plugin source to `git-subdir` so URL-based marketplace distribution can target `plugins/ruby-grape-rails/`

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

[1.0.3]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.3
[1.0.2]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.2
[1.0.1]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.1
[1.0.0]: https://github.com/slbug/claude-ruby-grape-rails/releases/tag/v1.0.0
