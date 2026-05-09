---
paths:
  - plugins/ruby-grape-rails/skills/**
  - .claude/skills/**
---

# Skill Development

## Audience: Agents, Not Humans

Skill bodies + `references/*.md` load into agent context when the
skill is invoked. Imperative instructions only — no tutorial
narration, no reasoning preludes, no `#` thinking lines inside
Bash command bodies (preference #6). Use markdown tables for
command/option lists.

## Structure

```
skills/{name}/
├── SKILL.md           # ~100-200 lines; move bulky examples to references/
└── references/        # Detailed content, ~350 lines max per file
    └── *.md
```

## Rules

- Include an "Iron Laws" section for critical rules
- No `triggers:` field — use `description` for auto-loading
- Description <= 1,536 characters (combined `description` + `when_to_use` truncates at 1,536; front-load key use case)
- For plugin-wide executables in `bin/`, use explicit `${CLAUDE_PLUGIN_ROOT}/bin/<cmd>` when the skill also references `${CLAUDE_SKILL_DIR}` (bare names can be conflated with skill-local files)
- **Cross-reference path rules** (substitution scope per CC docs):

  | Source file | Target | Pattern |
  |---|---|---|
  | SKILL.md body | sibling reference (same skill) | plain `references/<name>.md` (Anthropic standard) |
  | SKILL.md body | bash injection (`!`backtick) | `${CLAUDE_SKILL_DIR}/...` or `${CLAUDE_PLUGIN_ROOT}/...` (substituted at render) |
  | SKILL.md body | cross-skill or plugin-root file | `${CLAUDE_PLUGIN_ROOT}/...` (substituted at render) |
  | `references/*.md` | sibling in same `references/` dir | **plain filename only** — `discipline.md` |
  | `references/*.md` | parent SKILL.md | **`../SKILL.md`** |
  | `references/*.md` | cross-skill file | **repo-rooted** `plugins/ruby-grape-rails/skills/<skill>/...` |
  | `references/*.md` | bash command for agent to run | `${CLAUDE_PLUGIN_ROOT}/bin/...` (env var expands at shell level) |
  | `hooks.json` `command` | any plugin file | `${CLAUDE_PLUGIN_ROOT}/...` (CC documents this) |
  | Skill `hooks` frontmatter | bundled script | `${CLAUDE_PLUGIN_ROOT}/...` only — `${CLAUDE_SKILL_DIR}` not exposed there |

  Reason: CC substitutes `${CLAUDE_*}` only in (a) SKILL.md content
  rendered before send, (b) plugin-config-layer fields
  (hooks/MCP/LSP/monitors). Reference files load via Read tool — no
  substitution layer. Anthropic's official `anthropics/skills` repo
  uses **zero** `${CLAUDE_*}` literals in any reference file.
- Artifact paths: use `${REPO_ROOT}/.claude/...` only in imperative
  spawn / write steps where main session constructs the absolute path
  passed to subagents. Use relative `.claude/...` in contract docs,
  templates, user-facing references describing where artifacts live.
- Spawn-fanout skills: use run manifest at
  `.claude/{namespace}/RUN-CURRENT.json` (where `{namespace}` already
  includes the per-skill slug fragment, e.g. `reviews/{review-slug}`,
  `plans/{plan-slug}/research-fanout`). Per-run artifact paths use
  `{slug}-{datesuffix}.md` (review) or stable `{topic-slug}.md`
  (plan/brainstorm). See
  `plugins/ruby-grape-rails/references/run-manifest.md` for schema,
  staleness rules, and write protocol.
- Agent dispatch: foreground only. Skill bodies MUST NOT pass
  `run_in_background: true` on any `Agent(...)` call. Parallel = many
  Agent tool calls in a single message, NOT the background flag.

## Colon Naming

Colons in skill names (e.g., `rb:plan`) work via frontmatter `name` field (stabilized CC 2.1.94). If character restrictions are ever enforced, migrate to hyphen names with aliases.

## Workflow Skills

Workflow skills (plan, work, review, compound, full) have special requirements:

- Define clear input/output artifacts
- Include integration diagram showing position in the plan/work/review/compound cycle
- Document state transitions
- Reference previous and next phases
