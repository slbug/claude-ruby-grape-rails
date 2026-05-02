# Plugin Development Guide

Development documentation for the Ruby/Rails/Grape Claude Code plugin.

Contributor tooling and shipped hook workflows are validated on macOS, Linux,
and WSL. Native Windows is not currently supported.

## Overview

This plugin provides **agentic workflow orchestration** with specialist agents and reference skills for Ruby/Rails/Grape development.

Posture: lean read-only agents (`omitClaudeMd: true`), fast SessionStart
with async refresh, structured workflow memory (scratchpads), and targeted
post-edit routing via `rubyish-post-edit.sh` fan-out.

## Workflow Architecture

The plugin supports an optional **Brainstorm** discovery step before the core **Plan -> Work -> Verify -> Review -> Compound** lifecycle:

```
/rb:brainstorm (optional) -> /rb:plan -> /rb:work -> /rb:verify -> /rb:review -> /rb:compound
                                |           |            |              |              |
                                v           v            v              v              v
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
| `/rb:verify` | Verification | `[--quick\|--full]` (mode flag; resolves from current branch state, NOT plan path) | Verification results |
| `/rb:review` | Quality | Changed files | `.claude/reviews/{review-slug}-{datesuffix}.md` + `.claude/reviews/{agent-slug}/...` |
| `/rb:compound` | Knowledge | Solved problem | `.claude/solutions/{category}/{fix}.md` |
| `/rb:full` | All | Feature description | Complete cycle with compounding |

### Artifact Directories

Plan: `.claude/plans/{slug}/` (plan.md, research/, summaries/,
progress.md, scratchpad.md). Review:
`.claude/reviews/{review-slug}-{datesuffix}.md` + `{agent-slug}/...` +
`{review-slug}/{RUN-CURRENT.json,RUN-HISTORY.jsonl}` (run manifest —
`references/run-manifest.md`). Other: `.claude/audit/`,
`.claude/research/{topic-slug}.md`,
`.claude/investigations/{agent}/{slug}-{datesuffix}.md`,
`.claude/skill-metrics/`, `.claude/solutions/{category}/`,
`.claude/provenance-scan/`.

## Structure

```
claude-ruby-grape-rails/
├── .claude-plugin/
│   └── marketplace.json
├── .claude/                         # Contributor tooling (NOT distributed)
│   ├── agents/
│   ├── rules/                       # Auto-loaded context rules
│   └── skills/
├── scripts/
├── plugins/
│   └── ruby-grape-rails/
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/                  # 19 specialist agents
│       ├── bin/                     # Plugin executables (added to Bash tool PATH)
│       ├── hooks/
│       │   └── hooks.json
│       ├── lib/                     # Shared Ruby modules (stdlib only)
│       ├── references/              # Shipped reference docs
│       └── skills/                  # 53 skills
├── lab/
│   └── eval/                        # Contributor-only deterministic eval tooling
├── CLAUDE.md
└── README.md
```

## Conventions

### Agents

See `.claude/rules/agent-development.md` (auto-loads when editing agent files).

### Skills

See `.claude/rules/skill-development.md` (auto-loads when editing skill files).

### Hooks

See `.claude/rules/hook-development.md` (auto-loads when editing hook files).

Iron Laws are maintained in `plugins/ruby-grape-rails/references/iron-laws.yml`.
When `iron-laws.yml` changes:

```bash
bash scripts/generate-iron-law-outputs.sh all
```

### Workflow Skills

Workflow skills (plan, work, review, compound, full) have special structure:

- Define clear input/output artifacts
- Reference other workflow phases
- Include integration diagram showing position in cycle
- Document state transitions

### Compound Knowledge Skills

The compound system captures solved problems as searchable institutional knowledge:

- `compound-docs` -- Schema and reference for solution documentation
- `compound` (`/rb:compound`) -- Post-fix knowledge capture skill

Solution docs use YAML frontmatter (see `plugins/ruby-grape-rails/skills/compound-docs/references/schema.md`).

## Checklist

### New agent

- [ ] Frontmatter complete
- [ ] `disallowedTools: Edit, NotebookEdit, Agent, EnterWorktree, ExitWorktree, Skill` for artifact-writing agents; add `Write` for conversation-only agents
- [ ] `tools:` allowlist only for agents with intentionally narrow tool sets
- [ ] `omitClaudeMd: true` for specialist agents that don't need contributor context
- [ ] Skills preloaded
- [ ] Description at or under 250 chars
- [ ] Under target (300 lines); move long templates and examples to references/

### New skill

- [ ] SKILL.md keeps only routing-critical guidance inline; bulky examples live in `references/`
- [ ] "Iron Laws" section
- [ ] `references/` for details
- [ ] No `triggers:` field
- [ ] Description at or under 1,536 chars (combined with `when_to_use`; front-load key use case)

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

### Behavioral Reminders

**Learn From Mistakes**: After ANY correction from a contributor, ask:
"Should I update CLAUDE.md so this doesn't happen again?" If yes, add a
concise rule preventing the specific mistake. Keep rules actionable:
"Do NOT X -- instead Y"

**Intro Tutorial Maintenance**: When adding, removing, or renaming
commands/skills/agents, check if
`plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`
needs updating. The tutorial is new users' first impression -- stale
command references erode trust.

**Epistemic Posture**: Apply the behavioral contract documented in
`plugins/ruby-grape-rails/references/research/epistemic-posture.md`
when working in this repo: challenge false premises directly instead of
accepting contributor framing that contradicts repo evidence; avoid
unsupported agreement, apology cascades, and hedge chains; acknowledge
mistakes once, state the correction, continue; prefer positive success
targets over prohibition chains; use direct language for HIGH-confidence
findings. Iron Laws + preferences injector enforces this at
`SessionStart` (main session) and `SubagentStart` (subagents) via the
shared `inject-rules.sh`; this reminder keeps main-conversation
contributor work aligned with the same posture even outside the hook
delivery path.

### Versioning

The plugin uses [semantic versioning](https://semver.org/):

- **MAJOR**: Breaking changes (workflow redesign, removed commands)
- **MINOR**: New features (new hooks, skills, agents, commands)
- **PATCH**: Bug fixes, doc updates, description improvements

**IMPORTANT**: Keep versions aligned across `package.json`,
`.claude-plugin/marketplace.json`, and
`plugins/ruby-grape-rails/.claude-plugin/plugin.json`. Keep `CHANGELOG.md`
aligned with release state (categories: Added, Changed, Fixed, Removed).
Use `[Unreleased]` for post-release changes; move into target version section
when preparing the next release.

@.claude/rules/development.md
@.claude/rules/eval-workflow.md
