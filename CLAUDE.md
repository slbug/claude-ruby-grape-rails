# Plugin Development Guide

Development documentation for the Ruby/Rails/Grape Claude Code plugin.

## Overview

This plugin provides **agentic workflow orchestration** with specialist agents and reference skills for Ruby/Rails/Grape development.

## Workflow Architecture

The plugin implements a **Plan → Work → Verify → Review → Compound** lifecycle:

```
/rb:plan → /rb:work → /rb:verify → /rb:review → /rb:compound
     │           │            │              │              │
     ↓           ↓            ↓              ↓              ↓
plans/{slug}/  (in namespace) (in namespace) (in namespace) solutions/
```

**Key principle**: Filesystem is the state machine. Each phase reads from previous phase's output. Solutions feed back into future cycles.

### Workflow Commands

| Command | Phase | Input | Output |
|---------|-------|-------|--------|
| `/rb:plan` | Planning | Feature description | `plans/{slug}/plan.md` |
| `/rb:plan --existing` | Enhancement | Plan file | Enhanced plan with research |
| `/rb:brief` | Understanding | Plan file | Interactive walkthrough (ephemeral) |
| `/rb:work` | Execution | Plan file | Updated checkboxes, `plans/{slug}/progress.md` |
| `/rb:verify` | Verification | Plan namespace | Verification results |
| `/rb:review` | Quality | Changed files | `reviews/{review-slug}.md` + `reviews/{agent-slug}/...` |
| `/rb:compound` | Knowledge | Solved problem | `solutions/{category}/{fix}.md` |
| `/rb:full` | All | Feature description | Complete cycle with compounding |

### Artifact Directories

Each plan owns its implementation-state artifacts in a namespace directory:

```
.claude/
├── plans/{slug}/              # Everything for ONE plan
│   ├── plan.md                # The plan itself
│   ├── research/              # Research agent output
│   ├── summaries/             # Context-supervisor compressed output
│   ├── progress.md            # Progress log
│   └── scratchpad.md          # Auto-written decisions, dead-ends, handoffs
├── audit/                     # Audit namespace (not plan-specific)
│   ├── reports/               # 5 specialist agent outputs
│   └── summaries/             # Supervisor compressed output
├── reviews/                   # Review artifacts (per-agent + consolidated)
├── skill-metrics/             # Skill effectiveness dashboards and recommendations
│   ├── dashboard-{date}.json  # Per-skill aggregate metrics
│   └── recommendations-{date}.md  # Improvement recommendations
└── solutions/{category}/      # Global compound knowledge (unchanged)
    ├── active-record-issues/
    ├── sidekiq-issues/
    └── ...
```

### Context Supervisor Pattern

Orchestrators that spawn multiple sub-agents use a generic
`context-supervisor` (haiku) to compress worker output before
synthesis. This prevents context exhaustion in the parent:

```
Orchestrator (thin coordinator)
  └─► context-supervisor reads N worker output files
      └─► writes summaries/consolidated.md
          └─► Orchestrator reads only the summary
```

Used by: planning-orchestrator, parallel-reviewer, audit skill, docs-validation-orchestrator.

## Structure

```
claude-ruby-grape-rails/
├── .claude-plugin/
│   └── marketplace.json
├── .claude/                         # Contributor tooling (NOT distributed)
│   ├── agents/
│   │   ├── rails-project-analyzer.md    # Analyze external codebases
│   │   ├── docs-validation-orchestrator.md  # Plugin docs compatibility
│   │   └── skill-effectiveness-analyzer.md  # Per-skill metrics analysis
│   ├── commands/
│   │   ├── psql-query.md
│   │   └── techdebt.md
│   └── skills/
│       ├── docs-check/              # /docs-check — validate against Claude Code docs
│       ├── session-scan/            # /session-scan — Tier 1 metrics
│       ├── session-deep-dive/       # /session-deep-dive — Tier 2 analysis
│       ├── session-trends/          # /session-trends — trend reporting
│       └── skill-monitor/           # /skill-monitor — skill effectiveness dashboards
├── scripts/
│   └── fetch-claude-docs.sh         # Download Claude Code docs for validation
├── plugins/
│   └── ruby-grape-rails/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/                  # 22 specialist agents
│       │   ├── workflow-orchestrator.md   # Full cycle coordination
│       │   ├── planning-orchestrator.md
│       │   ├── context-supervisor.md     # Generic output compressor (haiku)
│       │   └── ...
│       ├── hooks/
│       │   └── hooks.json           # Format, review-state, compaction, and failure hooks
│       └── skills/                  # 49 skills
│           ├── work/                # Execution phase
│           ├── full/                # Autonomous cycle
│           ├── plan/                # Planning + deepening (--existing)
│           ├── review/              # Findings-only review phase
│           ├── compound/            # Knowledge capture phase
│           ├── compound-docs/       # Solution documentation system
│           ├── investigate/
│           └── ...
├── CLAUDE.md
└── README.md
```

