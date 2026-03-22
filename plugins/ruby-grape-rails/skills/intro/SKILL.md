---
name: rb:intro
description: Quick introduction to the Ruby/Rails/Grape plugin workflow and command set.
argument-hint: "[--section N]"
---

# Intro

Interactive introduction to the Ruby/Rails/Grape plugin for new users.

## Quick Start

1. **Plan a feature**: `/rb:plan Add user authentication with Devise`
2. **Work the plan**: `/rb:work .claude/plans/user-authentication/plan.md`
3. **Verify & Review**: `/rb:verify` then `/rb:review`

## What You Get

- **22 specialist agents**: ActiveRecord, Hotwire, security, Sidekiq experts
- **49 skills**: Commands for every phase of development
- **21 Iron Laws**: Non-negotiable rules enforced automatically
- **Auto-loaded references**: Context-aware docs loaded when editing relevant files

## Installation Notes

**Marketplace Install (Important)**

When installing from the Claude Code marketplace, the plugin's specialist agents will prompt for permissions on first use.
This is a security restriction — marketplace plugins cannot use `permissionMode: bypassPermissions`.

**Workarounds:**

1. Use `--plugin-dir` for local development (permissions auto-accepted)
2. Copy agents to `~/.claude/agents/` (one-time setup)
3. Add permissions to your project's `.claude/settings.json`

See CLAUDE.md "Conventions → Agents" section for details.

## Detailed Tutorial

See [references/tutorial-content.md](references/tutorial-content.md) for the complete walkthrough with:

- Core workflow commands and decision guide
- Knowledge & safety net (Iron Laws, auto-loading)
- Hooks & behavioral rules explanation
- Command cheat sheet and best practices
