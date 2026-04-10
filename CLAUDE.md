# Plugin Development Guide

Development documentation for the Ruby/Rails/Grape Claude Code plugin.

Contributor tooling and shipped hook workflows are validated on macOS, Linux,
and WSL. Native Windows is not currently supported.

## Overview

This plugin provides **agentic workflow orchestration** with specialist agents and reference skills for Ruby/Rails/Grape development.

Current Plugin Posture:

- **Lean read-only agents**: shipped read-only specialists use
  `omitClaudeMd: true` so they skip contributor-only repo guidance at runtime
- **Fast first-turn context**: SessionStart writes a quick runtime snapshot,
  then refreshes slower probes asynchronously in the background
- **Structured workflow memory**: active plans keep canonical scratchpads for
  dead ends, decisions, hypotheses, and handoffs
- **Targeted post-edit routing**: generic safety hooks stay broad, while
  Ruby-ish formatting / Iron Law / syntax / debug checks route through a single
  delegated `rubyish-post-edit.sh` fan-out

## Workflow Architecture

The plugin supports an optional **Brainstorm** discovery step before the core **Plan → Work → Verify → Review → Compound** lifecycle:

```
/rb:brainstorm (optional) → /rb:plan → /rb:work → /rb:verify → /rb:review → /rb:compound
                                │           │            │              │              │
                                ↓           ↓            ↓              ↓              ↓
                   .claude/plans/{slug}/  (namespace)  (namespace)  (namespace)  .claude/solutions/
```

**Key principle**: Filesystem is the state machine. Each phase reads from previous phase's output. Solutions feed back into future cycles.

### Workflow Commands

| Command | Phase | Input | Output |
|---------|-------|-------|--------|
| `/rb:brainstorm` | Discovery | Topic or feature idea | `.claude/plans/{slug}/interview.md` |
| `/rb:plan` | Planning | Feature description | `.claude/plans/{slug}/plan.md` |
| `/rb:plan --existing` | Enhancement | Plan file | Enhanced plan with research |
| `/rb:brief` | Understanding | Plan file | Interactive walkthrough (ephemeral) |
| `/rb:work` | Execution | Plan file | Updated checkboxes, `.claude/plans/{slug}/progress.md` |
| `/rb:verify` | Verification | Plan namespace | Verification results |
| `/rb:review` | Quality | Changed files | `.claude/reviews/{review-slug}.md` + `.claude/reviews/{agent-slug}/...` |
| `/rb:compound` | Knowledge | Solved problem | `.claude/solutions/{category}/{fix}.md` |
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
│   └── scratchpad.md          # Structured dead ends, decisions, hypotheses, handoffs
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
│   │   ├── docs-validation-orchestrator.md  # Plugin docs compatibility
│   │   └── skill-effectiveness-analyzer.md  # Per-skill metrics analysis
│   └── skills/
│       ├── docs-check/              # /docs-check — validate against cached Claude Code docs
│       ├── plugin-dev-workflow/     # Contributor workflow for this repo
│       ├── session-scan/            # /session-scan — exploratory Tier 1 metrics
│       ├── session-deep-dive/       # /session-deep-dive — transcript review
│       ├── session-trends/          # /session-trends — provider-scoped trend reporting
│       └── skill-monitor/           # /skill-monitor — observational dashboards
├── scripts/
│   ├── fetch-claude-docs.sh         # Download Claude Code docs for validation
│   ├── check-dynamic-injection.sh   # Block tracked docs/config from inline shell injection placeholders
│   ├── run-eval-tests.sh            # Contributor eval test entrypoint
│   ├── generate-iron-law-content.rb
│   ├── generate-iron-law-outputs.sh
│   └── ...
├── plugins/
│   └── ruby-grape-rails/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/                  # 23 specialist agents
│       │   ├── workflow-orchestrator.md   # Full cycle coordination
│       │   ├── planning-orchestrator.md
│       │   ├── context-supervisor.md     # Generic output compressor (haiku)
│       │   └── ...
│       ├── bin/                      # Plugin executables (added to Bash tool PATH)
│       │   ├── detect-stack         # Ruby stack/package detection
│       │   └── extract-permissions  # Session permission extraction
│       ├── hooks/
│       │   └── hooks.json           # Format, review-state, compaction, and failure hooks
│       └── skills/                  # 51 skills
│           ├── work/                # Execution phase
│           ├── full/                # Autonomous cycle
│           ├── plan/                # Planning + deepening (--existing)
│           ├── review/              # Findings-only review phase
│           ├── compound/            # Knowledge capture phase
│           ├── compound-docs/       # Solution documentation system
│           ├── investigate/
│           └── ...
├── lab/
│   └── eval/                        # Contributor-only deterministic eval tooling
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
- Review agents write their own artifacts but must not edit project code
  (`disallowedTools: Edit, NotebookEdit`)