## Conventions

### Agents

Agents are specialist reviewers that analyze code without modifying it.

**Frontmatter:**

```yaml
---
name: my-agent
description: Description with "Use proactively when..." guidance
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit, NotebookEdit
permissionMode: bypassPermissions
model: sonnet
memory: project
skills:
  - relevant-skill
---
```

**Rules:**

- Use `sonnet` model by default (Sonnet 4.6 achieves near-opus quality at lower cost)
- Use `opus` for primary workflow orchestrators and security-critical agents only
- Use `sonnet` for secondary orchestrators (investigation, tracing) and judgment-heavy tasks
- Use `haiku` for mechanical tasks: compression, verification, dependency analysis
- Review agents are **read-only** (`disallowedTools: Write, Edit, NotebookEdit`)
- Use `permissionMode: bypassPermissions` for all agents — **required for local development with `--plugin-dir`**
  - **Local dev (`--plugin-dir`)**: Field is honored, prevents "Bash command permission check failed" errors
  - **Marketplace install**: Claude Code **ignores** `permissionMode` on plugin agents — agents fall back to session default permissions
    - **Workaround**: Copy agents to `~/.claude/agents/` or add `permissions.allow` rules to `settings.json`
- Use `memory: project` for agents that benefit from cross-session learning (orchestrators, pattern analysts).
  Note: `memory` auto-enables Read, Write, Edit — only add to agents that already have Write access
- Preload relevant skills via `skills:` field
- Keep under 300 lines

### Skills

Skills provide domain knowledge with progressive disclosure.

**Structure:**

```
skills/{name}/
├── SKILL.md           # ~100 lines max
└── references/        # Detailed content
    └── *.md
```

**Rules:**

- SKILL.md: ~100 lines max (~500 tokens)
- Include "Iron Laws" section for critical rules
- Move detailed examples to `references/`
- No `triggers:` field (use `description` for auto-loading)

**Colon in Skill Names (Compatibility Risk):**

The plugin uses colons in skill names (e.g., `rb:plan`, `rb:work`) for namespacing.
Per current Claude Code docs, skill names should use "lowercase letters, numbers, and hyphens only."
The colon pattern works in practice but is a compatibility watch item.

- **Current behavior**: Works correctly in plugin context
- **Risk**: Future strict enforcement of character restrictions
- **Mitigation**: If restrictions tighten, migrate to internal hyphen names with external aliases

### Workflow Skills

Workflow skills (plan, work, review, compound, full) have special structure:

- Define clear input/output artifacts
- Reference other workflow phases
- Include integration diagram showing position in cycle
- Document state transitions

### Compound Knowledge Skills

The compound system captures solved problems as searchable institutional knowledge:

- `compound-docs` — Schema and reference for solution documentation
- `compound` (`/rb:compound`) — Post-fix knowledge capture skill
Solution docs use YAML frontmatter (see `compound-docs/references/schema.md`).

### Hooks

Defined in `hooks/hooks.json`:

```json
{
  "hooks": {
    "PreToolUse": [...],            // Block dangerous ops (rails db:drop, force push, RAILS_ENV=production)
    "PostToolUse": [...],          // Format + Iron Law verify + security + progress + plan STOP + debug stmt
    "PostToolUseFailure": [...],   // Ruby failure hints + error critic for bundle commands
    "SubagentStart": [...],        // Iron Laws injection into all subagents
    "SessionStart": [...],         // Setup dirs + runtime tool detection + resume detection
    "PreCompact": [...],           // Re-inject workflow rules before compaction
    "PostCompact": [...],          // Advise re-reading active plan artifacts after compaction
    "Stop": [...],                 // Warn if uncompleted tasks
    "StopFailure": [...]           // Persist API failure context for resume flows
  }
}
```

**Current hooks:**

