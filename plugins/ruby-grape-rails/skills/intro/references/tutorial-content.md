# Plugin Tutorial Content

Content for each section of the `/rb:intro` tutorial.
Present ONE section at a time with AskUserQuestion between sections.
IMPORTANT: Present ALL content in each section — every paragraph, table, and code block. Do NOT abbreviate or summarize.

## Contents

- [Section 1: Welcome](#section-1-welcome)
- [Section 2: Core Workflow Commands](#section-2-core-workflow-commands)
- [Section 3: Knowledge and Safety Net](#section-3-knowledge-and-safety-net)
- [Section 4: Hooks and Behavioral Rules](#section-4-hooks-and-behavioral-rules)
- [Section 5: Init, Review and Gaps](#section-5-init-review-and-gaps)
- [Section 6: Cheat Sheet and Next Steps](#section-6-cheat-sheet-and-next-steps)
- [Section 7: Claude Code Built-in Features](#section-7-claude-code-built-in-features)
- [Section 8: Keep CLAUDE.md Small](#section-8-keep-claudemd-small)

---

## Section 1: Welcome

### What This Plugin Does

This plugin adds **specialist Ruby/Rails/Grape agents**, **auto-loaded knowledge**, and **Iron Laws** to Claude Code. It turns a general-purpose AI into an opinionated Ruby pair programmer.

### The Core Concept

Everything revolves around an optional discovery step and a 5-phase workflow cycle:

```text
/rb:brainstorm (optional) → /rb:plan → /rb:work → /rb:verify → /rb:review → /rb:compound
                               |             |            |              |              |
                               v             v            v              v              v
                            Research &   Execute     Full check     Parallel       Capture what
                             plan tasks   tasks       verify/test    code review    you learned
```

Use `/rb:brainstorm` when requirements are vague or multiple approaches exist.
It gathers requirements interactively and produces an `interview.md` that
`/rb:plan` consumes. Skip it when requirements are already clear.

After `/rb:review`, follow this verdict-routing table to pick the next step:

| Verdict | Next step |
|---|---|
| `PASS` | `/rb:compound` to capture lessons. Optionally `/rb:triage {review-path}` to opt in to suggestions. |
| `PASS WITH WARNINGS` | `/rb:triage {review-path}` to batch warnings, or `/rb:compound` to capture lessons without fixing. |
| `BLOCKED` | `/rb:triage {review-path}` to select which findings to fix → `/rb:work` against the resulting plan. |
| `REQUIRES CHANGES` | `/rb:triage {review-path}` (default; auto-includes test-coverage gaps + handles any warnings). `/rb:plan {review-path}` for gaps-only plan, no triage UI. |

Each phase reads from the previous phase's output. Plans become checkboxes. Checkboxes track progress. Reviews catch mistakes. Compound knowledge makes future work faster.

### What You Get

| Feature | What It Does |
|---------|-------------|
| 19 specialist agents | ActiveRecord, Hotwire, security, Sidekiq, deployment, provenance experts |
| 52 skills | Commands for every phase of development |
| 22 Iron Laws | Non-negotiable rules enforced automatically |
| Auto-loaded references | Context-aware docs loaded when you edit relevant files |
| Runtime tooling integration | Runtime debugging when runtime tooling is connected |

---

## Section 2: Core Workflow Commands

### The Full Cycle

For features that need planning and review:

```bash
# 0. Brainstorm (optional) — gather requirements when idea is vague
/rb:brainstorm Add user avatars with S3 upload

# 1. Plan — spawns research agents, outputs checkbox plan
/rb:plan Add user avatars with S3 upload

# 1b. Brief (optional) — understand the plan before starting
/rb:brief .claude/plans/user-avatars/plan.md

# 2. Work — executes plan, checks off tasks, verification at checkpoints
/rb:work .claude/plans/user-avatars/plan.md

# 3. Review — parallel agents check Ruby idioms, security, tests
/rb:review

# 4. Compound — capture what you learned for future reference
/rb:compound Fixed S3 upload timeout with multipart streaming
```

### Shortcuts

Not everything needs the full cycle:

| Command | When to Use | Time |
|---------|------------|------|
| `/rb:quick` | Bug fixes, small features (<100 lines) | ~2 min |
| `/rb:full` | New features, autonomous plan→work→verify→review→compound | ~10 min |
| `/rb:investigate` | Debugging — checks obvious things first | ~3 min |

### Decision Guide

```text
Is it a bug?
  Yes --> /rb:investigate
  No  --> Is it < 100 lines?
            Yes --> /rb:quick
            No  --> Are requirements vague?
                      Yes --> /rb:brainstorm then /rb:plan
                      No  --> Do you want full autonomy?
                                Yes --> /rb:full
                                No  --> /rb:plan then /rb:work
```

### Deepening an Existing Plan

Already have a plan but want to add research or refine tasks?

```bash
/rb:plan --existing .claude/plans/user-avatars/plan.md
```

This spawns specialist agents to analyze your existing plan and enhance it with research findings.

---

## Section 3: Knowledge and Safety Net

### Context-Aware Knowledge

The plugin includes targeted references and guidance for common editing contexts:

| You're editing... | Plugin loads... |
|-------------------|----------------|
| `app/views/*.html.erb` | Hotwire/Turbo patterns, async/streams, components |
| `*_spec.rb`, `*_test.rb` | RSpec/Minitest patterns, factories |
| `db/migrate/*` | Migration patterns, safe operations |
| `*auth*`, `*session*` | Security patterns, authorization rules |
| `config/routes.rb` | Routing patterns, controllers, scopes |
| `*_job.rb`, `app/jobs/*` | Sidekiq patterns, idempotency rules |

These are the references Claude should use for those file types.
File-pattern loading is behavioral guidance plus skill `paths:`
auto-loading; the strongest signal still comes from invoking the
matching workflow command directly.

<!-- IRON_LAWS_START -->

<!-- GENERATED FROM iron-laws.yml — DO NOT EDIT -->

### Iron Laws (22 Rules, Always Enforced)

Iron Laws are non-negotiable rules that every agent enforces. If your code violates one, the plugin stops and explains before proceeding.

**Key Laws:**

| Law | Why |
|-----|-----|
| Decimal for Money | Floating point arithmetic causes rounding errors that compound in financial calculations |
| Parameterized Queries | String interpolation in SQL creates injection vulnerabilities |
| Eager Loading | N+1 queries kill performance at scale |
| Commit-Safe Enqueueing in Active Record | Jobs may run before transaction commits, reading uncommitted or stale data |
| Transaction Boundaries | Partial failures leave data in inconsistent states |
| No Validation Bypass | Skipping validations bypasses business rules and can corrupt data |
| No default_scope | default_scope creates invisible query conditions that surprise developers |

<!-- IRON_LAWS_END -->

### Analysis & Verification Commands

| Command | What It Does |
|---------|-------------|
| `/rb:verify` | Prefer project-native verify wrappers when present; otherwise run full direct verification (format, tests, and Rails-specific checks when applicable) |
| `/rb:permissions` | Analyze permission prompts and suggest safe settings entries |
| `/rb:audit` | 5-agent project health audit with scores |
| `/rb:n1-check` | Detect N+1 query patterns |
| `/rb:state-audit` | Audit Hotwire/Turbo stream state for memory |
| `/rb:boundaries` | Check Rails context boundary violations |
| `/rb:perf` | Performance analysis (Active Record, Hotwire/Turbo) |

### runtime tooling Integration

When runtime tooling is connected to your running Rails app:

| Goal | Tool call |
|---|---|
| Get docs for your exact dependency versions | `mcp__tidewave__get_docs "ActiveRecord::QueryMethods"` |
| Execute code in your running app | `mcp__tidewave__project_eval "User.count"` |
| Query your dev database directly | `mcp__tidewave__execute_sql_query "SELECT count(*) FROM users"` |

The plugin automatically prefers runtime tooling tools over alternatives when available.

---

## Section 4: Hooks and Behavioral Rules

The plugin uses **layered enforcement** — some things run automatically, some depend on Claude following instructions, some are on-demand. Here's what actually happens:

### Layer 1: Hooks (Automatic and Hook-Driven)

[Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) run shell scripts automatically after tool use. These are real automation — no instructions needed:

| Hook | Trigger | What It Does |
|------|---------|-------------|
| Dangerous ops block | Before Bash command | Blocks destructive DB commands like `rails db:drop`, `bin/rails db:reset`, `bundle exec rails db:purge`, `rake db:drop`, `bin/rake db:reset`, and `bundle exec rake db:purge`, plus equivalent `bundle exec bin/...` and env-prefixed forms; also blocks `git push --force`, Redis flushes (`FLUSHDB` / `FLUSHALL` via `redis-cli`), and `RAILS_ENV=prod` |
| Format check | Every `.rb` edit | Auto-fixes with StandardRB (if configured) or RuboCop |
| Iron Law verifier | Every `.rb` edit | Scans code content for Iron Law violations with line numbers |
| Debug stmt warning | Ruby-ish app file edits | Warns about `puts`/`debugger`/`p` in production code, excluding `spec/`, `test/`, and repo script directories |
| Security reminder | Editing auth/session/password files | Outputs relevant Iron Laws via stderr + exit 2 |
| Progress logging | Every file edit | Appends to `.claude/plans/{slug}/progress.md` (async) |
| Failure hints | Bash command fails | Injects debugging hints via `additionalContext` |
| Error critic | Repeated test failures | Escalates to structured critic analysis after 3+ failures |
| Iron Laws + Preferences injection | `SessionStart` (main session) + `SubagentStart` (any subagent spawn) | Injects 22 Iron Laws + 6 Advisory Preferences via `additionalContext`. Rules with `reference_files` declared in `iron-laws.yml` / `preferences.yml` get a bare companion path on the line beneath the rule; rules without `reference_files` emit no path. |
| PreCompact rules | Before context compaction | Warns about the active workflow phase and what to re-read after compaction |

Format check **auto-fixes** — runs `standardrb --fix` when StandardRB is configured, otherwise `rubocop -a`.

The PreCompact hook detects active workflow phases (`/rb:plan`, `/rb:work`, `/rb:full`) and emits a user-facing reminder
before compaction so the next turn re-reads the right plan artifacts. PostCompact then reinforces those re-read steps after
context is compressed.

Note: `verify-ruby.sh` runs `ruby -c` syntax checks on Ruby files. Verification commands
(`/rb:verify`, `/rb:full`) run full checks including format, tests, and Rails-specific validations
(zeitwerk:check for Rails apps).

### Layer 2: Iron Laws in Skills (Behavioral)

Each domain skill (active-record-patterns, hotwire-patterns, security, etc.) embeds its own Iron Laws.
When Claude loads a skill, the laws become active context.
Claude is instructed to **stop and explain** before writing code that violates them.

This is behavioral — it works because the rules are in Claude's context, not because code enforces them. It's effective but not 100% guaranteed.

### Layer 3: Skill Loading by File Type (Behavioral)

Two activation paths exist for domain skills:

| Path | Trigger |
|---|---|
| CC auto-activation | Skill declares `paths:` in its frontmatter; CC loads the skill when files matching the glob are open or being edited. ~16 shipped skills declare `paths:` (hotwire-patterns, active-record-patterns, testing, sidekiq, security, karafka, grape-idioms, ar-n1-check, deploy, hotwire-native, async-patterns, sequel-patterns, safe-migrations, rails-idioms, ruby-idioms, active-record-constraint-debug). Read each skill's frontmatter for the exact glob set. |
| Description-based | Skill omits `paths:`; CC matches on description text (less reliable). Examples: `rails-contexts`, `ruby-contexts`. |

Invoke `/rb:<workflow>` directly when the file you are editing is
not covered by any skill's `paths:` glob.

---

## Section 5: Init, Review and Gaps

### Layer 4: `/rb:init` (Project Stack Notes)

Run `/rb:init` to write a managed block into the project
`CLAUDE.md`. Block contents: stack-version header + project-specific
stack facts only.

| Source | Examples |
|---|---|
| `detect-stack` output | Ruby/Rails/Grape/Sidekiq/Karafka versions, `DETECTED_ORMS`, `PACKAGE_LAYOUT`, `PACKAGE_LOCATIONS`, `HAS_PACKWERK` |
| Scoped repo file scans | queue list (`config/sidekiq.yml`), Hotwire channels (`app/channels/*`), Karafka topic routes (`karafka.rb`), Packwerk enforcement flags (`packwerk.yml` + per-package `package.yml`) |
| Targeted interview | per-package ORM map for mixed AR+Sequel repos (NOT in `detect-stack`), retry policy, frame-id convention, secret-path scan policy |

`/rb:init` does NOT inject:

| Surface | Where it lives instead |
|---|---|
| Iron Laws + Advisory Preferences | `inject-rules.sh` hook on every `SessionStart` + `SubagentStart` |
| Skill workflow doctrine (complexity scoring, spawn rules, verification commands) | individual skill bodies (`/rb:plan`, `/rb:review`, `/rb:verify`) — load when skill invoked |
| Library defaults (Sidekiq base class, Turbo Frame patterns) | framework docs, NOT project `CLAUDE.md` |

```bash
/rb:init           # First-time setup
/rb:init --update  # Update managed block after plugin updates
```

`--update` replaces the content between
`<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->` and
`<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->` markers, so legacy
doctrine-heavy blocks from earlier plugin versions are migrated to
the slim form automatically.

### Layer 5: `/rb:review` + Iron Law Judge (On-Demand)

The `iron-law-judge` agent does **pattern-based violation
detection** — it scans your changed files for known anti-patterns.
Runs only when you invoke `/rb:review`.

What it catches with automated detection (regex patterns from
`agents/iron-law-judge.md`):

- `t.float :price` / `t.float :amount` in migrations (Law 1)
- SQL string interpolation: `where("id = #{id}")` (Laws 2/15)
- `.html_safe` / `raw(...)` on untrusted content (Law 14)
- `update_columns` / `save(validate: false)` in normal flows (Law 6)
- `default_scope` in models (Law 7)
- `perform_later(current_user)` — ORM objects in job args (Law 10)
- `after_save :enqueue_*` (should be `after_commit`) (Laws 4/11)
- `eval(...)` (Law 12)
- `def method_missing` without `respond_to_missing?` (Law 16)
- bare `rescue` / `rescue Exception` (Law 18)

### Layer 6: Planning Sets Structure Early

The `/rb:plan` phase sets naming conventions, context boundaries, and model structure
**before any code exists**. This is where you prevent Rails-y patterns at the architecture
level — fat controllers, service objects, and ActiveRecord patterns get caught in the plan,
not in code review.

### What's NOT Automated (Yet)

Being honest about the gaps:

| Check | Status | Why |
|-------|--------|-----|
| Ruby syntax check | PostToolUse Edit/Write via `rubyish-post-edit.sh` | `verify-ruby.sh` runs `ruby -c` on Ruby files |
| Format check (StandardRB/RuboCop) | PostToolUse Edit/Write via `rubyish-post-edit.sh` | Auto-fixes with StandardRB when configured, else RuboCop |
| Full verification | `/rb:verify`, `/rb:full` VERIFYING phase | Includes format, tests, and Rails-specific checks (zeitwerk:check for Rails) |
| `bundle exec rspec` | `/rb:full` VERIFYING phase + on-demand (`/rb:verify`) | Not run per-task, only between phases |
| Type checking (Steep/Sorbet) | On-demand (`/rb:verify`) | Takes minutes, not seconds |
| Iron Law detection during coding | Behavioral only | `iron-law-judge` is review-time only |

### The Honest Summary

```text
AUTOMATIC (hooks):     Format check, security reminders, progress logging, failure hints,
                       Iron Laws + Preferences injected at SessionStart + SubagentStart,
                       PreCompact rule preservation
BEHAVIORAL (Claude):   Iron Laws, skill loading, stop-and-explain
ON-DEMAND (commands):  /rb:review (iron-law-judge), /rb:verify (format/tests/zeitwerk for Rails)
PROJECT CONTEXT:       /rb:init (writes detected project-stack facts into CLAUDE.md)
```

Hooks deliver the rules. `/rb:review` catches what behavioral layer
missed. `/rb:init` records project-stack facts so Claude has the
right baseline context (queue list, ORM-per-package map, package
boundaries) without restating any rule already injected at runtime.

---

## Section 6: Cheat Sheet and Next Steps

### Command Reference

**Workflow (use in order):**

| Command | Phase |
|---------|-------|
| `/rb:brainstorm <topic>` | Gather requirements (optional, before plan) |
| `/rb:plan <feature>` | Plan with research agents |
| `/rb:plan --existing <file>` | Enhance existing plan |
| `/rb:brief [plan file]` | Interactive plan walkthrough |
| `/rb:work <plan file>` | Execute plan with verification |
| `/rb:review` | Parallel agent code review |
| `/rb:triage` | Interactive review finding triage |
| `/rb:compound` | Capture solved problem |

**Standalone:**

| Command | Purpose |
|---------|---------|
| `/rb:quick <task>` | Fast implementation, skip ceremony |
| `/rb:full <feature>` | Autonomous plan→work→verify→review→compound cycle |
| `/rb:investigate <bug>` | Structured bug investigation |
| `/rb:verify` | Run all quality checks |
| `/rb:permissions` | Tune Claude Bash permissions from real session evidence |
| `/rb:research <topic>` | Research with parallel workers, runtime tooling-first |
| `/rb:pr-review <PR#>` | Address PR review comments |
| `/rb:init` | Write project stack notes to CLAUDE.md (rules runtime-injected) |
| `/rb:runtime` | Runtime tooling (Tidewave integration) |
| `/rb:secrets` | Scan for leaked credentials |
| `/rb:document` | Generate YARD/RDoc, README, ADRs |
| `/rb:compression-report` | Anonymize and draft a verify-output compression telemetry report (opt-in via `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1`) |
| `/rb:provenance-scan` | Audit `.claude/` provenance sidecars and write a dated trust-state report |

**Analysis:**

| Command | Purpose |
|---------|---------|
| `/rb:audit` | Full project health audit |
| `/rb:perf` | Performance analysis |
| `/rb:n1-check` | N+1 query detection |
| `/rb:state-audit` | Hotwire/Turbo memory audit |
| `/rb:boundaries` | Context boundary check |
| `/rb:techdebt` | Technical debt analysis |
| `/rb:constraint-debug` | ActiveRecord constraint violations |
| `/rb:trace` | Build call trees to trace method flow |

**Knowledge:**

| Command | Purpose |
|---------|---------|
| `/rb:examples` | Practical walkthroughs |
| `/rb:learn` | Capture a lesson from a fix |
| `/rb:challenge` | Rigorous review mode |

### 3 Tips for Getting the Most Out of the Plugin

1. **Start with `/rb:plan` for any feature that touches multiple files.** The research agents catch architectural issues early, before you've written code that needs rewriting.

2. **Let Iron Laws stop you.** When the plugin flags a violation, read the explanation.
These rules exist because the Ruby community learned them the hard way
(string keys in JSON causing injection, N+1 queries at scale, memory bloat with Hotwire).

3. **Use `/rb:compound` after solving hard bugs.** The solution gets indexed and searchable. Next time you hit something similar, the plugin finds your past solution automatically.

### Next Steps

- Try `/rb:plan` with your next feature to see the full workflow
- Run `/rb:verify` to see your project's current health
- Run `/rb:audit` for a comprehensive project assessment
- Check `/rb:examples` for detailed walkthroughs

## Section 7: Claude Code Built-in Features

These are Claude Code native, not plugin. They complement the plugin.

- **`xhigh` effort** (Opus 4.7 default, CC 2.1.111) — between `high` and `max`; recommended default. Plugin's plan/audit/review/full skills use `effort: xhigh`.
- **Auto mode** (CC 2.1.111) — no longer requires `--enable-auto-mode` flag. Used for subagent spawning.
- **`/focus` command** (CC 2.1.110) — fullscreen TUI mode; keeps plugin SessionStart status-line output visible.
- **`/recap` command** (CC 2.1.108) — summary when resuming a session. Useful between `/rb:plan` → `/rb:work` sessions across days.
- **`/less-permission-prompts`** (CC 2.1.111) — interactive slider; the plugin's `/rb:permissions` skill produces analysis that feeds into this.
- **`/output-styles`** — choose communication mode:
  - `Default` — plugin's normal behavior
  - `Explanatory` — Claude narrates thought process; good for learning
  - `Learning` — interactive pair-programming; Claude stops for user to write `#TODO` sections
  - Recommend `Explanatory` or `Learning` when comprehension matters
    more than speed. Anthropic skill-formation RCT (n=52, Trio):
    conceptual-inquiry users score 65-86% mastery vs delegation <40%;
    agent-mode users still benefit from comprehension framing.
- **`skillListingBudgetFraction`** — caps combined `description` +
  `when_to_use` per skill in the listing block. Default 1% of context
  window (or 8K fallback). Plugin targets 1M context, so default fits
  shipped skills. 200K-context users should raise per the `/rb:init`
  skill's "Skill Listing Budget" advisory.

Each is a CC-native feature — the plugin does not reimplement any of them.

## Section 8: Keep CLAUDE.md Small

CLAUDE.md loads every session and counts against the context budget.
Anthropic recommends keeping it **under 200 lines**. Heavy repo-level
context files inflate per-call inference cost and crowd out task-specific
context, which can reduce task success on long-running sessions.

**Rule of thumb:** "Would removing this line cause Claude to make mistakes?"
If no, cut it.

**Belongs in root `CLAUDE.md`:**

- Exact verify commands for this repo
- How to run tests
- Dangerous commands to avoid
- Package boundaries
- Required tooling wrappers
- Short list of non-obvious local facts

**Does NOT belong (put in skills / scoped rules):**

- Long generic Ruby advice
- Repeated best practices already encoded in skills
- Verbose workflow philosophy
- Big example blocks

**Scoped rule files:** drop subtree-specific rules into `.claude/rules/*.md` with `paths:` frontmatter. They auto-load only when editing matching files.

Example `.claude/rules/migrations.md`:

```yaml
---
name: migrations
description: Safe migration rules
paths:
  - "db/migrate/**/*.rb"
  - "db/schema.rb"
---
```

This loads only when editing migrations — no permanent tax on context.