- Do **not** rely on `permissionMode` in shipped plugin agents
  - **Marketplace install**: Claude Code ignores `permissionMode` on plugin agents
  - **Workaround**: document `permissions.allow` rules in `.claude/settings.json` for required tools such as `Bash(bundle *)`, `Bash(rails *)`, `Bash(rake *)`, `Read(*)`, `Grep(*)`, and `Glob(*)`
  - **Local dev (`--plugin-dir`)**: you may still experiment with `permissionMode` while iterating locally, but do not ship it in plugin agent frontmatter
- Use `memory: project` for agents that benefit from cross-session learning (orchestrators, pattern analysts).
  Note: `memory` auto-enables Read, Write, Edit — only add to agents that already have Write access
- Preload relevant skills via `skills:` field
- Prefer denylist-only tool access over `tools:` allowlists. This follows the
  built-in agent pattern (Explore, Plan, Verification) — agents inherit all
  tools implicitly and Write works reliably in foreground spawns.
  - All denylist specialists also block `Agent, EnterWorktree, ExitWorktree,
    Skill` — these aren't covered by hooks or shellfirm. Bash stays available
    because hooks (`block-dangerous-ops.sh`) and shellfirm guard shell commands.
  - Artifact-writing agents: `disallowedTools: Edit, NotebookEdit, Agent,
    EnterWorktree, ExitWorktree, Skill`
  - Conversation-only agents: add `Write` to the above
  - `parallel-reviewer` keeps `Agent` (spawns sub-reviewers) but blocks the rest
  - `tools:` allowlists only for agents with intentionally narrow tool sets
    (web-researcher, output-verifier, ruby-gem-researcher)
- Add `omitClaudeMd: true` for shipped specialist agents that do not need
  contributor-only `CLAUDE.md` guidance at runtime. Iron Laws still arrive
  through `SubagentStart`. This applies to both denylist-only agents and
  allowlist agents — the criterion is whether the agent needs repo conventions,
  not whether it has Write access.
- Target under 300 lines when practical
- Keep agent descriptions at `<= 250` characters so Claude does not silently
  truncate them in the internal skill/agent listing context

### Skills

Skills provide domain knowledge with progressive disclosure.

**Structure:**

```
skills/{name}/
├── SKILL.md           # prefer ~100-200 lines; move bulky examples to references/
└── references/        # Detailed content
    └── *.md
```

**Rules:**

- SKILL.md: prefer ~100-200 lines for new skills when practical; larger
  framework/workflow skills are acceptable when further splitting would make
  routing or navigation worse
- Include "Iron Laws" section for critical rules
- Move detailed examples to `references/`
- No `triggers:` field (use `description` for auto-loading)
- Keep skill descriptions at `<= 250` characters. Longer descriptions are
  silently truncated by Claude's listing budget and hurt routing quality.
- For plugin-wide executables in `bin/`, use explicit
  `${CLAUDE_PLUGIN_ROOT}/bin/<cmd>` in skill text when the skill also
  references `${CLAUDE_SKILL_DIR}`. Bare command names are PATH-resolved
  but can be conflated with skill-local files by the model.

**Colon in Skill Names (Documented Behavior Divergence):**

The plugin uses colons in skill names (e.g., `rb:plan`, `rb:work`) for namespacing.
The skills docs still say names should use "lowercase letters, numbers, and hyphens only."
However, the plugins-reference documents that when a plugin uses skill paths like
`"skills": ["./"]`, the frontmatter `name` field determines the invocation name,
giving a stable name across install methods. CC 2.1.94 stabilized this behavior.

- **Current status**: Works in practice; frontmatter-name-based invocation is
  stabilized in plugin path behavior
