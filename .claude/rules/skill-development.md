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
- No `triggers:` field — use `description` for routing
- No `when_to_use:` field — single `description` field per agentskills.io canon
- No `paths:` field on plugin SKILL.md — empirically non-functional at plugin scope (the `.claude/rules/*.md` `paths:` mechanism is distinct and remains functional)
- **Registry sync on visibility flips**: toggling `disable-model-invocation`, renaming, or adding/removing a skill REQUIRES updating `plugins/ruby-grape-rails/references/skill-registry.yml`:
  - DMI on → entry under `hidden_skills` with `aliases:`, `advertise_in:`, `symptom:`, `rationale:`
  - DMI off (or absent) → entry under `visible_skills` with `name`, `folder`, `rationale` only (no `advertise_in` — auto-routed via description)
  - After edit: run `bash scripts/generate-skill-routing.sh` to propagate to intent-detection routing table, hub footers, and tutorial inventory
  - `test_registry_visibility_sync.py` catches drift between SKILL.md DMI flag and registry bucket; `test_registry_in_sync.py` catches drift between registry and generated artifacts
- Description <= 1,024 chars (agentskills.io cap); front-load WHEN the skill applies, include real-query phrases as Triggers, include negative exclusion clauses as Do NOT use for
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

  CC substitution scope: (a) SKILL.md content rendered before send,
  (b) plugin-config-layer fields (hooks / MCP / LSP / monitors). NOT
  reference files — those load via Read tool with no substitution
  layer. Anthropic's `anthropics/skills` uses zero `${CLAUDE_*}`
  literals in any reference file.
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

Colons in skill names (e.g., `rb:plan`) work via the frontmatter `name` field. If character restrictions are ever enforced, migrate to hyphen names with aliases.

## Description = routing trigger

Tell the model WHEN to load the skill, not WHAT the skill does. Front-load the real-query phrase. Include negative exclusion clauses.

- Pattern: gerund-led "`{What it does}. Triggers: \"phrase1\", \"phrase2\". Do NOT use for: <exclusion>.`"
- Single `description` field, ≤1,024 chars
- Real-query phrasing wins over polished marketing prose
- Negative examples can matter more than positive examples
- Action-at-a-distance: changing one description shifts routing of unrelated skills; run the eval before merge
- LLM-generated descriptions tend to be low-quality; require human curation

## Body discipline — every skill is a tax

Every sentence costs context every session. Apply the test to each sentence: would the agent get this wrong without this instruction? Delete sentences that fail.

## Append-mostly maintenance

Skills are append-mostly. The gotchas / anti-patterns section accrues the most value over time. Add gotchas; do not rewrite history.

## Workflow Skills

Workflow skills (plan, work, review, compound, full) have special requirements:

- Define clear input/output artifacts
- Include integration diagram showing position in the plan/work/review/compound cycle
- Document state transitions
- Reference previous and next phases
