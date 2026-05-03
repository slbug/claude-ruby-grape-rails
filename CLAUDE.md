# Plugin Development Guide

Ruby/Rails/Grape Claude Code plugin. Validated on macOS, Linux, WSL.
Native Windows unsupported.

## Posture

- Lean read-only specialist agents (`omitClaudeMd: true`)
- Fast `SessionStart` with async refresh
- Filesystem is the state machine — each phase reads previous
  phase's output
- Targeted post-edit routing via `rubyish-post-edit.sh` fan-out
- Solutions feed back into future cycles

## Workflow

```
/rb:brainstorm (optional) -> /rb:plan -> /rb:work -> /rb:verify -> /rb:review -> /rb:compound
                                |           |            |              |              |
                                v           v            v              v              v
                   .claude/plans/{slug}/  (namespace)  (namespace)  (namespace)  .claude/solutions/
```

### Commands

| Command | Phase | Input | Output |
|---|---|---|---|
| `/rb:brainstorm` | Discovery | Topic / feature idea | `.claude/plans/{slug}/interview.md` |
| `/rb:plan` | Planning | Feature description | `.claude/plans/{slug}/plan.md` |
| `/rb:plan --existing` | Enhancement | Plan file | Enhanced plan with research |
| `/rb:brief` | Understanding | Plan file | Interactive walkthrough (ephemeral) |
| `/rb:work` | Execution | Plan file | Updated checkboxes + `.claude/plans/{slug}/progress.md` |
| `/rb:verify` | Verification | `[--quick\|--full]` (resolves from current branch state, NOT plan path) | Verification results |
| `/rb:review` | Quality | Changed files | `.claude/reviews/{review-slug}-{datesuffix}.md` + per-agent artifacts |
| `/rb:compound` | Knowledge | Solved problem | `.claude/solutions/{category}/{fix}.md` |
| `/rb:full` | All | Feature description | Complete cycle with compounding |

### Artifact Directories

| Namespace | Path |
|---|---|
| Plan | `.claude/plans/{slug}/{plan.md, research/, progress.md, scratchpad.md}` |
| Review consolidated | `.claude/reviews/{review-slug}-{datesuffix}.md` |
| Review per-agent | `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md` |
| Review manifest | `.claude/reviews/{review-slug}/RUN-CURRENT.json` + `RUN-HISTORY.jsonl` (schema: `references/run-manifest.md`) |
| Audit | `.claude/audit/` |
| Cross-plan research | `.claude/research/{topic-slug}.md` |
| Investigations | `.claude/investigations/{agent}/{slug}-{datesuffix}.md` |
| Skill metrics | `.claude/skill-metrics/` |
| Solutions | `.claude/solutions/{category}/` |
| Provenance scans | `.claude/provenance-scan/` |

## Structure

```
claude-ruby-grape-rails/
├── .claude-plugin/marketplace.json
├── .claude/                         # Contributor tooling (NOT distributed)
│   ├── agents/   ├── rules/   └── skills/
├── scripts/
├── plugins/ruby-grape-rails/
│   ├── .claude-plugin/plugin.json
│   ├── agents/                      # 19 specialist agents
│   ├── bin/                         # Plugin executables (added to Bash PATH)
│   ├── hooks/hooks.json
│   ├── lib/                         # Shared Ruby modules (stdlib only)
│   ├── references/                  # Shipped reference docs
│   └── skills/                      # 53 skills
├── lab/eval/                        # Contributor-only deterministic eval tooling
├── CLAUDE.md
└── README.md
```

## Conventions

### Audience: Agents, Not Humans

ALL prose in this repo (except `README.md`, `CHANGELOG.md`, and
executable code under `scripts/` / `lab/eval/`) loads into some
agent's context at runtime: shipped plugin docs into Claude
sub-/main-sessions; `.claude/rules/` + `.claude/skills/` into
contributor-session Claude; `.github/copilot-instructions.md` +
`.github/instructions/*` into Copilot. Authoring rule: imperative
instructions, not explanatory guides.

