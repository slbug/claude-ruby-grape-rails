---
paths:
  - plugins/ruby-grape-rails/agents/**
  - .claude/agents/**
---

# Agent Development

## Model Selection

- **sonnet** (default): near-opus quality at lower cost; use for most specialists
- **opus**: security-critical agents only (e.g., security-analyzer)
- **haiku**: mechanical tasks — compression, verification, dependency analysis

## Tool Access

Prefer denylist-only over `tools:` allowlists (follows built-in agent pattern).

- All denylist agents block: `Agent, EnterWorktree, ExitWorktree, Skill`
- **Artifact-writing agents**: add `Edit, NotebookEdit` to disallowedTools
- **Conversation-only agents**: add `Write` to the above
- `tools:` allowlists only for intentionally narrow agents (context-supervisor, web-researcher, output-verifier, ruby-gem-researcher)
- NO agent declares or invokes `Agent` — see "Subagents Are Leaf Workers" below

## Subagents Are Leaf Workers

- NEVER declare `Agent` in subagent `tools:` allowlist
- NEVER write `Agent(subagent_type:)` calls inside subagent bodies
- Orchestration belongs in skill bodies (main-session fanout)
- Specialist agents stay terminal: read, analyze, write artifact, return summary
- `context-supervisor` and similar compression agents are leaf workers
  callable from any skill body post-fanout

## Memory

Use `memory: project` only for pattern-analyst agents that benefit from
cross-session learning. Note: `memory` auto-enables Read, Write, Edit —
only add to agents that already have Write access. After the orchestrator
cleanup, no agent ships with `memory: project`; the field is a future
extension hook, not an active mechanism.

## omitClaudeMd Scope

- Shipped specialist agents (`plugins/ruby-grape-rails/agents/**`): SET
  `omitClaudeMd: true`. They do not need contributor CLAUDE.md context.
- Contributor agents (`.claude/agents/**`): MAY omit the field. They run
  in contributor sessions and benefit from contributor CLAUDE.md / repo
  conventions context.

## Size Limits

- Target: 300 lines; hard limit: 365
- Description: <= 250 characters (agent descriptions are shorter than skill descriptions)
