# Ruby/Rails/Grape Plugin for Claude Code

**Claude Code is great. But it doesn't know that `default_scope` will bite you later, that `t.float` will corrupt your money fields, or that your Sidekiq job isn't idempotent.**

This plugin does. It coordinates **23 specialist agents** and **51 skills** that plan, implement,
review, and verify your Ruby/Rails/Grape code in parallel -- each with domain
expertise, fresh context, and enforced [Iron Laws](#iron-laws-non-negotiable-rules)
that catch the bugs your tests won't. It is now stack-aware enough to handle
mixed Active Record + Sequel repos and Packwerk-style modular monoliths
without flattening everything into generic Rails advice.

The plugin also keeps the runtime path leaner than older builds: read-only
agents skip contributor-only `CLAUDE.md` context via `omitClaudeMd`, session
start writes a fast runtime snapshot before a quiet async refresh, and active
plans keep structured scratchpads for dead ends, decisions, and handoffs.

```bash
# You describe the feature. The plugin figures out the rest.
/rb:plan Add real-time comment notifications

# 4 research agents analyze your codebase in parallel.
# A structured plan lands in .claude/plans/comment-notifications/plan.md
# Then:

/rb:work .claude/plans/comment-notifications/plan.md
# Implements task by task. Verification checkpoints at key milestones.
# Stops on programmatic Iron Law violations and pushes the rest into review-time checks.

/rb:review
# 4 specialist agents audit in parallel:
# idioms, security, tests, verification.
# Deduplicates findings. Flags pre-existing issues separately.
```

No prompt engineering. No "please check for N+1 queries." The plugin auto-loads
the right domain knowledge based on what files you're editing and enforces rules
that prevent the mistakes Ruby developers actually make in production.

Hook prerequisites: core hook guardrails expect `bash`, `jq`, `grep`, and
standard Unix utilities available on macOS/Linux/WSL such as `head`,
`readlink`, `awk`, `cksum`, `mktemp`, `sed`, `find`, `cp`, `mv`, `rm`, `tr`,
`wc`, `cat`, and `mkdir`. If a required dependency is missing, the plugin now
surfaces an explicit hook error or warning instead of silently disabling those
checks.

```
┌─────────────────────────────────────────────────────────────────────┐
│  💎 Ruby/Rails/Grape Plugin for Claude Code                         │
│                                                                     │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐           │
│  │    23    │    51    │   100+   │    11    │    21    │           │
│  │  Agents  │  Skills  │   Refs   │  Events  │Iron Laws │           │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘           │
│                                                                     │
│  AGENTS                          COMMANDS                           │
│  ─────────────────────           ──────────────────────────         │
│  Orchestrators (opus)            Workflow                           │
│    workflow-orchestrator           /rb:plan    /rb:work             │
│    planning-orchestrator           /rb:review  /rb:full             │
│    parallel-reviewer               /rb:compound /rb:quick           │
│    context-supervisor              /rb:brief   /rb:triage           │
│                                                                     │
│  Reviewers (sonnet)              Investigation & Debug              │
│    ruby-reviewer                   /rb:investigate /rb:trace        │
│    testing-reviewer                /rb:n1-check   /rb:perf          │
│    security-analyzer               /rb:constraint-debug             │
│    iron-law-judge                  /rb:state-audit                  │
│                                                                     │
│  Architecture (sonnet)           Analysis & Review                  │
│    rails-architect                 /rb:audit    /rb:verify          │
│    active-record-schema-designer   /rb:techdebt /rb:boundaries      │
│    rails-patterns-analyst          /rb:pr-review /rb:challenge      │
│    ruby-runtime-advisor            /rb:research  /rb:document       │
│                                                                     │
│  Investigation (sonnet/haiku)    Knowledge (auto-loaded)            │
│    deep-bug-investigator           hotwire-patterns                 │
│                                    active-record-patterns           │
│    call-tracer                     ruby-idioms      security        │
│    dependency-analyzer             rails-contexts   sidekiq         │
│    verification-runner             testing   deploy   runtime       │
│                                                                     │
│  Domain (sonnet)                 Hooks                              │
│    sidekiq-specialist              auto-format · ruby-syntax-check  │
│    deployment-validator            iron-law-verify · security-scan  │
│    ruby-gem-researcher             debug-stmt-detect · error-critic │
│    web-researcher                  progress-tracking · db/prod/git guard │
│                                                                     │
│  ───────────────────────────────────────────────────────────        │
│  21 Iron Laws · Runtime Tooling · plan→work→verify→review→compound  │
│  github.com/slbug/claude-ruby-grape-rails                           │
└─────────────────────────────────────────────────────────────────────┘
```

Ruby-ish Edit/Write automation is delegated through
[rubyish-post-edit.sh](plugins/ruby-grape-rails/hooks/scripts/rubyish-post-edit.sh),
which fans out to Iron Law verification, formatting, syntax, and debug checks
for `*.rb`, `*.rake`, `Gemfile`, `Rakefile`, and `config.ru`. Generic safety
hooks stay separate: the security reminder is now advisory, secret scanning
still watches all edits/writes and blocks when coverage cannot be trusted,
progress logging runs async, and the plan STOP reminder fires only on
`Write(*plan.md)`. `block-dangerous-ops.sh` currently blocks four
command families: destructive Rails/Rake DB tasks, Redis flushes, git force
pushes, and production-environment commands.
Default secret scanning is targeted per edit or inline payload and now fails
closed when the workspace root or scanner cannot be trusted. Strict mode
broadens that to recent-change sweeps and also fails closed when that broader
coverage cannot be trusted.
[hooks.json](plugins/ruby-grape-rails/hooks/hooks.json)
is the current wiring source of truth.

## Installation

### From GitHub (recommended)

```bash
# In Claude Code, add the marketplace
/plugin marketplace add slbug/claude-ruby-grape-rails

# Install the plugin
/plugin install ruby-grape-rails
```

### From Local Path (for development)

```bash
git clone https://github.com/slbug/claude-ruby-grape-rails.git
cd claude-ruby-grape-rails

# Run these commands from the cloned repo root.

# Option A: Test local working-tree changes directly
claude --plugin-dir ./plugins/ruby-grape-rails

# Option B: Validate marketplace install flow
# Note: marketplace.json now uses git-subdir source, so this installs the
# published GitHub-backed plugin source, not your uncommitted working tree.
/plugin marketplace add .
/plugin install ruby-grape-rails
```

### Known Limitations

**Supported Environments**: This plugin is validated on macOS, Linux, and WSL.
Native Windows is not currently supported.

**Marketplace Install & Agent Permissions**: Marketplace-installed plugin agents
follow your session permission policy. If you want specialist agents to run Ruby
verification commands without repeated prompts, add explicit `permissions.allow`
rules for the tools they need.

**Workarounds:**

1. Add explicit rules to your project's `.claude/settings.json`:

   ```json
   {
     "permissions": {
       "defaultMode": "acceptEdits",
       "allow": [
          "Bash(bundle *)",
          "Bash(rails *)",
          "Bash(rake *)",
          "Grep(*)",
          "Read(*)",
          "Glob(*)"
       ]
     }
   }
   ```

2. Run `/rb:permissions` to scan recent prompts and propose safer
   `settings.json` allowlists instead of growing them blindly
3. Use `--plugin-dir` for local development while iterating on the plugin itself

## Getting Started

New to the plugin? Run the interactive tutorial:

```bash
/rb:intro
```

It walks through the workflow, commands, and features in 6 short sections (~5 min).
Skip to any section with `/rb:intro --section N`.

## Quick Examples

```bash
# Just describe what you need — the plugin detects complexity and suggests the right approach
> Fix the N+1 query in the user dashboard

# Plan a feature with parallel research agents, then execute
/rb:plan Add email notifications for new comments
/rb:work .claude/plans/email-notifications/plan.md

# Full autonomous mode — plan, implement, review, capture learnings
/rb:full Add user profile avatars with S3 upload

# 4-agent parallel code review (idioms, security, tests, verification)
/rb:review

# Quick implementation — skip ceremony, just code
/rb:quick Add pagination to the users list

# Structured bug investigation with 4 parallel tracks
/rb:investigate Timeout errors in the checkout flow

# Project health audit across 5 categories
/rb:audit
```

The plugin auto-loads domain knowledge based on what files you're editing
(Rails patterns for `*_controller.rb`, Active Record patterns for models, security rules for auth code)
and enforces [Iron Laws](#iron-laws-non-negotiable-rules) that prevent common Ruby/Rails mistakes.

## How It Works

### The Lifecycle

The plugin supports an optional **Brainstorm** discovery step before the core **Plan → Work → Verify → Review → Compound** lifecycle. Each phase produces artifacts in a namespaced directory:

```
/rb:brainstorm (optional) → /rb:plan → /rb:work → /rb:verify → /rb:review → /rb:compound
                                │           │            │              │              │
                                ↓           ↓            ↓              ↓              ↓
                   .claude/plans/{slug}/  (namespace)  (namespace)  (namespace)  .claude/solutions/
```

- **Plan** -- Research agents analyze your codebase in parallel, then synthesize a structured implementation plan
- **Work** -- Execute the plan task-by-task with quick verification checks after each change
- **Verify** -- Prefer the repo's native verify wrapper when present; otherwise run the full direct verification loop before review
- **Review** -- Four specialist agents audit your code in parallel (idioms, security, tests, static analysis)
- **Compound** -- Capture what you learned as reusable knowledge for future sessions

### Key Concepts

- **Filesystem is the state machine.** Each phase reads from the previous phase's output. No hidden state.
- **Plan namespaces.** Each plan owns its implementation-state artifacts in `.claude/plans/{slug}/` -- plan, research, summaries, progress, scratchpad.
- **Scratchpads are durable workflow memory.** Dead ends, decisions, and
  handoffs survive long sessions and compaction instead of living only in chat.
- **Reviews are standalone artifacts.** Reviewer outputs live under `.claude/reviews/`, not inside plan namespaces.
- **Plan checkboxes track progress.** `[x]` = done, `[ ]` = pending. `/rb:work` finds the first unchecked task and continues.
- **One plan = one work unit.** Large features get split into multiple plans. Each is self-contained.
- **Agents are automatic.** The plugin spawns specialist agents behind the scenes. You don't manage them directly.
- **Read-only agents stay lean.** Most specialist reviewers and analyzers set
  `omitClaudeMd: true`, so subagents keep product/runtime context while
  skipping contributor-only repo guidance.
- **The stack is detected, not guessed.** `/rb:init` and SessionStart hooks identify Rails/Grape/Sidekiq/Karafka, Active Record vs Sequel, and Packwerk/modular package layouts before giving guidance.
- **Session start is split into fast sync + async refresh.** You get immediate
  stack context from the quick snapshot while slower helper-version probes
  refresh in the background.
- **Fresh research is reused, not re-bought.** `/rb:plan` checks
  `.claude/research/` and prior plan research before respawning
  duplicate topic-research agents.
- **Workflow continuity is hook-backed.** `PreCompact`, `PostCompact`, and
  `StopFailure` warn before compaction, log failure context, and surface
  re-read reminders after compaction or failed stops instead of relying only on
  chat memory.

### Plan Namespaces

Every plan gets its own directory with its implementation-state artifacts:

```
.claude/
├── plans/{slug}/          # Everything for ONE plan
│   ├── plan.md            # The plan itself (checkboxes = state)
│   ├── research/          # Research agent output
│   ├── summaries/         # Compressed multi-agent output
│   ├── progress.md        # Session progress log
│   └── scratchpad.md      # Structured dead ends, decisions, hypotheses, handoffs
├── research/              # Reusable cross-plan topic research
├── reviews/               # Review artifacts (per-agent + consolidated)
└── solutions/             # Compound knowledge (reusable across plans)
```

Implementation state stays under one plan namespace; review artifacts stay consistently under `.claude/reviews/`.

## Architecture

### Agent Hierarchy

The plugin uses 23 agents organized into 3 tiers:

```
                    ┌──────────────────────────────┐
                    │  Orchestrators (opus model)  │
                    │  Coordinate phases, spawn    │
                    │  specialists, manage flow    │
                    └──────────┬───────────────────┘
                               │
         ┌─────────────────────┼──────────────────────┐
         │                     │                      │
         ▼                     ▼                      ▼
┌───────────────┐  ┌───────────────────┐  ┌────────────────────┐
│ workflow-     │  │ planning-         │  │ parallel-          │
│ orchestrator  │  │ orchestrator      │  │ reviewer           │
│ (full cycle)  │  │ (research phase)  │  │ (review phase)     │
└───────────────┘  └───────────────────┘  └────────────────────┘
                               │                      │
                    ┌──────────┼──────────┐    ┌──────┼──────┐
                    ▼          ▼          ▼    ▼      ▼      ▼
             ┌──────────┐ ┌────────┐ ┌──────┐ ... 4 specialist
             │ rails    │ │ active │ │ web  │     review agents
             │ architect│ │ record │ │ rsch │
             └──────────┘ └────────┘ └──────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             ┌────────────┐      ┌──────────────┐
             │  context-  │      │ Orchestrator  │
             │ supervisor │ ───► │ reads ONLY    │
             │  (haiku)   │      │ the summary   │
             └────────────┘      └──────────────┘
```

**Orchestrators** (opus) -- Primary workflow coordinators, security-critical analysis.
**Specialists** (sonnet) -- Domain experts, secondary orchestrators, judgment-heavy tasks. Sonnet 4.6 achieves near-opus quality at sonnet pricing.
**Lightweight** (haiku) -- Mechanical tasks: verification, compression, dependency analysis.

### The Context Supervisor Pattern

When an orchestrator spawns 4-8 research agents, their combined output can exceed 50k tokens -- flooding the parent's context window. The **context-supervisor** solves this using a compression pattern:

```
┌────────────────────────────────────────────────────┐
│  Orchestrator (thin coordinator, ~10k context)     │
│  Only reads: summaries/consolidated.md             │
└──────────────────┬─────────────────────────────────┘
                   │ spawns AFTER workers finish
┌──────────────────▼─────────────────────────────────┐
│  context-supervisor (haiku, fresh 200k context)    │
│  Reads: all worker output files                    │
│  Applies: compression strategy based on size       │
│  Validates: every input file represented           │
│  Writes: summaries/consolidated.md                 │
└──────────────────┬─────────────────────────────────┘
                   │ reads from
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
   worker 1      worker 2      worker N
   research/     research/     research/
   patterns.md   security.md   active-record.md
```

**How compression works:**

| Total Output    | Strategy   | Compression | What's Kept                    |
| --------------- | ---------- | ----------- | ------------------------------ |
| Under 8k tokens | Index      | ~100%       | Full content with file list    |
| 8k - 30k tokens | Compress   | ~40%        | Key findings, decisions, risks |
| Over 30k tokens | Aggressive | ~20%        | Only critical items            |

The supervisor also **deduplicates** -- if two agents flag the same issue
(e.g., both the security analyzer and code reviewer find a missing
authorization check), it merges them into one finding with both sources cited.

**Used by:** planning-orchestrator (research synthesis), parallel-reviewer (review deduplication), audit skill (cross-category analysis).

### How Planning Works

When you run `/rb:plan Add real-time notifications`:

```
1. planning-orchestrator analyzes your request
   │
2. Spawns specialists IN PARALLEL based on feature needs:
   ├── rails-patterns-analyst    (always -- scans your codebase)
   ├── rails-architect           (if service/context changes needed)
   ├── active-record-schema-designer (if database changes needed)
   ├── security-analyzer         (if auth/user data involved)
   ├── sidekiq-specialist        (if background jobs needed)
   ├── web-researcher            (if unfamiliar technology)
   └── ... up to 8 agents
   │
3. Each agent writes to `.claude/plans/{slug}/research/{topic}.md`
   │
4. context-supervisor compresses all research into one summary
   │
5. Orchestrator reads the summary + synthesizes the plan
   │
6. Output: `.claude/plans/{slug}/plan.md` with [P1-T1] checkboxes
```

### How Review Works

When you run `/rb:review`:

```
1. parallel-reviewer collects your git diff
   │
2. Delegates to 4 EXISTING specialist agents:
   ├── ruby-reviewer        → Idioms, patterns, error handling
   ├── security-analyzer    → SQL injection, XSS, auth gaps
   ├── testing-reviewer     → Test coverage, factory patterns
   └── verification-runner  → zeitwerk:check, format, test
   │
3. Each reviewer writes to `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md`
   │
4. context-supervisor deduplicates + consolidates
   │
5. Output: `.claude/reviews/{review-slug}.md`
```

## Usage Guide

### Quick tasks (bug fixes, small changes)

Just describe what you need. The plugin auto-detects complexity and suggests the right approach:

```
> Fix the N+1 query in the dashboard

Claude: This is a simple fix (score: 2). I'll handle it directly.
```

Or use `/rb:quick` to skip ceremony:

```
/rb:quick Add pagination to the users list
```

### Medium tasks (new features, refactors)

Use `/rb:plan` to create an implementation plan, then `/rb:work` to execute it:

```
/rb:plan Add email notifications for new comments
```

The plugin will:

1. Spawn research agents to analyze your codebase patterns
2. Show a completeness check (every requirement mapped to a task)
3. Ask you how to proceed (start implementation, review plan, adjust)

When starting implementation, the plugin recommends a **fresh session** for plans with 5+ tasks. The plan file is self-contained, so no context from the planning session is needed:

```
# In a new Claude Code session:
/rb:work .claude/plans/email-notifications/plan.md
```

### Large tasks (new domains, security features)

Use deep research planning:

```
/rb:plan Add OAuth login with Google and GitHub
```

This spawns 4+ parallel research agents, then produces a detailed plan.
For security-sensitive features, the plugin will ask clarifying questions
before proceeding. Or use `/rb:full` for fully autonomous development.

### Fixing review issues

After implementing, run a review:

```
/rb:review
```

Four parallel agents check your code (idioms, tests, security, verification). If blockers are found, the plugin asks whether to replan or fix directly:

```
Review found 2 blockers:
1. Missing authorization in controller action -- security risk
2. N+1 query in list_comments -- performance issue

Options:
- Replan fixes (/rb:plan --existing)
- Fix directly (/rb:work)
- Handle myself
```

### Project health checks

Run a comprehensive audit with 5 parallel specialist agents:

```
/rb:audit                    # Full audit
/rb:audit --quick            # 2-3 minute pulse check
/rb:audit --focus=security   # Deep dive single area
/rb:audit --since HEAD~10    # Audit recent changes only
```

The audit scores your project across 5 categories (architecture, performance, security, tests, dependencies) and produces an actionable report.

### Full autonomous mode

For hands-off development:

```
/rb:full Add user profile avatars with S3 upload
```

Runs the complete cycle: plan (with research), work, verify, review. After review fixes, re-verifies before cycling back. Captures learnings on completion.

## Workflow Tips

### Context management

- `/rb:plan` creates a **self-contained plan file** with all implementation details
- For 5+ task plans, start `/rb:work` in a **fresh session** to maximize context space
- For small plans (2-4 tasks), continuing in the same session is fine

### Resuming work

Plan checkboxes are the state. If a session ends mid-work:

```
# Just run /rb:work on the same plan -- it finds the first [ ] and continues
/rb:work .claude/plans/my-feature/plan.md
```

### Splitting large features

When a feature has 10+ tasks across different domains, the plugin offers to split into multiple plan files:

```
Created 3 plans (14 total tasks):
1. .claude/plans/auth/plan.md (5 tasks -- login, register, reset)
2. .claude/plans/profiles/plan.md (4 tasks -- avatar, bio, settings)
3. .claude/plans/admin/plan.md (5 tasks -- dashboard, roles)

Recommended order: 1 -> 2 -> 3
```

Execute each plan separately with `/rb:work`.

### Learning from mistakes

After fixing a bug or receiving a correction:

```
/rb:learn Fixed N+1 query -- always preload associations in service objects
```

This updates the plugin's knowledge base so the same mistake is prevented in future sessions.

## Iron Laws (Non-Negotiable Rules)

<!-- IRON_LAWS_START -->

<!-- GENERATED FROM iron-laws.yml — DO NOT EDIT -->

The plugin enforces **21 Iron Laws** that prevent common, costly mistakes:

| Category | Count | Laws |
|----------|-------|------|
| Active Record | 7 | Use decimal for money, never float; Use parameterized queries, never SQL interpolation; Use includes/preload to prevent N+1 queries; In Active Record code, use after_commit when enqueueing jobs; Wrap multi-step operations in transactions; Never bypass validations in normal code; Never use default_scope |
| Sidekiq | 4 | Jobs must be idempotent (safe to retry); Job args must be JSON-safe only; Never pass ORM objects to jobs — pass IDs; Always enqueue jobs after commit using the active ORM |
| Security | 4 | Never use eval with user input; Authorize explicitly in every action; Never use html_safe/raw on untrusted content; Never concatenate SQL strings |
| Ruby | 3 | Always pair method_missing with respond_to_missing?; Always supervise background processes; Only rescue StandardError, never Exception |
| Hotwire/Turbo | 2 | Pre-compute all data before Turbo Stream broadcast; Use turbo_frame_tag for partial page updates |
| Verification | 1 | Always run tests and show results before claiming done |

### Enforcement

- **Programmatic**: 6 programmatic detectors checked automatically on targeted Ruby-ish edits
- **Behavioral**: All 21 laws injected into subagent context
- **Review-time**: Full audit during `/rb:review`

See [full registry](plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md) for details.

<!-- IRON_LAWS_END -->

## Commands Reference

### Workflow

| Command                 | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `/rb:full <feature>`    | Full autonomous cycle (plan, work, verify, review, compound) |
| `/rb:brainstorm <topic>`| Adaptive requirements gathering before planning              |
| `/rb:plan <input>`      | Create implementation plan with specialist agents            |
| `/rb:plan --existing`   | Enhance existing plan with deeper research                   |
| `/rb:work <plan-file>`  | Execute plan tasks with verification                         |
| `/rb:review [focus]`    | Multi-agent code review (4 parallel agents)                  |
| `/rb:compound`          | Capture solved problem as reusable knowledge                 |
| `/rb:triage`            | Interactive triage of review findings                        |
| `/rb:document`          | Generate YARD/RDoc, README, ADRs                             |
| `/rb:learn <lesson>`    | Capture lessons learned                                      |
| `/rb:brief <plan>`      | Interactive plan walkthrough                                 |
| `/rb:perf`              | Performance analysis with specialist agents                  |
| `/rb:pr-review`         | Address PR review comments                                   |
| `/rb:permissions`       | Analyze permission prompts and suggest safe settings entries  |

### Utility

| Command                  | Description                                                |
| ------------------------ | ---------------------------------------------------------- |
| `/rb:intro`              | Interactive plugin tutorial (6 sections, ~5 min)           |
| `/rb:init`               | Initialize plugin in a project (auto-activation rules)     |
| `/rb:quick <task>`       | Fast implementation, skip ceremony                         |
| `/rb:investigate <bug>`  | Systematic bug debugging (4 parallel investigation tracks) |
| `/rb:research <topic>`   | Research Ruby topics on the web                            |
| `/rb:verify`             | Prefer project-native verify wrapper, else run full direct verification |
| `/rb:trace <method>`     | Build call trees to trace method flow                      |
| `/rb:boundaries`         | Analyze Rails service boundaries                           |
| `/rb:examples`           | Practical examples and pattern walkthroughs                |
| `/rb:constraint-debug`   | Debug ActiveRecord constraint violations                   |

### Analysis

| Command              | Description                                       |
| -------------------- | ------------------------------------------------- |
| `/rb:n1-check`       | Detect N+1 query patterns                         |
| `/rb:state-audit`    | Audit request state, CurrentAttributes, caching   |
| `/rb:runtime`        | Runtime tooling integration (Tidewave, etc.)      |
| `/rb:secrets`        | Scan for leaked secrets and API keys              |
| `/rb:techdebt`       | Find technical debt and refactoring opportunities |
| `/rb:audit`          | Full project health audit with 5 parallel agents  |
| `/rb:challenge`      | Rigorous review mode ("grill me")                 |

## Agents (23)

| Agent                             | Model  | Memory  | Role                                         |
| --------------------------------- | ------ | ------- | -------------------------------------------- |
| **workflow-orchestrator**         | opus   | project | Full cycle coordination (plan, work, review) |
| **planning-orchestrator**         | opus   | project | Parallel research agent coordination         |
| **parallel-reviewer**             | opus   | --      | 4-agent parallel code review                 |
| **deep-bug-investigator**         | sonnet | --      | 4-track structured bug investigation         |
| **call-tracer**                   | sonnet | --      | Parallel call tree tracing                   |
| **security-analyzer**             | opus   | --      | OWASP vulnerability scanning                 |
| **context-supervisor**            | haiku  | --      | Multi-agent output compression               |
| **verification-runner**           | haiku  | --      | zeitwerk:check, format, test                 |
| **output-verifier**               | sonnet | --      | Provenance checks for research/review claims |
| **iron-law-judge**                | sonnet | --      | Pattern-based Iron Law detection             |
| **dependency-analyzer**           | sonnet | --      | Module dependency & dead code analysis       |
| **ruby-gem-researcher**           | sonnet | --      | RubyGems library evaluation                  |
| **rails-architect**               | sonnet | --      | Service structure, Hotwire/Turbo patterns    |
| **active-record-schema-designer** | sonnet | --      | Migrations, data models, query patterns      |
| **rails-patterns-analyst**        | sonnet | --      | Codebase pattern discovery                   |
| **ruby-reviewer**                 | sonnet | --      | Code idioms, patterns, conventions           |
| **testing-reviewer**              | sonnet | --      | RSpec, Minitest, factory patterns            |
| **sidekiq-specialist**            | sonnet | --      | Job idempotency, error handling              |
| **ruby-runtime-advisor**          | sonnet | --      | Performance, memory, concurrency             |
| **deployment-validator**          | sonnet | --      | Docker, Kubernetes, Fly.io config            |
| **web-researcher**                | haiku  | --      | Tiered-source docs and GitHub research       |
| **data-integrity-reviewer**       | sonnet | --      | Data consistency and constraint validation   |
| **migration-safety-reviewer**     | sonnet | --      | Migration safety and rollback review         |

Agents with `project` memory leverage Claude Code's built-in memory system
to retain context across sessions. Orchestrators remember architectural
decisions; pattern analysts skip redundant discovery.

## Reference Skills (Auto-Loaded)

These load automatically based on file context -- no commands needed:

| Skill                     | Triggers On                                      |
| ------------------------- | ------------------------------------------------ |
| `ruby-idioms`             | Any `.rb` file                                   |
| `rails-contexts`          | Context modules, router, controllers, services   |
| `hotwire-patterns`        | Views, Turbo frames, Stimulus controllers        |
| `active-record-patterns`  | Models, migrations, queries, associations        |
| `testing`                 | `*_spec.rb`, `*_test.rb`, factories              |
| `sidekiq`                 | Sidekiq jobs, workers, queue config              |
| `security`                | Auth, sessions, CSRF/CSP, input validation       |
| `deploy`                  | Dockerfile, fly.toml, production config          |
| `runtime-integration`     | Runtime debugging, live process inspection       |
| `intent-detection`        | First message routing to /rb: commands           |
| `compound-docs`           | Solution documentation lookups                   |

## Runtime Tooling Integration

The plugin integrates with [Tidewave Rails](https://github.com/tidewave-ai/tidewave_rails) for runtime debugging and introspection:

```bash
# Install Tidewave in your Rails app
bundle add tidewave --group development

# Runtime commands use Tidewave MCP tools
/rb:runtime execute "User.count"           # Execute Ruby in Rails context
/rb:runtime query "SELECT * FROM users"    # Execute SQL
/rb:runtime docs "ActiveRecord::QueryMethods"  # Fetch version-specific docs
/rb:runtime logs                           # Read application logs
```

**Note:** Runtime features require Tidewave Rails gem and Tidewave MCP tool access.

## Requirements

- Claude Code CLI
- Ruby/Rails/Grape project

### Optional

- **Runtime tooling** (Tidewave) for runtime debugging
- **ccrider** for contributor-only session analysis (see Contributing)

## Inspired By

This plugin draws inspiration from two excellent Claude Code plugin ecosystems:

- **[Elixir/Phoenix Plugin](https://github.com/oliver-kriska/claude-elixir-phoenix)** by Oliver Kriska —
  The primary architectural inspiration. Adopted the agentic workflow philosophy, filesystem-as-state-machine pattern,
  context supervisor compression, and the "Iron Laws" concept for non-negotiable rules.

- **[Compound Engineering Plugin](https://github.com/EveryInc/compound-engineering-plugin)** by Every Inc —
  Contributed ideas around parallel specialist review orchestration, structured investigation tracks, and solution compounding.

The goal is to bring the same rigorous, automated quality enforcement to Ruby/Rails/Grape development that these plugins provide for their respective stacks.

## Contributing

PRs welcome! See [CLAUDE.md](CLAUDE.md) for development conventions.

### Development rules

- Skills: keep `SKILL.md` concise and push most detail into `references/`;
  prefer roughly `100-200` lines for new skills, but allow larger framework or
  workflow skills when splitting further would make routing or navigation worse
- Agents: under 300 lines, `disallowedTools` for reviewers
- Markdown-only edits should pass `npm run lint:markdown`; `npm run lint`
  runs the full local lint/validation bundle

### Contributor prerequisites

Local contributor workflows require more than `npm ci` alone:

- `python3` `3.10+` for eval tooling and release checks
- `ruby` for YAML validation and Ruby maintenance scripts
- `shellcheck` for `npm run lint`, `make ci`, and local shell pre-commit checks
- Claude Code CLI for `npm run validate` / `make validate`
- `jq` for local hook/runtime script validation

Practical bootstrap:

- `npm ci`
- `npm run doctor`

If `npm run validate` reports `claude` missing, install it with:

```bash
npm install -g @anthropic-ai/claude-code
```

### Eval workflow

The canonical contributor eval workflow now lives in
[CLAUDE.md](CLAUDE.md#contributor-eval-workflow). Use that section for the full
command matrix and caveats.

Common entrypoints:

- `make eval` or `npm run eval` for lint + injection check + changed surfaces
- `make eval-ci` or `npm run eval:ci` for the contributor CI gate
- `make eval-tests` or `npm run eval:test` for the default contributor test
  path (`unittest` by default for deterministic cross-environment runs)
- contributor eval tooling requires `python3` 3.10+

Notes:

- `--include-untracked` is local-only for changed-mode exploration and is not
  part of `eval-ci`
- `scripts/check-dynamic-injection.sh` expects git metadata for comparable
  tracked-file scans and now refuses broad non-git fallback scans
- local pre-commit checks staged Markdown, JSON, and shell syntax; CI is broader

### Docs-check and session analytics

Contributor-only maintenance tooling under `.claude/` now has two distinct
roles:

- `/docs-check` validates the plugin against the current cached Claude Code
  docs and should be treated as a docs-compatibility workflow, not a generic
  style lint
- `/session-scan`, `/session-deep-dive`, `/session-trends`, and
  `/skill-monitor` are exploratory analytics workflows for contributors using
  `ccrider`

Practical guidance:

- prefer `claude plugin validate`, `make eval`, and `/docs-check` before
  trusting session-derived conclusions
- when using session analytics, prefer provider-scoped runs such as
  `--provider claude-code`
- treat transcript-derived metrics as heuristic triage signals, not release
  proof

## License

MIT
