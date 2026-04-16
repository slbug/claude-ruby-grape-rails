---
name: rb:intro
description: "Use when users want a tutorial walkthrough of plugin commands and capabilities. Use when users want to learn what the plugin offers, not when they already have a specific task to work on."
when_to_use: "Triggers: \"tutorial\", \"what can you do\", \"show commands\", \"help with plugin\", \"getting started\"."
argument-hint: "[--section N]"
effort: low
---
# Intro

Interactive introduction to the Ruby/Rails/Grape plugin for new users.

## Quick Start

1. **Plan a feature**: `/rb:plan Add user authentication with Devise`
2. **Work the plan**: `/rb:work .claude/plans/user-authentication/plan.md`
3. **Verify & Review**: `/rb:verify` then `/rb:review`

## What You Get

- **23 specialist agents**: ActiveRecord, Hotwire, security, Sidekiq, provenance experts
- **51 skills**: Commands for every phase of development
- **22 Iron Laws**: Non-negotiable rules enforced automatically
- **Auto-loaded references**: Context-aware docs loaded when editing relevant files

## Installation Notes

**Marketplace Install (Important)**

When installing from the Claude Code marketplace, the plugin's specialist agents will prompt for permissions on first use.
This is a security restriction — plugin agents follow your session permission policy, so project-level `permissions.allow` rules are the normal fix.

**Workarounds:**

1. Add permissions to your project's `.claude/settings.json` for the commands agents need, such as `Bash(bundle *)`, `Bash(rails *)`, `Bash(rake *)`, `Read(*)`, `Grep(*)`, and `Glob(*)`
2. Run `/rb:permissions` to generate a narrower project allowlist from recent usage
3. Use `--plugin-dir` for local development while iterating on the plugin itself

See CLAUDE.md "Conventions → Agents" section for details.

## Detailed Tutorial

See `${CLAUDE_SKILL_DIR}/references/tutorial-content.md` for the complete walkthrough with:

- Core workflow commands and decision guide
- Knowledge & safety net (Iron Laws, auto-loading)
- Hooks & behavioral rules explanation
- Command cheat sheet and best practices
