---
paths:
  - plugins/ruby-grape-rails/skills/**
---

# Skill Development

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
- Artifact paths: use `${REPO_ROOT}/.claude/...` only in imperative
  spawn / write steps where main session constructs the absolute path
  passed to subagents. Use relative `.claude/...` in contract docs,
  templates, user-facing references describing where artifacts live.
- Spawn-fanout skills: use run manifest at
  `.claude/{namespace}/{slug}/RUN-CURRENT.json` for cross-session
  resume. Per-run artifact paths use `{slug}-{datesuffix}.md`. See
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