- `PreToolUse` (Bash): Block destructive operations (`rails db:drop`, `git push --force`, `RAILS_ENV=production`) before execution
- `PostToolUse` (Edit|MultiEdit|Write): Multiple scripts run in sequence:
  - `format-ruby.sh`: Auto `bundle exec standardrb` or `bundle exec rubocop -a`
  - `verify-ruby.sh`: Syntax check via `ruby -c <file>` (catches broken Ruby before formatting)
  - `iron-law-verifier.sh`: **Programmatic Iron Law verification** (scans code for violations)
  - `security-reminder.sh`: Security Iron Laws for auth files
  - `log-progress.sh`: Async progress logging
  - `plan-stop-reminder.sh`: Plan STOP reminder on plan.md write
  - `debug-statement-warning.sh`: Detect debug statements (`puts`, `binding.pry`, etc.) in production .rb files
  - `secret-scan.sh`: Secret scanning with hook-mode gating
- `PostToolUseFailure` (Bash): Ruby-specific debugging hints when bundle exec fails,
  **error critic** that detects repeated failures and escalates to structured analysis (both via `additionalContext`)
- `SubagentStart`: Inject all Iron Laws into every spawned subagent via `additionalContext` (addresses zero skill auto-loading gap)
- `PreCompact`: Re-inject workflow rules (plan/work/full) before compaction via JSON `systemMessage`,
  including `.claude/ACTIVE_PLAN` resolution for context-aware compaction
- `PostCompact`: Advise Claude which active plan artifacts to re-read after
  compaction when unchecked tasks still exist
- `SessionStart` (all): Setup `.claude/` directories + consolidated runtime detection
  - `detect-runtime.sh`: Detect Ruby/Rails version, stack gems, Tidewave, RTK, betterleaks, and active hook mode
- `SessionStart` (startup|resume only): Scratchpad check + resume workflow detection + workflow hints
- `Stop`: Warn if plans have unchecked tasks
- `StopFailure`: Append normalized API-failure context to the active plan scratchpad for better resume continuity

**Hook modes:**

- `default` (implicit): keep startup quieter, scan normal written text/source/config files, skip obvious binary/media files, and avoid recent-change fallback scans
- `strict`: scan every written file and broaden secret scanning to recent changes when no specific file path is available
- Configure via `${REPO_ROOT}/.claude/ruby-plugin-hook-mode` or `RUBY_PLUGIN_HOOK_MODE=strict`

**Active Plan Infrastructure:**

Workflow convention with hook-level detection support:

- `active-plan-lib.sh` / `active-plan-marker.sh`: Manage `.claude/ACTIVE_PLAN` marker file tracking the current plan
  - **Set by:** `/rb:plan` (after creating plan)
  - **Cleared by:** `/rb:work` (when all tasks complete)
  - **Read by:** `precompact-rules.sh` (phase detection), `check-scratchpad.sh` (resume detection), `log-progress.sh` (progress tracking)
  - `/rb:full` orchestrates the lifecycle via plan/work phases

**Note:** Marker lifecycle is enforced at the skill level, not via hooks. Only plan sets it, only work clears it.

**Hook output patterns (important for contributors):**

- `PostToolUse` stdout is **verbose-mode only** — use `exit 2` + stderr to feed messages to Claude
- `PreCompact` has **no stdout context injection** — use JSON `systemMessage`
- `SessionStart` stdout IS added to Claude's context (one of two exceptions along with `UserPromptSubmit`)
- `SubagentStart` uses `hookSpecificOutput.additionalContext` to inject context into subagents
- `PostToolUseFailure` uses `hookSpecificOutput.additionalContext` for debugging hints

### Runtime Tooling Integration

The plugin integrates with Tidewave Rails for runtime operations:

- `/rb:runtime execute` - Ruby code execution via `mcp__tidewave__project_eval`
- `/rb:runtime query` - SQL execution via `mcp__tidewave__execute_sql_query`
- `/rb:runtime docs` - Documentation via `mcp__tidewave__get_docs`
- `/rb:runtime logs` - Log reading via `mcp__tidewave__get_logs`
- Tidewave gem detection via `Gemfile` parsing

**Note:** Runtime features require Tidewave Rails gem (`bundle add tidewave --group development`) and Tidewave MCP tool access.

## Development

### Testing locally

```bash
# Option A: Test local working-tree changes directly
claude --plugin-dir ./plugins/ruby-grape-rails

# Option B: Validate marketplace install flow
# Note: marketplace.json now uses git-subdir source, so this installs the
# published GitHub-backed plugin source, not your uncommitted working tree.
/plugin marketplace add .
/plugin install ruby-grape-rails
```

