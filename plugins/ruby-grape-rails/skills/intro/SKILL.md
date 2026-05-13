---
name: rb:intro
description: "Walking a user through the Ruby/Rails/Grape plugin commands, capabilities, and workflow. Tutorial-style intro for newcomers who want to learn what the plugin offers rather than tackle a specific task. Triggers: \"tutorial\", \"what can you do\", \"show commands\", \"help with plugin\", \"getting started\". Do NOT use for: working on a specific task (route via intent-detection)."
argument-hint: "[--section N]"
effort: low
disable-model-invocation: true
---
# Intro

Interactive introduction to the Ruby/Rails/Grape plugin for new users.

## Quick Start

1. **Plan a feature**: `/rb:plan Add user authentication with Devise`
2. **Work the plan**: `/rb:work .claude/plans/user-authentication/plan.md`
3. **Verify & Review**: `/rb:verify` then `/rb:review`

## What You Get

- **19 specialist agents**: ActiveRecord, Hotwire, security, Sidekiq, provenance experts
- **52 skills**: Commands for every phase of development
- **22 Iron Laws**: Non-negotiable rules enforced automatically
- **Domain reference skills**: Routed via NL on description; reach manually via `/rb:*` slash invocation

## Installation Notes

**Marketplace Install (Important)**

When installing from the Claude Code marketplace, the plugin's specialist agents will prompt for permissions on first use.
This is a security restriction — plugin agents follow your session permission policy, so project-level `permissions.allow` rules are the normal fix.

**Workarounds:**

1. Add permissions to your project's `.claude/settings.json`:
   - Command rules: `Bash(bundle *)`, `Bash(rails *)`, `Bash(rake *)`,
     `Bash(mkdir -p **/.claude/**)`,
     `Bash(*/bin/manifest-update *)`,
     `Read(*)`, `Grep(*)`, `Glob(*)`
   - Recursive Write rules for plugin artifact namespaces:
     `Write(**/.claude/plans/**)`, `Write(**/.claude/reviews/**)`,
     `Write(**/.claude/audit/**)`, `Write(**/.claude/research/**)`,
     `Write(**/.claude/solutions/**)`,
     `Write(**/.claude/skill-metrics/**)`,
     `Write(**/.claude/investigations/**)`
2. Run `/update-config` to apply the recommended Write allowlist without hand-editing
3. Run `/rb:permissions` to generate a narrower project allowlist from recent usage
4. Use `--plugin-dir` for local development while iterating on the plugin itself
5. Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your shell. Enables
   `SendMessage` so spawn-fanout skills can resume agents that paused
   at `maxTurns`. Without it, paused agents become coverage gaps.

See CLAUDE.md "Conventions → Agents" section for details.

## Detailed Tutorial

See `${CLAUDE_SKILL_DIR}/references/tutorial-content.md` for the complete walkthrough with:

- Core workflow commands and decision guide
- Knowledge & safety net (Iron Laws, auto-loading)
- Hooks & behavioral rules explanation
- Command cheat sheet and best practices
- Claude Code built-in features (`xhigh`, `/focus`, `/recap`,
  `/less-permission-prompts`, `/output-styles`)
- Keeping `CLAUDE.md` small + scoped-rule pattern

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Feature still fuzzy → `/rb:brainstorm` (workflow on-ramp; pre-plan discovery)
- Pattern reference needed → `/rb:examples` (codebase pattern surface)
<!-- END-GENERATED related-footer -->
