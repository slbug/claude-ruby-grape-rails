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

Each phase reads from the previous phase's output. Plans become checkboxes. Checkboxes track progress. Reviews catch mistakes. Compound knowledge makes future work faster.

### What You Get

| Feature | What It Does |
|---------|-------------|
| 19 specialist agents | ActiveRecord, Hotwire, security, Sidekiq, deployment, provenance experts |
| 53 skills | Commands for every phase of development |
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

These are the references Claude should use for those file types. In
practice this is strongest after `/rb:init` and when you invoke the
matching workflow command; most file-pattern loading is behavioral
guidance, not a hook-backed auto-loader.

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
| `/rb:permissions` | Analyze recent permission prompts and suggest safer Claude settings entries |
| `/rb:audit` | 5-agent project health audit with scores |
| `/rb:n1-check` | Detect N+1 query patterns |
| `/rb:state-audit` | Audit Hotwire/Turbo stream state for memory |
| `/rb:boundaries` | Check Rails context boundary violations |
| `/rb:perf` | Performance analysis (Active Record, Hotwire/Turbo) |

### runtime tooling Integration

When runtime tooling is connected to your running Rails app:

```bash
# Get docs for your exact dependency versions
mcp__tidewave__get_docs "ActiveRecord::QueryMethods"

# Execute code in your running app
mcp__tidewave__project_eval "User.count"

# Query your dev database directly
mcp__tidewave__execute_sql_query "SELECT count(*) FROM users"
```

The plugin automatically prefers runtime tooling tools over alternatives when available.

---

## Section 4: Hooks and Behavioral Rules

The plugin uses **layered enforcement** — some things run automatically, some depend on Claude following instructions, some are on-demand. Here's what actually happens:

### Layer 1: Hooks (Automatic and Hook-Driven)

[Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) run shell scripts automatically after tool use. These are real automation — no instructions needed:

| Hook | Trigger | What It Does |
|------|---------|-------------|
| Dangerous ops block | Before Bash command | Blocks destructive DB commands like `rails db:drop`, `bin/rails db:reset`, `bundle exec rails db:purge`, `rake db:drop`, `bin/rake db:reset`, and `bundle exec rake db:purge`, plus equivalent `bundle exec bin/...` and env-prefixed forms; also blocks `git push --force` and `RAILS_ENV=prod` |
| Format check | Every `.rb` edit | Auto-fixes with StandardRB (if configured) or RuboCop |
| Iron Law verifier | Every `.rb` edit | Scans code content for Iron Law violations with line numbers |
| Debug stmt warning | Ruby-ish app file edits | Warns about `puts`/`debugger`/`p` in production code, excluding `spec/`, `test/`, and repo script directories |
| Security reminder | Editing auth/session/password files | Outputs relevant Iron Laws via stderr + exit 2 |
| Progress logging | Every file edit | Appends to `.claude/plans/{slug}/progress.md` (async) |
| Failure hints | Bash command fails | Injects debugging hints via `additionalContext` |
| Error critic | Repeated test failures | Escalates to structured critic analysis after 3+ failures |
| Iron Laws injection | Any subagent spawns | Injects all 22 Iron Laws into subagents via `additionalContext` |
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

CLAUDE.md instructs Claude to load specific skills based on file patterns:

```text
app/views/*.erb         → hotwire-patterns (streams, frames, Turbo)
app/models/*.rb         → active-record-patterns (queries, associations)
app/controllers/*.rb    → rails-contexts (controllers, requests)
*_spec.rb               → testing (RSpec, Minitest, factories)
*_test.rb                → testing (Minitest)
*_worker.rb             → sidekiq (jobs, idempotency, queue config)
Any .rb file            → ruby-idioms (always)
```

This is **not plugin infrastructure** — it's instructions that Claude follows. No hooks trigger skill loading.
This is the plugin's biggest known gap — in practice, skills rarely auto-load from file context alone.
Running `/rb:init` significantly improves this.

---

## Section 5: Init, Review and Gaps

### Layer 4: `/rb:init` (Strengthens Everything)

Running `/rb:init` injects enforcement rules **directly into your project's CLAUDE.md**. This is stronger than plugin-level instructions because CLAUDE.md is always read at session start.

What it adds:

- **7-step mandatory procedure** — complexity scoring, interview questions before coding, reference loading
- **Iron Laws with STOP protocol** — explicitly tells Claude to halt on violations
- **Verification rules** — Format checks (StandardRB or RuboCop) run automatically; full verification (`/rb:verify`) includes format, tests, and Rails-specific checks (zeitwerk:check when applicable)
- **Stack-specific rules** — detects Rails version, Sidekiq, Grape from `Gemfile`

```bash
/rb:init           # First-time setup
/rb:init --update  # Update after plugin updates
```

If you're finding the plugin inconsistent, running `/rb:init` is the single biggest improvement you can make.

### Layer 5: `/rb:review` + Iron Law Judge (On-Demand)

The `iron-law-judge` agent does **pattern-based violation detection** — it uses Grep to search your changed files for known anti-patterns. But it only runs when you invoke `/rb:review`.

What it catches with automated detection:

- `constantize` in lib code
- `t.float :price` in migrations
- `raw(@variable)` (XSS risk)
- Database queries in Hotwire controller without proper guards
- Missing `lock` in ActiveRecord query fragments

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
                       Iron Laws in subagents, PreCompact rule preservation
BEHAVIORAL (Claude):   Iron Laws, skill loading, stop-and-explain
ON-DEMAND (commands):  /rb:review (iron-law-judge), /rb:verify (format/tests/zeitwerk for Rails)
STRENGTHENED BY:       /rb:init (injects rules into project CLAUDE.md)
```

The plugin works best when all layers are active: `/rb:init` for persistent rules, hooks for automatic checks, and `/rb:review` to catch what the behavioral layer missed.

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
| `/rb:init` | Initialize plugin in a project |
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
  - Recommend `Explanatory` or `Learning` when comprehension matters more than speed (Anthropic skill-formation study: conceptual-inquiry patterns score 86% mastery vs delegation <40%).

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