### Testing workflow

```bash
# Test individual workflow phase
/rb:plan Test feature for workflow
# Check: .claude/plans/ has checkbox plan

/rb:work .claude/plans/test-feature/plan.md
# Check: Checkboxes update, progress logged in plans/test-feature/progress.md
```

### Adding new agent

1. Create `plugins/ruby-grape-rails/agents/{name}.md`
2. Add frontmatter with all required fields
3. Keep under 300 lines

### Adding new skill

1. Create `plugins/ruby-grape-rails/skills/{name}/SKILL.md` (~100 lines)
2. Create `references/` with detailed content
3. For workflow skills, document integration with cycle

### Setup

```bash
npm install  # Pre-commit hooks + linting
```

### Linting

```bash
npm run lint       # Check all markdown
npm run lint:fix   # Auto-fix issues
```

### Validation

```bash
# Validate plugin structure and manifest
claude plugin validate plugins/ruby-grape-rails

# Should pass without errors before committing changes
```

## Size Guidelines

| Component | Target | Hard Limit | Notes |
|-----------|--------|------------|-------|
| SKILL.md (reference) | ~100 | ~150 | Iron Laws + quick patterns |
| SKILL.md (command) | ~100 | ~185 | Command skills need complete execution flow inline |
| references/*.md | ~350 | ~350 | Detailed patterns |
| agents (specialist) | ~300 | ~365 | Design guidance beyond preloaded skill patterns |
| agents (orchestrator) | ~300 | ~535 | Subagent prompts + flow control must be inline |

### Why orchestrators and command skills exceed targets

Even with `permissionMode: bypassPermissions`, plugin files live in `~/.claude/plugins/cache/` — outside the project.
This means agents **cannot reliably read** skill `references/*.md` at runtime.

Content must be inline (in agent prompt or preloaded SKILL.md) to be available:

| Location | Auto-available? | Reliable? |
|----------|----------------|-----------|
| Agent system prompt | Yes | Yes |
| Preloaded skill SKILL.md (`skills:` field) | Yes | Yes |
| Skill `references/*.md` | No — needs Read call | **No** — permission prompt |

Orchestrators embed subagent prompts (~80 lines × 4 agents = 320 lines minimum).
Command skills drive execution — removing a step breaks the workflow.
Only trim when content is purely informational and not execution-critical.

## Checklist

### New agent

- [ ] Frontmatter complete
- [ ] `disallowedTools: Write, Edit, NotebookEdit` for review agents
- [ ] `Write` allowed for agents that output reports (e.g., research agents, context-supervisor)
- [ ] `permissionMode: bypassPermissions`
- [ ] Skills preloaded
- [ ] Under target (300 lines), hard limit only if justified by inline subagent prompts

### New skill

- [ ] SKILL.md under target (~100 lines), hard limit for command skills (~185)
- [ ] "Iron Laws" section
- [ ] `references/` for details
- [ ] No `triggers:` field

### New workflow skill

- [ ] Clear input/output artifacts
- [ ] Integration diagram with cycle position
- [ ] State transitions documented
- [ ] References previous/next phases

### Release

- [ ] All markdown passes linting
- [ ] Version bumped in `plugins/ruby-grape-rails/.claude-plugin/plugin.json`
- [ ] `CHANGELOG.md` updated with all changes under new version heading
- [ ] README updated
- [ ] `/rb:intro` tutorial content still accurate (commands, agents, features)

### Versioning

The plugin uses [semantic versioning](https://semver.org/):

- **MAJOR**: Breaking changes (workflow redesign, removed commands)
- **MINOR**: New features (new hooks, skills, agents, commands)
- **PATCH**: Bug fixes, doc updates, description improvements

**IMPORTANT**: Users only receive updates when the version in `plugin.json`
changes. If you push code without bumping the version, existing users won't
see the changes due to caching.

When making changes, ALWAYS update `CHANGELOG.md` under the current
`[Unreleased]` section. Use categories: Added, Changed, Fixed, Removed.
On release, rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD` and bump
`plugin.json`.

## Backlog

### Potential New Agents

1. **Ruby concurrency advisor** — Thread-safety and concurrency specialist
   - **Scope**: Concurrent Ruby, Thread safety, Ractor usage, Sidekiq concurrency patterns
   - **Status**: Consider for v2.0

2. **Hotwire architect** — Complex Hotwire/Turbo architecture specialist
   - **Scope**: Nested frames, Stimulus controller architecture, cable connections
   - **Current coverage**: `rails-architect` agent covers general Rails patterns
   - **Status**: Consider if `rails-architect` proves too general for complex Hotwire apps

---

# Claude Code Behavioral Instructions

**CRITICAL**: These instructions OVERRIDE default behavior for Ruby/Rails/Grape projects in this codebase.

## Automatic Skill Loading

When working on Ruby/Rails/Grape code, ALWAYS load relevant skills based on file context:

| File Pattern | Auto-Load Skills | Check References |
|--------------|------------------|------------------|
| `*_controller.rb`, `*_helper.rb` | `rails-contexts`, `rails-idioms` | `references/routing-patterns.md` |
| `*job.rb`, `app/jobs/*` | `sidekiq` or `rails-idioms` | `references/job-patterns.md` |
| `db/migrate/*`, `*_migration.rb`, `*model.rb` | `active-record-patterns`, `safe-migrations` | `references/migrations.md`, `references/queries.md` |
| `*auth*`, `*session*`, `*password*` | `security` | `references/authentication.md`, `references/authorization.md` |
| `*_spec.rb`, `*_test.rb`, `*factory*`, `*fixtures*` | `testing` | `references/rspec-patterns.md`, `references/factory-patterns.md` |
| `config/environments/production.rb`, `Dockerfile`, `fly.toml` | `deploy` | `references/docker-config.md` |
| `app/services/*`, `app/interactors/*`, `lib/**/*.rb` | `rails-contexts`, `ruby-contexts` | `references/context-patterns.md` |
| `lib/tasks/*.rake` | `ruby-idioms` | `references/rake-tasks.md` |
| `*_component.rb`, `app/components/*` | `hotwire-patterns` | `references/components.md` |
| `app/api/**/*.rb`, `*_api.rb`, `app/apis/**/*.rb` | `grape-idioms` | `references/grape-patterns.md` |
| `*.rb` | `ruby-idioms` | Always check Iron Laws |

**Note on job files**: Load `rails-idioms` instead of `sidekiq` when `config/environments/production.rb` contains `solid_queue` (Rails 8+ default).

### Skill Loading Behavior

1. When opening/editing a file matching patterns above, silently load the skill
2. Apply Iron Laws from loaded skills as validation rules
3. If code violates Iron Law, **stop and explain** before proceeding
4. Reference detailed docs from `references/` when making implementation decisions

## Workflow Routing (Proactive)

When the user's FIRST message describes work without specifying a `/rb:` command:

1. Detect intent from their description (see `intent-detection` skill for routing table)
2. If multi-step workflow detected, suggest the appropriate command
3. Format: "This looks like [intent]. Want me to run `/rb:[command]`, or should I handle it directly?"
4. For trivial tasks (typos, single-line fixes, config changes): skip suggestion, just do it
5. If user already specified a command: follow it, don't re-suggest
6. NEVER block the user — suggestion only, one attempt max

### Debugging Loop Detection

The `error-critic.sh` hook automatically detects repeated bundle/rails failures and
escalates from generic hints (attempt 1) to structured critic analysis
(attempt 3+). It tracks failure count per command and consolidates error
history. This implements the Critic→Refiner pattern from AutoHarness
(Lou et al., 2026): structured error consolidation before retry prevents
debugging loops more effectively than unstructured retry.

If the hook hasn't triggered (e.g., non-bundle failures), manually detect:
when 3+ consecutive Bash commands are `bundle exec` or `rails` with failures,
suggest: "Looks like a debugging loop. Want me to run `/rb:investigate` for structured analysis?"

### Hotwire Bug Detection via Runtime Context

When the user's message contains runtime context describing a broken form, missing element, or UI issue — proactively suggest:
"This looks like a Hotwire/Stimulus bug. Want me to run `/rb:investigate` for structured root-cause analysis?"

### Custom RAILS_ENV Awareness

Some projects use non-standard Rails environments (e.g., `RAILS_ENV=staging` or `RAILS_ENV=ci`). When you see:

- `config/environments/staging.rb` or other non-standard env config files
- `RAILS_ENV=` in shell scripts or CI configs
- User running `RAILS_ENV=<custom> bundle exec`

Then use that RAILS_ENV for ALL Rails commands on those files. Do NOT use default RAILS_ENV for code that only works under the custom env.

### Scoped Format and Compile Checks

When running `bundle exec standardrb` or `bundle exec rubocop`, **always scope to the files you changed**
when possible. If a full-project check fails on files you didn't edit, report it as pre-existing
and continue — do NOT waste time debugging unrelated format failures.

### Sibling File Check

When fixing a bug in a file that has named variants (e.g., `seller_account/form.rb`,
`buyer_account/form.rb`, `occupier_account/form.rb`), proactively grep for all sibling files and
check if the same bug exists in each variant. Do this BEFORE implementing the fix, not after.

<!-- IRON_LAWS_START -->

<!-- GENERATED FROM iron-laws.yml — DO NOT EDIT -->

## Iron Laws Enforcement (NON-NEGOTIABLE)

These rules are NEVER violated. If code would violate them, **STOP and explain** before proceeding:

### Active Record Iron Laws

1. **Decimal for Money** — NEVER use float for money — use decimal or integer (cents)
2. **Parameterized Queries** — ALWAYS use parameterized queries — never interpolate user input into SQL strings
3. **Eager Loading** — USE includes/preload for associations — avoids N+1 queries
4. **Commit-Safe Enqueueing in Active Record** — IN Active Record code, use after_commit not after_save when enqueueing jobs that depend on committed data
5. **Transaction Boundaries** — WRAP multi-step operations in transactions — use ActiveRecord::Base.transaction
6. **No Validation Bypass** — NO update_columns, update_column, or save(validate: false) in normal flows
7. **No default_scope** — NO default_scope — use explicit named scopes only

### Sidekiq Iron Laws

8. **Idempotent Jobs** — Jobs MUST be idempotent — safe to retry
9. **JSON-Safe Arguments** — Args use JSON-safe types only — no symbols, no Ruby objects, no procs
10. **No ORM Objects in Args** — NEVER store ORM objects in args — store IDs, not records
11. **Commit-Safe Enqueueing** — ALWAYS enqueue jobs after commit using the active ORM or transaction hook — not after_save or inline before commit

### Security Iron Laws

12. **No Eval** — NO eval with user input — code injection vulnerability
13. **Explicit Authorization** — AUTHORIZE in EVERY controller action — do not trust before_action alone
14. **No Unsafe HTML** — NEVER use html_safe or raw with untrusted content — XSS vulnerability
15. **No SQL Concatenation** — NO SQL string concatenation — always use parameterized queries

### Ruby Iron Laws

16. **method_missing Requires respond_to_missing?** — NO method_missing without respond_to_missing? — breaks introspection
17. **Supervise Background Processes** — SUPERVISE ALL BACKGROUND PROCESSES — use proper process managers in production
18. **Rescue StandardError** — DON'T RESCUE Exception — only rescue StandardError or specific classes

### Hotwire/Turbo Iron Laws

19. **No DB Queries in Turbo Streams** — NEVER query DB in Turbo Stream responses — pre-compute everything before broadcast
20. **Use turbo_frame_tag** — ALWAYS use turbo_frame_tag for partial updates — prevents full page reloads

### Verification Iron Laws

21. **Verify Before Claiming Done** — VERIFY BEFORE CLAIMING DONE — never say 'should work' or 'this fixes it.' Run bundle exec rspec or bin/rails test and show the result

### Violation Response

When detecting a potential Iron Law violation:

```
STOP: This code would violate Iron Law [number]: [description]

