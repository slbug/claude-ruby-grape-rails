---
paths:
  - plugins/ruby-grape-rails/agents/**
---

# Agent Development

## Model Selection

- **sonnet** (default): near-opus quality at lower cost; use for most specialists and secondary orchestrators
- **opus**: primary workflow orchestrators and security-critical agents only
- **haiku**: mechanical tasks — compression, verification, dependency analysis

## Tool Access

Prefer denylist-only over `tools:` allowlists (follows built-in agent pattern).

- All denylist specialists block: `Agent, EnterWorktree, ExitWorktree, Skill`
- **Artifact-writing agents**: add `Edit, NotebookEdit` to disallowedTools
- **Conversation-only agents**: add `Write` to the above
- `parallel-reviewer` keeps `Agent` (spawns sub-reviewers) but blocks the rest
- `tools:` allowlists only for intentionally narrow agents (web-researcher, output-verifier, ruby-gem-researcher)

## omitClaudeMd

Set `omitClaudeMd: true` for shipped specialist agents that do not need
contributor-only CLAUDE.md guidance at runtime. Iron Laws still arrive
through `SubagentStart`. The criterion is whether the agent needs repo
conventions, not whether it has Write access.

## Memory

Use `memory: project` for agents that benefit from cross-session learning
(orchestrators, pattern analysts). Note: `memory` auto-enables Read, Write,
Edit — only add to agents that already have Write access.

## Size Limits

- Target: 300 lines; hard limit: 365 (specialist) / 535 (orchestrator)
- Description: <= 250 characters (longer descriptions are silently truncated)

## Why Orchestrators Exceed Targets

Marketplace agents cannot reliably Read `references/*.md` (permission
prompt in installed plugins). Subagent prompts must be inline (~80 lines
x 4 agents = 320 lines minimum). Only trim purely informational,
non-execution-critical content.
