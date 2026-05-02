# Ruby/Rails/Grape Plugin for Claude Code

**Claude Code is great. But it doesn't know that `default_scope` will bite you later, that `t.float` will corrupt your money fields, or that your Sidekiq job isn't idempotent.**

This plugin does. It coordinates **19 specialist agents** and **53 skills** that plan, implement,
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
│  │    19    │    53    │   100+   │    14    │    22    │           │
│  │  Agents  │  Skills  │   Refs   │  Events  │Iron Laws │           │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘           │
│                                                                     │
│  AGENTS                          COMMANDS                           │
│  ─────────────────────           ──────────────────────────         │
│  Reviewers (mostly sonnet)       Workflow                           │
│    ruby-reviewer                   /rb:plan    /rb:work             │
│    testing-reviewer                /rb:review  /rb:full             │
│    security-analyzer (opus)        /rb:compound /rb:quick           │
│    iron-law-judge                  /rb:brief   /rb:triage           │
│    data-integrity-reviewer                                          │
│    migration-safety-reviewer                                        │
│    output-verifier                                                  │
│                                                                     │
│  Architecture (sonnet)           Investigation & Debug              │
│    rails-architect                 /rb:investigate /rb:trace        │
│    active-record-schema-designer   /rb:n1-check   /rb:perf          │
│    rails-patterns-analyst          /rb:constraint-debug             │
│    ruby-runtime-advisor            /rb:state-audit                  │
│                                                                     │
│  Investigation (sonnet)          Analysis & Review                  │
│    deep-bug-investigator           /rb:audit    /rb:verify          │
│    call-tracer                     /rb:techdebt /rb:boundaries      │
│    dependency-analyzer             /rb:pr-review /rb:challenge      │
│                                    /rb:research  /rb:document       │
│                                                                     │
│  Domain (sonnet)                 Knowledge (auto-loaded)            │
│    sidekiq-specialist              hotwire-patterns                 │
│    deployment-validator            active-record-patterns           │
│    ruby-gem-researcher             ruby-idioms      security        │
│                                    rails-contexts   sidekiq         │
│                                    testing   deploy   runtime       │
│                                                                     │
│  Mechanical / Extraction (haiku)                                    │
│    verification-runner                                              │
│    web-researcher                                                   │
│                                                                     │
│  Hooks (plugin-wide, not tied to specific agents)                   │
│    auto-format · ruby-syntax-check · iron-law-verify                │
│    security-scan · debug-stmt-detect · error-critic                 │
│    progress-tracking · db/prod/git                                  │
│                                                                     │
│  ───────────────────────────────────────────────────────────        │
│  22 Iron Laws · Runtime Tooling · plan→work→verify→review→compound  │
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
          "Bash(mkdir -p **/.claude/**)",
          "Bash(${CLAUDE_PLUGIN_ROOT}/bin/manifest-update *)",
          "Grep(*)",
          "Read(*)",
          "Glob(*)",
          "Write(**/.claude/plans/**)",
          "Write(**/.claude/reviews/**)",
          "Write(**/.claude/audit/**)",
          "Write(**/.claude/research/**)",
          "Write(**/.claude/solutions/**)",
          "Write(**/.claude/skill-metrics/**)",
          "Write(**/.claude/investigations/**)"
       ]
     }
   }
   ```

   Recursive `**/.claude/<ns>/**` globs are required: plugin skills
   write artifacts under nested per-agent subdirs (e.g.,
   `.claude/reviews/{agent-slug}/{slug}-{datesuffix}.md`). Shallow
   `Write(.claude/<ns>/*)` globs do not match.

2. Run `/rb:permissions` to scan recent prompts and propose safer
   `settings.json` allowlists instead of growing them blindly
3. Run `/update-config` to add the recommended Write rules above to
   `settings.json` without hand-editing
4. Use `--plugin-dir` for local development while iterating on the plugin itself

## Configuration

Per-shell environment toggles (no `settings.json` edit required):

| Env var | Default | Effect when set |
|---------|---------|-----------------|
| `RUBY_PLUGIN_DISABLE_RULES_INJECTION` | `0` (injection on) | `=1` skips Iron Laws + Advisory Preferences injection on `SessionStart` and `SubagentStart`. Use when the plugin is installed at user scope but the active project is not Ruby/Rails/Grape. |
| `RUBY_PLUGIN_STRICT_PERMS` | `0` (soft deny) | `=1` makes `block-dangerous-ops.sh` `PermissionRequest` deny include `interrupt: true`, fully stopping Claude rather than just denying the single command. |
| `RUBY_PLUGIN_HOOK_MODE` | `default` | `=strict` broadens `secret-scan.sh` to recent-change sweeps and fails closed when broader coverage cannot be trusted. |
| `RUBY_PLUGIN_COMPRESSION_TELEMETRY` | `0` (off) | `=1` opts in to verify-output compression telemetry collection at `${CLAUDE_PLUGIN_DATA}/compression.jsonl`. |

Set per-shell, per-command, or via [direnv](https://direnv.net/) `.envrc`
for project-scoped values.

## Getting Started

New to the plugin? Run the interactive tutorial:

```bash
/rb:intro
```

It walks through the workflow, commands, and features in 8 short sections (~5 min).
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
- **Investigations are standalone artifacts.** `deep-bug-investigator`
  writes its report to
  `.claude/investigations/deep-bug-investigator/{slug}-{datesuffix}.md`
  and returns a ≤300-word chat summary; the file is the real output.
- **Plan checkboxes track progress.** `[x]` = done, `[ ]` = pending. `/rb:work` finds the first unchecked task and continues.
- **One plan = one work unit.** Large features get split into multiple plans. Each is self-contained.
- **Agents are automatic.** The plugin spawns specialist agents behind the scenes. You don't manage them directly.
- **Specialist agents stay lean.** Reviewers and analyzers set
  `omitClaudeMd: true` so subagents keep product/runtime context while
  skipping contributor-only repo guidance. They are instructed to write
  only their own artifacts under `.claude/`, not edit project code.
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

The plugin uses 19 leaf agents organized by responsibility. Skill bodies
(main session) spawn agents in parallel. Models vary by risk: `opus` for
security-critical (1 agent), `sonnet` for judgment-heavy specialists
(16 agents), `haiku` for mechanical extraction (2 agents).

```
                ┌──────────────────────────────────────┐
                │  Specialists (mixed — 17 agents)     │
                │  Domain experts; called from skill   │
                │  bodies (main session) in parallel.  │
                │  security-analyzer is opus; rest     │
                │  sonnet.                              │
                └────────────────┬─────────────────────┘
                                 │
       ┌──────────────────┬──────┴───────┬──────────────────────┐
       ▼                  ▼              ▼                      ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  Reviewers   │  │ Architecture │  │ Investigation│  │   Domain         │
│              │  │              │  │              │  │                  │
│ ruby-        │  │ rails-       │  │ deep-bug-    │  │ sidekiq-         │
│   reviewer   │  │   architect  │  │   investigator│ │   specialist     │
│ security-    │  │ active-      │  │ call-tracer  │  │ deployment-      │
│   analyzer   │  │   record-    │  │ dependency-  │  │   validator      │
│   (opus)     │  │   schema-    │  │   analyzer   │  │ ruby-gem-        │
│ testing-     │  │   designer   │  │              │  │   researcher     │
│   reviewer   │  │ rails-       │  │              │  │                  │
│ iron-law-    │  │   patterns-  │  │              │  │                  │
│   judge      │  │   analyst    │  │              │  │                  │
│ data-        │  │ ruby-runtime-│  │              │  │                  │
│   integrity- │  │   advisor    │  │              │  │                  │
│   reviewer   │  │              │  │              │  │                  │
│ migration-   │  │              │  │              │  │                  │
│   safety-    │  │              │  │              │  │                  │
│   reviewer   │  │              │  │              │  │                  │
│ output-      │  │              │  │              │  │                  │
│   verifier   │  │              │  │              │  │                  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘

       ┌─────────────────────────────────────────────┐
       │  Mechanical / Extraction (haiku — 2)        │
       │  verification-runner — verification         │
       │  web-researcher — web/source extraction     │
       │  Called from skill bodies as leaf workers.  │
       └─────────────────────────────────────────────┘
```

**Specialists** (mostly sonnet, security-analyzer opus) -- Domain experts, judgment-heavy tasks.
**Mechanical / Extraction** (haiku) -- Compression, verification, web-research extraction (matches dashboard tier name).

### How Planning Works

When you run `/rb:plan Add real-time notifications`:

```
1. `/rb:plan` skill body analyzes your request from main session
   │
2. Spawns specialists IN PARALLEL via `Agent(subagent_type:)` calls:
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
4. Skill body reads each research artifact + synthesizes the plan
   │
5. Output: `.claude/plans/{slug}/plan.md` with [P1-T1] checkboxes
```

### How Review Works

When you run `/rb:review`:

```
1. `/rb:review` skill body collects git diff + reviewer list
   │
2. `manifest-update prepare-run --skill=rb:review --slug=<slug>
    --base-ref=<ref> --agents=<csv>` archives any prior manifest +
   inits a fresh `.claude/reviews/<slug>/RUN-CURRENT.json`
   (helper computes datesuffix, agent paths, consolidated path,
   git pins)
   │
3. Spawns 4 EXISTING specialist agents in parallel:
   ├── ruby-reviewer        → Idioms, patterns, error handling
   ├── security-analyzer    → SQL injection, XSS, auth gaps
   ├── testing-reviewer     → Test coverage, factory patterns
   └── verification-runner  → zeitwerk:check, format, test
   │
4. Each reviewer writes to `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md`
   │
5. Skill body reads each artifact + dedupes + writes consolidated review
   │
6. Output: `.claude/reviews/{review-slug}-{datesuffix}.md`
   Manifest: `.claude/reviews/{review-slug}/RUN-CURRENT.json` (status: complete)
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

Runs the complete cycle: plan (with research), work, verify, review. Halts on Critical findings; user decides next step.

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

The plugin enforces **22 Iron Laws** that prevent common, costly mistakes:

| Category | Count | Laws |
|----------|-------|------|
| Active Record | 7 | Use decimal for money, never float; Use parameterized queries, never SQL interpolation; Use includes/preload to prevent N+1 queries; In Active Record code, use after_commit when enqueueing jobs; Wrap multi-step operations in transactions; Never bypass validations in normal code; Never use default_scope |
| Sidekiq | 4 | Jobs must be idempotent (safe to retry); Job args must be JSON-safe only; Never pass ORM objects to jobs — pass IDs; Always enqueue jobs after commit using the active ORM |
| Security | 4 | Never use eval with user input; Authorize explicitly in every action; Never use html_safe/raw on untrusted content; Never concatenate SQL strings |
| Ruby | 3 | Always pair method_missing with respond_to_missing?; Always supervise background processes; Only rescue StandardError, never Exception |
| Hotwire/Turbo | 2 | Pre-compute all data before Turbo Stream broadcast; Use turbo_frame_tag for partial page updates |
| Verification & Discipline | 2 | Always run tests and show results before claiming done; Only change what the user asked for — no drive-by improvements |

### Enforcement

- **Programmatic**: 6 programmatic detectors checked automatically on targeted Ruby-ish edits
- **Behavioral**: All 22 laws injected into subagent context
- **Review-time**: Full audit during `/rb:review`

See [full registry](plugins/ruby-grape-rails/skills/iron-laws/references/canonical-registry.md) for details.

<!-- IRON_LAWS_END -->

## Commands Reference

### Workflow

| Command                  | Description                                                  |
| -----------------------  | ------------------------------------------------------------ |
| `/rb:full <feature>`     | Full autonomous cycle (plan, work, verify, review, compound) |
| `/rb:brainstorm <topic>` | Adaptive requirements gathering before planning              |
| `/rb:plan <input>`       | Create implementation plan with specialist agents            |
| `/rb:plan --existing`    | Enhance existing plan with deeper research                   |
| `/rb:work <plan-file>`   | Execute plan tasks with verification                         |
| `/rb:review [focus]`     | Multi-agent code review (4 parallel agents)                  |
| `/rb:compound`           | Capture solved problem as reusable knowledge                 |
| `/rb:triage`             | Interactive triage of review findings                        |
| `/rb:document`           | Generate YARD/RDoc, README, ADRs                             |
| `/rb:learn <lesson>`     | Capture lessons learned                                      |
| `/rb:brief <plan>`       | Interactive plan walkthrough                                 |
| `/rb:perf`               | Performance analysis with specialist agents                  |
| `/rb:pr-review`          | Address PR review comments                                   |
| `/rb:permissions`        | Analyze permission prompts and suggest safe settings entries |

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
| `/rb:compression-report` | Anonymized verify-output compression telemetry report (opt-in via `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1`) |
| `/rb:provenance-scan`    | Audit `.claude/` provenance sidecars; classifies each via the 4-state trust algorithm and writes a dated Markdown report |

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

## Agents (19)

| Agent                             | Model  | Memory  | Role                                         |
| --------------------------------- | ------ | ------- | -------------------------------------------- |
| **deep-bug-investigator**         | sonnet | --      | 4-track structured bug investigation         |
| **call-tracer**                   | sonnet | --      | Parallel call tree tracing                   |
| **security-analyzer**             | opus   | --      | OWASP vulnerability scanning                 |
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

After the orchestrator cleanup, no shipped agent uses `memory: project`.
The field remains supported as a future extension for pattern-analyst
agents that need cross-session continuity.

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
- Ruby >= 3.4 — required by plugin runtime hooks and the
  `compression-stats` end-user CLI under
  `plugins/ruby-grape-rails/bin/`. Stdlib only; no Bundler gems
  required at runtime.

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
- Agents: under 300 lines; prefer denylist-only `disallowedTools` for
  specialists, `tools:` allowlists only for intentionally narrow tool sets
- Markdown-only edits should pass `npm run lint:markdown`; `npm run lint`
  runs the full local lint/validation bundle

### Contributor prerequisites

Local contributor workflows require more than `npm ci` alone:

- `python3` `3.14+` for eval tooling and release checks
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
[`.claude/rules/eval-workflow.md`](.claude/rules/eval-workflow.md)
(auto-loaded for contributors). Use that file for the full command matrix
and caveats.

Common entrypoints:

- `make eval` or `npm run eval` for lint + injection check + changed surfaces
- `make eval-ci-deterministic` or `npm run eval:ci:deterministic` for the
  contributor CI gate (deterministic; used by GitHub CI)
- `make eval-tests` or `npm run eval:test` for the default contributor test
  path (`unittest` by default for deterministic cross-environment runs)
- `make eval-behavioral` or `npm run eval:behavioral` for LLM-based trigger
  routing tests (cache-only, runs offline if cache exists)
- `make eval-behavioral-verbose` / `npm run eval:behavioral:verbose` — same with
  verbose cache/score output
- `make eval-behavioral-fresh` / `npm run eval:behavioral:fresh` — ignore
  cache, re-run via the default provider (local Ollama `gemma4:26b-a4b-it-q8_0`).
  The npm script is a composite (`cmd1 && cmd2`), so
  `npm run ... -- --provider haiku`
  would append to the wrong target; `make` doesn't forward args either.
  To switch provider prefix with `RUBY_PLUGIN_EVAL_PROVIDER=haiku` or
  `RUBY_PLUGIN_EVAL_PROVIDER=apfel`; change the default Ollama model with
  `RUBY_PLUGIN_EVAL_OLLAMA_MODEL=gemma4:latest` (low-RAM fallback,
  10GB instead of 28GB) or any other Ollama tag; or
  call the module directly with
  `python3 -m lab.eval.behavioral_scorer --all --summary --provider haiku`
- `make eval-behavioral-fresh-verbose` / `npm run eval:behavioral:fresh:verbose`
  — fresh run with full prompt/response debug output
- `make eval-ablation` or `npm run eval:ablation` for matcher signal/noise
  classification (deterministic, no API calls)
- `make eval-neighbor` or `npm run eval:neighbor` for confusable-pair
  regression detection on changed skills (requires the active provider —
  local Ollama `gemma4:26b-a4b-it-q8_0` by default). `make` doesn't forward args;
  `npm run eval:neighbor -- --provider haiku` does (single-command script).
  For a cross-wrapper option prefix with `RUBY_PLUGIN_EVAL_PROVIDER=haiku`
  or `RUBY_PLUGIN_EVAL_PROVIDER=apfel`,
  or call the module directly with
  `python3 -m lab.eval.neighbor_regression --changed --provider haiku`
- `make eval-hygiene` or `npm run eval:hygiene` for trigger corpus
  contamination scanning
- contributor eval tooling requires `python3` 3.14+

Notes:

- `--include-untracked` is local-only for changed-mode exploration and is not
  part of `eval-ci-deterministic`
- `scripts/check-dynamic-injection.sh` expects git metadata for comparable
  tracked-file scans and now refuses broad non-git fallback scans
- local pre-commit checks staged Markdown (markdownlint), JSON validation,
  and shell syntax + shellcheck lint; CI is broader

### Docs-check and session analytics

Contributor-only maintenance tooling under `.claude/` now has two distinct
roles:

- `/docs-check` validates the plugin against the current cached Claude Code
  docs and should be treated as a docs-compatibility workflow, not a generic
  style lint
- `/cc-changelog` tracks Claude Code releases against plugin surfaces (hooks,
  agents, skills, config), classifying entries as BREAKING/OPPORTUNITY/RELEVANT
  FIX/DEPRECATION/INFO with cross-referenced impact; requires `jq` and `curl`
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