What you wrote:
[problematic code]

Correct pattern:
[fixed code]

Should I apply this fix?
```

<!-- IRON_LAWS_END -->

## Framework Detection

### Sequel vs Active Record Detection

If the project uses Sequel (detected by `Sequel::Model` or `DB[:table]`):

1. **Warn**: "This project uses Sequel. My Active Record-specific patterns may not apply."
2. **Suggest**: "For Sequel-specific guidance, consult Sequel documentation."
3. **Skip**: Don't apply Active Record Iron Laws to Sequel models

### Rails Version Detection

Check `Gemfile.lock` or `config/application.rb` for Rails version:

- **Rails 8.x+**: Modern defaults, Solid Queue recommended
- **Rails 7.x**: Standard patterns apply
- **Rails 6.x**: May need compatibility considerations

## Greenfield Project Detection

If project has <20 `.rb` files (new project):

1. **Use simpler planning** (no parallel agents needed)
2. **Suggest initial setup**: StandardRB, RSpec, test factories

## Reference Auto-Loading

When working on code, automatically consult relevant reference documentation before implementing.

### Auto-Load Rules

| File/Code Pattern | Skill | References to Consult |
|-------------------|-------|----------------------|
| `*_controller.rb` | rails-contexts, rails-idioms | routing-patterns.md |
| `*_controller.rb` + JSON | rails-contexts | json-api-patterns.md |
| `app/services/*`, `app/interactors/*`, `lib/**/*.rb` | rails-contexts, ruby-contexts | context-patterns.md |
| `db/migrate/*` | active-record-patterns, safe-migrations | migrations.md |
| `class.*ApplicationRecord` | active-record-patterns | validations.md |
| `scope :`, `where(`, `joins(` | active-record-patterns | queries.md |
| `app/jobs/*`, `*job.rb` | sidekiq or rails-idioms | job-patterns.md |
| `include Sidekiq::Job` | sidekiq | job-patterns.md, queue-config.md |
| `*auth*`, `*session*` | security | authentication.md, authorization.md |
| `*_spec.rb` | testing | rspec-patterns.md |
| `spec/factories/*` | testing | factory-patterns.md |
| `spec/system/*` | testing | system-testing.md |
| `app/views/*` | hotwire-patterns | components.md, forms-uploads.md |
| `turbo_frame_tag` | hotwire-patterns | async-streams.md |
| `data-controller` | hotwire-patterns | js-interop.md |
| `Dockerfile`, `fly.toml` | deploy | docker-config.md, flyio-config.md |
| `lib/tasks/*.rake` | ruby-idioms | rake-tasks.md |
| `app/api/**/*.rb`, `*_api.rb`, `app/apis/**/*.rb` | grape-idioms | grape-patterns.md |

### Consultation Behavior

1. **Before implementing**, read relevant reference for correct pattern
2. **Silently apply** patterns (don't narrate unless complex)
3. **Check Iron Laws** from skill before and after implementation
4. **Security code ALWAYS gets reference consultation** (authentication.md, authorization.md)

## Command Suggestions

| User Intent | Command |
|-------------|---------|
| New to the plugin | `/rb:intro` |
| Bug fix, debug | `/rb:investigate` |
| Small UI fix, CSS tweak, config change | `/rb:quick` |
| Small change (<50 lines) | `/rb:quick` |
| New feature (clear scope) | `/rb:plan` then `/rb:work` |
| Understand a plan | `/rb:brief` |
| Enhance existing plan | `/rb:plan --existing` |
| Large feature (new domain) | `/rb:full` |
| Review code | `/rb:review` |
| Triage review findings | `/rb:triage` |
| Capture solved problem | `/rb:compound` |
| Run checks | `/rb:verify` |
| Research topic | `/rb:research` |
| Evaluate a Ruby gem | `/rb:research --library` |
| Resume work | `/rb:work --continue` |
| N+1 queries | `/rb:n1-check` |
| Request/state audit | `/rb:state-audit` |
| PR review comments | `/rb:pr-review` |
| Challenge/grill me | `/rb:challenge` |
| Constraint debugging | `/rb:constraint-debug` |
| Documentation generation | `/rb:document` |
| Examples and patterns | `/rb:examples` |
| Initialize plugin | `/rb:init` |
| Learn from fixes | `/rb:learn` |
| Runtime tooling | `/rb:runtime` |
| Secrets scanning | `/rb:secrets` |
| Performance analysis | `/rb:perf` |
| Project health | `/rb:audit` |
| Scan sessions for metrics | `/session-scan` |
| Deep-analyze sessions | `/session-deep-dive` |
| View session trends | `/session-trends` |
| Monitor skill effectiveness | `/skill-monitor` |
| Validate plugin against docs | `/docs-check` |

**Workflow Commands**: `/rb:plan` -> `/rb:brief` (optional) -> `/rb:plan --existing` (optional) -> `/rb:work` -> `/rb:brief` (optional) -> `/rb:review` -> `/rb:triage` (optional) -> `/rb:compound`

**Review → Follow-up Plan**: After `/rb:review`, if findings reveal scope gaps or missing coverage, use `/rb:triage .claude/reviews/{review-slug}.md` to turn selected findings into `.claude/plans/{slug}/plan.md`.

**Standalone**: `/rb:quick`, `/rb:full`, `/rb:investigate`, `/rb:verify`, `/rb:research`

**Analysis**: `/rb:n1-check`, `/rb:state-audit`, `/rb:boundaries`, `/rb:trace`, `/rb:techdebt`

**Session Analytics (dev-only, requires ccrider MCP)**: `/session-scan`, `/session-deep-dive`, `/session-trends`

**Skill Monitoring (dev-only)**: `/skill-monitor` — per-skill effectiveness dashboard and improvement recommendations

**Plugin Maintenance (dev-only)**: `/docs-check` — validate plugin against latest Claude Code documentation

## Workflow Patterns (from Claude Code team)

### Challenge Mode

When I say "grill me" or "challenge this":

- Review my changes as a senior Ruby engineer would
- Check for: N+1 queries, missing error handling, anti-patterns, untested paths
- Diff behavior between `main` and current branch
- Don't approve until issues are addressed

### Elegance Reset

When I say "make it elegant" or "knowing everything you know now":

- Scrap the current approach
- Implement the idiomatic Ruby solution
- Prefer composition over inheritance
- Prefer small, focused methods over large ones
- Use proper design patterns where applicable
- Follow Rails conventions

### Auto-Fix Patterns

When I say:

- "fix CI" → Run `bundle exec rubocop -a && bundle exec rspec` and fix all failures
- "fix it" → Look at the error/bug context and autonomously fix without asking questions
- "fix rubocop" → Run `bundle exec rubocop -a` and fix all auto-correctable issues

### Learn From Mistakes

After ANY correction I make:

- Ask: "Should I update CLAUDE.md so this doesn't happen again?"
- If yes, add a concise rule preventing the specific mistake
- Keep rules actionable: "Do NOT X — instead Y"

### Intro Tutorial Maintenance

When adding, removing, or renaming commands/skills/agents, check if
`plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md` needs updating.
The tutorial is new users' first impression — stale command references erode trust.
Quick check: does the cheat sheet in Section 4 still match reality?

---

## Claude Code Features Under Evaluation

Based on `/docs-check` validation against latest Claude Code docs, the following features are available but not yet adopted:

### Agent Features (Adopted)

- [x] **`effort` field** — Added to all 22 agents for cost optimization:
  - `low`: web-researcher, context-supervisor, verification-runner (mechanical tasks)
  - `medium`: dependency-analyzer, call-tracer, rails-patterns-analyst, rails-architect, ruby-reviewer,
    testing-reviewer, sidekiq-specialist, ruby-runtime-advisor, deployment-validator, iron-law-judge,
    data-integrity-reviewer, migration-safety-reviewer, active-record-schema-designer,
    deep-bug-investigator, ruby-gem-researcher (specialist analysis)
  - `high`: planning-orchestrator, workflow-orchestrator, security-analyzer, parallel-reviewer (orchestrators, security-critical)

### Agent Features (Under Evaluation)

- [ ] **`isolation: "worktree"`** — Run agents in isolated git worktrees for parallel execution.
  Potential use: `verification-runner` or parallel review tasks that modify files.

### Hook Features (Adopted)

- [x] **`PostCompact` event** — Added to surface active-plan recovery reminders after compaction
- [x] **`StopFailure` event** — Added to persist API-failure context into plan scratchpads for resume flows

### Hook Features (Under Evaluation)

- [ ] **`http` hook type** — Could enable external telemetry/logging endpoints
- [ ] **`SubagentStop` event** — Could track specialist agent completion metrics
- [ ] **`SessionEnd` event** — Could clean up temporary files
- [ ] **`environment` field** — Could simplify hook script configuration

### Skill Features (Adopted)

- [x] **Skill `effort` field** — Added across all shipped skills for lower-cost simple flows and higher-effort orchestration where needed
- [x] **`${CLAUDE_SKILL_DIR}` variable** — Adopted selectively in workflow skills where explicit local reference paths improve reliability across install/cache contexts

### Skill Features (Under Evaluation)

### Plugin Features (Under Evaluation)

- [ ] **`${CLAUDE_PLUGIN_DATA}` directory** — Could cache plugin dependencies across updates
- [ ] **`settings.json` at plugin root** — Plugin-level default settings. Currently only `agent` key supported.
- [ ] **`.lsp.json` LSP server configuration** — Could bundle Ruby LSP (ruby-lsp/solargraph) for code intelligence.
  Requires users to install LSP binary separately.

### Adoption Criteria

Features are adopted when:

1. They solve a concrete problem (not just "nice to have")
2. They don't add complexity without clear benefit
3. They're tested in development environment first
4. They're documented in this section when adopted