- **Divergence**: Published naming-character guidance still says hyphen-only
- **Mitigation**: If character restrictions are ever enforced strictly, migrate
  to internal hyphen names with external aliases

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
Solution docs use YAML frontmatter (see `plugins/ruby-grape-rails/skills/compound-docs/references/schema.md`).

### Hooks

Defined in `plugins/ruby-grape-rails/hooks/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [...],           // Generic safety + targeted Ruby/post-plan hooks
    "PreToolUse": [...],            // Block dangerous ops (rails/bin/rails/rake db:drop variants, force push, RAILS_ENV=production)
    "PostToolUseFailure": [...],   // Ruby failure hints + error critic for Ruby-relevant Bash failures
    "SubagentStart": [...],        // Iron Laws injection into all subagents
    "SessionStart": [...],         // Setup dirs + runtime tool detection + resume detection
    "UserPromptSubmit": [...],     // Auto session title from first prompt (once: true)
    "FileChanged": [...],          // Runtime refresh when Gemfile/Rakefile/lefthook/justfile files change
    "CwdChanged": [...],           // Runtime refresh when working directory changes
    "PreCompact": [...],           // Warn before compaction about active workflow state
    "PostCompact": [...],          // Advise re-reading active plan artifacts after compaction
    "Stop": [...],                 // Warn if uncompleted tasks
    "StopFailure": [...]           // Persist API failure context for resume flows
  }
}
```

**Current hooks:**

- `PreToolUse` (Bash): Block destructive operations before execution, including
  `rails db:drop/reset/purge`, `bin/rails db:drop/reset/purge`,
  `./bin/rails db:drop/reset/purge`, `bundle exec rails db:drop/reset/purge`,
  `rake db:drop/reset/purge`, `bin/rake db:drop/reset/purge`,
  `./bin/rake db:drop/reset/purge`, `bundle exec rake db:drop/reset/purge`,
  equivalent `bundle exec bin/...` and env-prefixed forms, Redis flushes
  (`redis-cli flushall` / `flushdb`), `git push --force`, and
  `RAILS_ENV=production`
- `PostToolUse` (Edit|Write, broad safety layer):
  - `security-reminder.sh`: Security Iron Laws for auth/sensitive files
  - `log-progress.sh`: Async progress logging
  - `secret-scan.sh`: Secret scanning with hook-mode gating
- `PostToolUse` (Ruby-ish Edit/Write, declarative `if` filters):
  - `rubyish-post-edit.sh`: fan-out for `*.rb`, `*.rake`, `*Gemfile`,
    `*Rakefile`, and `*config.ru`
  - delegates to `iron-law-verifier.sh`, `format-ruby.sh`,
    `verify-ruby.sh`, and `debug-statement-warning.sh`
- `PostToolUse` (`Write(*plan.md)` only):
  - `plan-stop-reminder.sh`: STOP reminder when a new or replaced `plan.md`
    lands on disk
- `PostToolUseFailure` (Bash): Ruby-specific debugging hints and **error critic**
  only for Ruby-relevant Bash failures (`bundle`, `rails`, `rake`, `ruby`,
  `rspec`, `standardrb`, `rubocop`, `brakeman`) via declarative `if` filters
- `SubagentStart`: Inject all Iron Laws into every spawned subagent via `additionalContext` (addresses zero skill auto-loading gap)
- `UserPromptSubmit`: Auto session title from first prompt — `/rb:plan auth`
  → `"rb:plan — auth"`, free-form prompts use first ~60 chars. Uses
  `hookSpecificOutput.sessionTitle` (CC v2.1.94+), `once: true`. Does not
  support matchers.
- `PreCompact`: Warn before compaction about the active plan/work/full state so
  the next turn re-reads the right artifacts after compaction
- `PostCompact`: Advise Claude which active plan artifacts to re-read after
  compaction when unchecked tasks still exist
- `SessionStart` (all): Setup `.claude/` directories + fast runtime snapshot,
  plus async background runtime refresh
  - `detect-runtime-fast.sh`: quick first-turn runtime snapshot and `.runtime_env`
  - `detect-runtime-async.sh`: quiet full refresh for helper versions and slower probes
