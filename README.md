# Ruby/Rails/Grape Plugin for Claude Code

**Claude Code is great. But it doesn't know that `default_scope` will bite you later, that `t.float` will corrupt your money fields, or that your Sidekiq job isn't idempotent.**

This plugin does. It coordinates **22 specialist agents** and **49 skills** that plan, implement,
review, and verify your Ruby/Rails/Grape code in parallel -- each with domain
expertise, fresh context, and enforced [Iron Laws](#iron-laws-non-negotiable-rules)
that catch the bugs your tests won't. It is now stack-aware enough to handle
mixed Active Record + Sequel repos and Packwerk-style modular monoliths
without flattening everything into generic Rails advice.

```bash
# You describe the feature. The plugin figures out the rest.
/rb:plan Add real-time comment notifications

# 4 research agents analyze your codebase in parallel.
# A structured plan lands in .claude/plans/comment-notifications/plan.md
# Then:

/rb:work .claude/plans/comment-notifications/plan.md
# Implements task by task. Verification checkpoints at key milestones.
# Stops cold if code violates an Iron Law.

/rb:review
# 4 specialist agents audit in parallel:
# idioms, security, tests, verification.
# Deduplicates findings. Flags pre-existing issues separately.
```

No prompt engineering. No "please check for N+1 queries." The plugin auto-loads
the right domain knowledge based on what files you're editing and enforces rules
that prevent the mistakes Ruby developers actually make in production.

```
┌─────────────────────────────────────────────────────────────────────┐
│  💎 Ruby/Rails/Grape Plugin for Claude Code                         │
│                                                                     │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐           │
│  │    22    │    49    │   100+   │    21    │    21    │           │
│  │  Agents  │  Skills  │   Refs   │  Hooks   │Iron Laws │           │
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
│    web-researcher                  progress-tracking · block-danger │
│                                                                     │
│  ───────────────────────────────────────────────────────────        │
│  21 Iron Laws · Runtime Tooling · plan→work→verify→review→compound  │
│  github.com/slbug/claude-ruby-grape-rails                           │
└─────────────────────────────────────────────────────────────────────┘
```

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

# Option A: Test local working-tree changes directly
claude --plugin-dir ./claude-ruby-grape-rails/plugins/ruby-grape-rails

# Option B: Validate marketplace install flow
# Note: marketplace.json now uses git-subdir source, so this installs the
# published GitHub-backed plugin source, not your uncommitted working tree.
/plugin marketplace add ./claude-ruby-grape-rails
/plugin install ruby-grape-rails
```

### Known Limitations

**Marketplace Install & Agent Permissions**: This plugin's specialist agents require
`permissionMode: bypassPermissions` to run Bash commands in the background. When installed
via marketplace, Claude Code strips this field, which may cause "permission check failed" errors.

**Workarounds:**

1. Copy agents to your local `~/.claude/agents/` directory (they'll retain permissions)
2. Add permissive rules to your project's `.claude/settings.json`:

   ```json
   {
     "permissions": {
       "defaultMode": "acceptEdits",
       "allow": [
         "Bash(bundle *)",
         "Bash(rails *)",
         "Bash(rake *)",
         "Read(*)",
         "Glob(*)"
       ]
     }
   }
   ```

3. Use `--plugin-dir` for local development (development mode honors `permissionMode`)

We are working on a marketplace-compatible redesign (Phase 3B in plan).

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

The plugin implements a **Plan, Work, Verify, Review, Compound** lifecycle. Each phase produces artifacts in a namespaced directory:

```
/rb:plan → /rb:work → /rb:verify → /rb:review → /rb:compound
     │           │            │              │              │
     ↓           ↓            ↓              ↓              ↓
plans/{slug}/  (in namespace) (in namespace) (in namespace) solutions/
```

- **Plan** -- Research agents analyze your codebase in parallel, then synthesize a structured implementation plan
- **Work** -- Execute the plan task-by-task with quick verification checks after each change
- **Verify** -- Full verification loop (zeitwerk, format, test) before review
- **Review** -- Four specialist agents audit your code in parallel (idioms, security, tests, static analysis)
- **Compound** -- Capture what you learned as reusable knowledge for future sessions

### Key Concepts

- **Filesystem is the state machine.** Each phase reads from the previous phase's output. No hidden state.
- **Plan namespaces.** Each plan owns its implementation-state artifacts in `.claude/plans/{slug}/` -- plan, research, summaries, progress, scratchpad.
- **Reviews are standalone artifacts.** Reviewer outputs live under `.claude/reviews/`, not inside plan namespaces.
- **Plan checkboxes track progress.** `[x]` = done, `[ ]` = pending. `/rb:work` finds the first unchecked task and continues.
- **One plan = one work unit.** Large features get split into multiple plans. Each is self-contained.
- **Agents are automatic.** The plugin spawns specialist agents behind the scenes. You don't manage them directly.
- **The stack is detected, not guessed.** `/rb:init` and SessionStart hooks identify Rails/Grape/Sidekiq/Karafka, Active Record vs Sequel, and Packwerk/modular package layouts before giving guidance.
- **Workflow continuity is hook-backed.** `PreCompact`, `PostCompact`, and `StopFailure` preserve plan context through compaction and failed stops instead of relying only on chat memory.

### Plan Namespaces

Every plan gets its own directory with its implementation-state artifacts:

```
.claude/
├── plans/{slug}/          # Everything for ONE plan
│   ├── plan.md            # The plan itself (checkboxes = state)
│   ├── research/          # Research agent output
│   ├── summaries/         # Compressed multi-agent output
│   ├── progress.md        # Session progress log
│   └── scratchpad.md      # Auto-written decisions, dead-ends, handoffs
├── reviews/               # Review artifacts (per-agent + consolidated)
└── solutions/             # Compound knowledge (reusable across plans)
```

Implementation state stays under one plan namespace; review artifacts stay consistently under `.claude/reviews/`.

## Architecture

### Agent Hierarchy

The plugin uses 22 agents organized into 3 tiers:

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
3. Each agent writes to plans/{slug}/research/{topic}.md
   │
4. context-supervisor compresses all research into one summary
   │
5. Orchestrator reads the summary + synthesizes the plan
   │
6. Output: plans/{slug}/plan.md with [P1-T1] checkboxes
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

- **Programmatic**: 7 laws checked automatically on every file edit
- **Behavioral**: All 21 laws injected into subagent context
- **Review-time**: Full audit during `/rb:review`

See [full registry](plugins/ruby-grape-rails/references/iron-laws.yml) for details.

<!-- IRON_LAWS_END -->

## Commands Reference

### Workflow

| Command                 | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `/rb:full <feature>`    | Full autonomous cycle (plan, work, verify, review, compound) |
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

### Utility

| Command                  | Description                                                |
| ------------------------ | ---------------------------------------------------------- |
| `/rb:intro`              | Interactive plugin tutorial (6 sections, ~5 min)           |
| `/rb:init`               | Initialize plugin in a project (auto-activation rules)     |
| `/rb:quick <task>`       | Fast implementation, skip ceremony                         |
| `/rb:investigate <bug>`  | Systematic bug debugging (4 parallel investigation tracks) |
| `/rb:research <topic>`   | Research Ruby topics on the web                            |
| `/rb:verify`             | Run full verification (zeitwerk, format, test)             |
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

## Agents (22)

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
| **web-researcher**                | sonnet | --      | Ruby Weekly, docs, GitHub research           |
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
- **ccrider** for session analysis (see Contributing)

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

- Skills: ~100 lines SKILL.md + `references/` for details
- Agents: under 300 lines, `disallowedTools` for reviewers
- All markdown passes `npm run lint`

## License

MIT
