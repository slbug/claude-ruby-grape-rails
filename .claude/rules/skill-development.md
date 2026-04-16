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

## Colon Naming

Colons in skill names (e.g., `rb:plan`) work via frontmatter `name` field (stabilized CC 2.1.94). If character restrictions are ever enforced, migrate to hyphen names with aliases.

## Workflow Skills

Workflow skills (plan, work, review, compound, full) have special requirements:

- Define clear input/output artifacts
- Include integration diagram showing position in the plan/work/review/compound cycle
- Document state transitions
- Reference previous and next phases