- `SessionStart` (startup|resume only): Scratchpad auto-init/check +
  resume workflow detection + workflow hints
- `FileChanged` (Gemfile|Gemfile.lock|Rakefile|lefthook.yml|lefthook.yaml|justfile): Re-runs `detect-runtime-file-changed.sh` to refresh `.claude/.runtime_env` when core project files change mid-session
- `CwdChanged`: Re-runs `detect-runtime-file-changed.sh` to keep runtime detection aligned when the session moves between repos or package roots
- `Stop`: Warn if plans have unchecked tasks
- `StopFailure`: Append normalized API-failure context to the active plan scratchpad for better resume continuity

**Deletion safety rule:**

- use `rm -f` only for `mktemp` outputs or exact fixed plugin-owned paths
- use `rm -rf` only for validated `mktemp -d` outputs
- prefer `rmdir` for expected-empty lock directories
- for variable-based cleanup, validate the path/prefix first and use
  `${var:?}` in the final delete

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
- `PreCompact` has **no context injection path** — use a user-facing stderr
  reminder only and rely on `PostCompact` to re-read active plan artifacts
- `SessionStart` stdout IS added to Claude's context (one of two exceptions along with `UserPromptSubmit`)
- `SubagentStart` uses `hookSpecificOutput.additionalContext` to inject context into subagents
- `PostToolUseFailure` uses `hookSpecificOutput.additionalContext` for debugging hints

## Development

### Testing locally

```bash
# Run these commands from the repo root.

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
# Check: Checkboxes update, progress logged in .claude/plans/test-feature/progress.md
```

### Adding new agent

1. Create `plugins/ruby-grape-rails/agents/{name}.md`
2. Add frontmatter with all required fields
3. Target under 300 lines when practical

### Adding new skill

1. Create `plugins/ruby-grape-rails/skills/{name}/SKILL.md` (prefer ~100-200 lines for new skills)
2. Create `references/` with detailed content
3. For workflow skills, document integration with cycle

### Setup

```bash
npm ci  # Pre-commit hooks + linting with the committed lockfile
npm run doctor  # Verify shellcheck, Claude CLI, python3/ruby/jq, and optional betterleaks
```

### Linting

```bash
npm run lint       # Run the full local lint/validation bundle
npm run lint:markdown  # Check markdown only
npm run lint:fix   # Auto-fix issues
```

### Validation

```bash
# Validate plugin structure and manifest
npm run validate

# Validate version alignment + changelog heading/footer integrity
python3 scripts/check-release-metadata.py

# Should pass without errors before committing changes
```

### Output Artifact Eval

`1.7.0` adds deterministic contributor checks for research/review outputs:

```bash
make eval-output
# or
npm run eval:output
```

This scores tracked fixture artifacts under `lab/eval/fixtures/output/` and is
the canonical contributor check for provenance/report contract changes.

### Hook Failure Policy

Keep hook behavior explicit when editing scripts under
`plugins/ruby-grape-rails/hooks/scripts/`:

- advisory hooks warn or skip on degraded state and must say so clearly:
  `detect-runtime.sh`, `check-resume.sh`, `log-progress.sh`
- delegated Ruby post-edit guardrails fail closed once they are selected for a
  Ruby-ish path:
  `rubyish-post-edit.sh`, `format-ruby.sh`, `verify-ruby.sh`,
  `debug-statement-warning.sh`
- security-sensitive hooks should fail closed in strict/high-confidence cases
  and document any narrower advisory fallback explicitly:
  `secret-scan.sh`, `block-dangerous-ops.sh`

Do not leave this implicit. Add or update a short policy comment near the top
of the hook when behavior changes.

## Size Guidelines