| Rule | Action |
|---|---|
| Tutorial narration ("first do X, then Y, this teaches…") | reject |
| Reasoning preludes before commands | state the action, drop the prelude |
| `#` thinking/checklist lines inside Bash command bodies (preference #6) | use markdown table or prose lead-in instead |
| Long explanatory paragraphs where a table fits | rewrite as table |
| Step-by-step explanation of obvious mechanics | drop |

### Agents

See `.claude/rules/agent-development.md` (auto-loads when editing
agent files).

### Skills

See `.claude/rules/skill-development.md` (auto-loads when editing
skill files).

### Hooks

See `.claude/rules/hook-development.md` (auto-loads when editing
hook files).

### Iron Laws + Preferences

Source of truth: `plugins/ruby-grape-rails/references/iron-laws.yml`
and `preferences.yml`. After edits, regenerate downstream artifacts:

```bash
bash scripts/generate-iron-law-outputs.sh all
```

### Workflow Skills

Required structure for `plan`, `work`, `review`, `compound`, `full`:

- Clear input/output artifacts
- Cross-references to neighboring workflow phases
- Integration diagram showing cycle position
- State transitions

### Compound Knowledge Skills

| Skill | Role |
|---|---|
| `compound-docs` | Schema + reference for solution documentation |
| `compound` (`/rb:compound`) | Post-fix knowledge capture |

Solution docs use YAML frontmatter — schema:
`plugins/ruby-grape-rails/skills/compound-docs/references/schema.md`.

## Checklist

### New agent

- [ ] Frontmatter complete
- [ ] `disallowedTools: Edit, NotebookEdit, Agent, EnterWorktree, ExitWorktree, Skill` for artifact-writing agents; add `Write` for conversation-only agents
- [ ] `tools:` allowlist only for agents with intentionally narrow tool sets
- [ ] `omitClaudeMd: true` for specialist agents that don't need contributor context
- [ ] Skills preloaded
- [ ] Description ≤ 250 chars
- [ ] Body ≤ 300 lines (target); move long templates / examples to `references/`

### New skill

- [ ] `SKILL.md` keeps routing-critical guidance inline; bulky examples in `references/`
- [ ] "Iron Laws" section
- [ ] `references/` for details
- [ ] No `triggers:` field
- [ ] Description ≤ 1,536 chars (combined with `when_to_use`; front-load key use case)

### New workflow skill

- [ ] Clear input/output artifacts
- [ ] Integration diagram with cycle position
- [ ] State transitions documented
- [ ] Cross-references to previous + next phases

### Release

- [ ] Markdown lint passes
- [ ] Version aligned across `package.json`, `.claude-plugin/marketplace.json`, `plugins/ruby-grape-rails/.claude-plugin/plugin.json`
- [ ] `CHANGELOG.md` updated under new version heading
- [ ] `README.md` updated
- [ ] `/rb:intro` tutorial content current (commands, agents, features)

## Behavioral Rules

### Learn from corrections

After contributor corrects an action: ask "should I update CLAUDE.md
so this doesn't happen again?" If yes, add an actionable rule of
the form `Do NOT X — instead Y`.

### Intro tutorial maintenance

When adding/removing/renaming commands/skills/agents, update
`plugins/ruby-grape-rails/skills/intro/references/tutorial-content.md`.

### Epistemic posture

Apply the contract from
`plugins/ruby-grape-rails/references/research/epistemic-posture.md`:

- Challenge false premises that contradict repo evidence — do NOT
  accept contributor framing without verification
- Avoid unsupported agreement, apology cascades, hedge chains
- Acknowledge mistakes once, state correction, continue
- Prefer positive success targets over prohibition chains
- Use direct language for HIGH-confidence findings

The Iron Laws + preferences injector enforces this at
`SessionStart` (main) and `SubagentStart` (subagents) via
`inject-rules.sh`. This reminder keeps main-conversation
contributor work aligned even outside the hook delivery path.

## Versioning

[Semantic versioning](https://semver.org/):

| Bump | Trigger |
|---|---|
| MAJOR | Breaking changes (workflow redesign, removed commands) |
| MINOR | New features (hooks, skills, agents, commands) |
| PATCH | Bug fixes, doc updates, description improvements |

Keep versions aligned across `package.json`,
`.claude-plugin/marketplace.json`,
`plugins/ruby-grape-rails/.claude-plugin/plugin.json`. Keep
`CHANGELOG.md` aligned with release state (categories: Added,
Changed, Fixed, Removed). Use `[Unreleased]` for post-release
changes; move to the target version section when preparing the
next release.

@.claude/rules/development.md
@.claude/rules/eval-workflow.md