| Component | Target | Hard Limit | Notes |
|-----------|--------|------------|-------|
| SKILL.md (reference) | ~100 | ~150 | Iron Laws + quick patterns |
| SKILL.md (command) | ~100 | ~185 | Command skills need complete execution flow inline |
| references/*.md | ~350 | ~350 | Detailed patterns |
| agents (specialist) | ~300 | ~365 | Design guidance beyond preloaded skill patterns |
| agents (orchestrator) | ~300 | ~535 | Subagent prompts + flow control must be inline |

### Why orchestrators and command skills exceed targets

Marketplace-installed plugin files live in `~/.claude/plugins/cache/` and agent
tool access still follows the session permission policy. This means agents
**cannot reliably read** skill `references/*.md` at runtime.

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
- [ ] `disallowedTools: Edit, NotebookEdit, Agent, EnterWorktree, ExitWorktree, Skill` for artifact-writing agents; add `Write` for conversation-only agents
- [ ] `tools:` allowlist only for agents with intentionally narrow tool sets (web-researcher, output-verifier, ruby-gem-researcher)
- [ ] `omitClaudeMd: true` for specialist agents that don't need contributor context
- [ ] Skills preloaded
- [ ] Description at or under 250 chars
- [ ] Under target (300 lines), hard limit only if justified by inline subagent prompts

### New skill

- [ ] SKILL.md keeps only routing-critical guidance inline; bulky examples live in `references/`
- [ ] "Iron Laws" section
- [ ] `references/` for details
- [ ] No `triggers:` field
- [ ] Description at or under 250 chars

### New workflow skill

- [ ] Clear input/output artifacts
- [ ] Integration diagram with cycle position
- [ ] State transitions documented
- [ ] References previous/next phases

### Release

- [ ] All markdown passes linting
- [ ] Versions aligned in:
  - `package.json`
  - `.claude-plugin/marketplace.json`
  - `plugins/ruby-grape-rails/.claude-plugin/plugin.json`
- [ ] `CHANGELOG.md` updated with all changes under new version heading
- [ ] README updated
- [ ] `/rb:intro` tutorial content still accurate (commands, agents, features)

### Versioning

The plugin uses [semantic versioning](https://semver.org/):

- **MAJOR**: Breaking changes (workflow redesign, removed commands)
- **MINOR**: New features (new hooks, skills, agents, commands)
- **PATCH**: Bug fixes, doc updates, description improvements

**IMPORTANT**: Keep release versions aligned across `package.json`,
`.claude-plugin/marketplace.json`, and
`plugins/ruby-grape-rails/.claude-plugin/plugin.json`. Marketplace metadata,
published package metadata, and the shipped plugin manifest should move
together when preparing a release.

When making changes, keep `CHANGELOG.md` aligned with release state. Use
categories: Added, Changed, Fixed, Removed.

- if the current version is already treated as released, add new notes under
  `[Unreleased]`
- if preparing the next release, move that work into the target version section
  and bump all three versioned metadata files together

# Claude Code Behavioral Instructions

**CRITICAL**: These instructions OVERRIDE default behavior for Ruby/Rails/Grape projects in this codebase.

## Automatic Skill Loading

When working on Ruby/Rails/Grape code, ALWAYS load relevant skills based on file context:

| File Pattern | Auto-Load Skills | Check References |
|--------------|------------------|------------------|
| `*_controller.rb`, `*_helper.rb` | `rails-contexts`, `rails-idioms` | `plugins/ruby-grape-rails/skills/rails-contexts/references/routing-patterns.md` |
| `*job.rb`, `app/jobs/*` | `sidekiq` or `rails-idioms` | `plugins/ruby-grape-rails/skills/sidekiq/references/job-patterns.md` |
| `db/migrate/*`, `*_migration.rb`, `*model.rb` | `active-record-patterns`, `safe-migrations` | `plugins/ruby-grape-rails/skills/active-record-patterns/references/migrations.md`, `plugins/ruby-grape-rails/skills/active-record-patterns/references/queries.md` |
| `*auth*`, `*session*`, `*password*` | `security` | `plugins/ruby-grape-rails/skills/security/references/authentication.md`, `plugins/ruby-grape-rails/skills/security/references/authorization.md` |
| `*_spec.rb`, `*_test.rb`, `*factory*`, `*fixtures*` | `testing` | `plugins/ruby-grape-rails/skills/testing/references/rspec-patterns.md`, `plugins/ruby-grape-rails/skills/testing/references/factory-patterns.md` |
| `config/environments/production.rb`, `Dockerfile`, `fly.toml` | `deploy` | `plugins/ruby-grape-rails/skills/deploy/references/docker-config.md` |
| `app/services/*`, `app/interactors/*`, `lib/**/*.rb` | `rails-contexts`, `ruby-contexts` | `plugins/ruby-grape-rails/skills/rails-contexts/references/context-patterns.md` |
| `lib/tasks/*.rake` | `ruby-idioms` | `plugins/ruby-grape-rails/skills/ruby-idioms/references/rake-tasks.md` |
| `*_component.rb`, `app/components/*` | `hotwire-patterns` | `plugins/ruby-grape-rails/skills/hotwire-patterns/references/components.md` |
| `app/api/**/*.rb`, `*_api.rb`, `app/apis/**/*.rb` | `grape-idioms` | `plugins/ruby-grape-rails/skills/grape-idioms/references/grape-patterns.md` |
| `*.rb` | `ruby-idioms` | Always check Iron Laws |

**Hook prerequisites:** core hook automation expects `bash`, `jq`, `grep`, and
standard Unix utilities (`head`, `readlink`, `awk`, `cksum`, `mktemp`, `sed`,
`find`, `cp`, `mv`, `rm`, `tr`, `wc`, `cat`, `mkdir`) to be available. When
those dependencies are missing, hooks now surface an explicit error or warning
instead of silently disabling guardrails.

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

Iron Laws are maintained in `iron-laws.yml` and projected into shipped plugin
artifacts.

When `iron-laws.yml` changes, rerun:

```bash
bash scripts/generate-iron-law-outputs.sh
```

This refreshes the generated hook/runtime projections, including the shipped
injector/verifier surfaces.

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

See the [Automatic Skill Loading](#automatic-skill-loading) section above for
the canonical auto-load routing table by file pattern.

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
| Small change (<100 lines) | `/rb:quick` |
| Explore ideas, gather requirements | `/rb:brainstorm` |
| New feature (clear scope) | `/rb:plan` then `/rb:work` |
| Understand a plan | `/rb:brief` |
| Enhance existing plan | `/rb:plan --existing` |
| Large feature (new domain) | `/rb:full` |
| Review code | `/rb:review` |
| Triage review findings | `/rb:triage` |
| Capture solved problem | `/rb:compound` |
| Run checks | `/rb:verify` |
| Reduce permission prompts | `/rb:permissions` |
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
| Scan sessions for exploratory metrics | `/session-scan` |
| Deep-review session transcripts | `/session-deep-dive` |
| View provider-scoped trends | `/session-trends` |
| Monitor observational skill signals | `/skill-monitor` |
| Validate plugin against cached docs | `/docs-check` |

**Workflow Commands**: `/rb:brainstorm` (optional) -> `/rb:plan` -> `/rb:brief` (optional) ->
`/rb:plan --existing` (optional) -> `/rb:work` -> `/rb:brief` (optional) ->
`/rb:review` -> `/rb:triage` (optional) -> `/rb:compound`

**Review → Follow-up Plan**: After `/rb:review`, if findings reveal scope gaps or missing coverage, use `/rb:triage .claude/reviews/{review-slug}.md` to turn selected findings into `.claude/plans/{slug}/plan.md`.

**Standalone**: `/rb:quick`, `/rb:full`, `/rb:investigate`, `/rb:verify`, `/rb:research`, `/rb:permissions`

**Analysis**: `/rb:n1-check`, `/rb:state-audit`, `/rb:boundaries`, `/rb:trace`, `/rb:techdebt`

**Session Analytics (dev-only, requires ccrider MCP)**: `/session-scan`, `/session-deep-dive`, `/session-trends`
Use these as exploratory workflows. Prefer a single provider per run when you
care about comparisons.

**Skill Monitoring (dev-only)**: `/skill-monitor` — observational per-skill
signals and recommendation triage, not release-grade proof

**Plugin Maintenance (dev-only)**: `/docs-check` — validate plugin against the
current cached Claude Code docs and separate real schema drift from stale local
guidance

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

### Contributor Eval Workflow

For contributor-facing plugin quality work, prefer the deterministic eval
entrypoints before broader experimentation:

Minimum runtime: `python3` 3.10+ for `lab/eval/`.

- `make eval` / `npm run eval` for lint + injection check + tracked changed surfaces
- `make eval-all` / `npm run eval:all` for the full eval snapshot
- `make eval-ci` / `npm run eval:ci` for the contributor CI gate
- `make eval-output` / `npm run eval:output` for deterministic research/review
  artifact and provenance checks
- `make security-injection` / `npm run security:injection`
- `make eval-tests` / `npm run eval:test` for the default contributor test
  path (`unittest` discovery)
- `make eval-tests-pytest` / `npm run eval:test:pytest` for explicit `pytest`
  runs
- `make eval-behavioral` / `npm run eval:behavioral` for LLM-based trigger
  routing tests (cache-only, runs offline if cache exists)
- `make eval-behavioral-verbose` / `npm run eval:behavioral:verbose` — same,
  with verbose cache/score output
- `make eval-behavioral-fresh` / `npm run eval:behavioral:fresh` — ignore
  cache, re-run via `claude` CLI with Haiku access
- `make eval-behavioral-fresh-verbose` / `npm run eval:behavioral:fresh:verbose`
  — fresh run with full prompt/response debug output
- `make eval-ablation` / `npm run eval:ablation` for leave-one-out matcher
  signal/noise classification (deterministic, no API calls)
- `make eval-neighbor` / `npm run eval:neighbor` for confusable-pair
  regression detection on changed skills (requires Haiku for fresh results)
- `make eval-hygiene` / `npm run eval:hygiene` for trigger corpus
  contamination scanning (deterministic)
- `make eval-baseline`
- `make eval-compare`
- `make eval-overlap`
- `make eval-hard-corpus`

Notes:

- `eval-output` is separate from `eval-all` / `eval-ci` for now.
- `--include-untracked` is available for local changed-mode exploration, but it
  intentionally makes results non-comparable and is not part of `eval-ci`.
- `check-dynamic-injection.sh` expects git metadata for comparable tracked-file
  scans.

Current `lab/eval/` scope:

- full 51/51 skill eval coverage (all shipped skills)
- full 51/51 trigger corpora (all shipped skills)
- structural scoring for all shipped agents
- deterministic trigger corpora and confusable-pair analysis
- deterministic research/review artifact and provenance checks
- optional behavioral routing dimension (`--behavioral` flag, cached haiku results)

For contributor workflows under `.claude/`, use this order:

1. `claude plugin validate plugins/ruby-grape-rails`
2. `make eval` or `make eval-all`
3. `make eval-output` for deterministic research/review artifact fixtures
4. `/docs-check` when Claude docs or local schema assumptions may have drifted
5. session analytics only as corroborating, provider-scoped evidence

---

## Claude Code Features Under Evaluation

Based on `/docs-check` validation against the current cached Claude Code docs,
these are the main still-unadopted features worth tracking:

### Agents

- `isolation: "worktree"` for agents that modify files, such as
  `verification-runner` or parallel review tasks. CC 2.1.97 fixed a parent-cwd
  leak bug, reducing evaluation risk.

### Hooks

- `http` hook type for external telemetry/logging
- `SubagentStop` for specialist completion metrics. CC 2.1.97 fixed
  prompt-type Stop/SubagentStop hooks failing on long sessions.
- `SessionEnd` for cleanup of temporary artifacts
- Per-skill YAML frontmatter hooks are documented and available (CC 2.1.94
  fixed plugin skill frontmatter hooks being silently ignored). Not adopted —
  no skills currently need them. Note: plugin **agents** still do not support
  `hooks`, `mcpServers`, or `permissionMode`.

### Skills

- broader `paths:` adoption, especially whether `hotwire-patterns` should be
  path-scoped or left semantic-only

### Plugin

- `${CLAUDE_PLUGIN_DATA}` for persistent plugin-managed state or caches
- plugin-root `settings.json` currently only supports the `agent` key;
  `effortLevel` and `showTurnDuration` are NOT supported in plugin settings
  (unknown keys are silently ignored). Track for future key expansion.
- `.lsp.json` LSP configuration, with Ruby LSP preferred if this is ever added.
  Requires users to install LSP binary separately.

### Output Styles

- `keep-coding-instructions` frontmatter field: documented for custom output
  styles (preserves coding instructions in system prompt when `true`). Not
  relevant unless the plugin ships an `output-styles/` directory.

### Adoption Criteria

Features are adopted when:

1. They solve a concrete problem (not just "nice to have")
2. They don't add complexity without clear benefit
3. They're tested in development environment first
4. They're documented in this section when adopted
