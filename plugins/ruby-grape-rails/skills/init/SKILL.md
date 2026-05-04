---
name: rb:init
description: "Use when initializing the Ruby/Rails/Grape plugin in a project. Writes a managed block of project-specific stack notes (queue list, ORM-per-package map, package layout) into CLAUDE.md so /rb:plan, /rb:work, /rb:review, and /rb:verify operate with current stack context. Iron Laws and preferences are runtime-injected via SessionStart + SubagentStart hooks."
when_to_use: "Triggers: \"initialize plugin\", \"setup ruby plugin\", \"install plugin\", \"configure Claude for Rails\"."
argument-hint: "[--update]"
effort: low
---
# Plugin Initialization

Write a managed block of project-specific stack notes into the
project's `CLAUDE.md` so downstream `/rb:*` skills operate with
current stack context. Behavioral rules (Iron Laws, Advisory
Preferences) are runtime-injected via the `inject-rules.sh` hook on
`SessionStart` + `SubagentStart`; they are NOT written to
`CLAUDE.md`.

## Usage

- `/rb:init` — Fresh install
- `/rb:init --update` — Update existing managed block

## Detect the Stack

Check the project before writing anything.

Detection rules:

1. **Always run** `${CLAUDE_PLUGIN_ROOT}/bin/detect-stack` first.
2. **Prefer exact `*_VERSION` values** from that script when writing the managed-block header.
3. Use plain `detected` only as a last resort when a direct gem is present but no resolved lockfile version is available.
4. **Never** use broad substring regexes like `/rails \(([^)]+)\)/` against raw `Gemfile.lock`; they can falsely match gems such as `rubocop-rails`.
5. Read these detector keys before deciding what ORM/package
   guidance to inject:
   - ORM: `DETECTED_ORMS`, `PRIMARY_ORM`
   - Rails shape: `RAILS_COMPONENTS`, `FULL_RAILS_APP`
   - Ruby: `RUBY_VERSION` (project pin; falls back to interpreter when no pin). `INTERPRETER_RUBY_VERSION` is informational only — emitted when interpreter differs from project pin.
   - Packages: `PACKAGE_LAYOUT`, `PACKAGE_LOCATIONS`, `HAS_PACKWERK`,
     `PACKAGE_QUERY_NEEDED`
6. If `PACKAGE_QUERY_NEEDED=true`, ask the user: `No Packwerk detected. Do you have something similar implemented? Provide modules/packages location and their stack/ORM.`
7. **Do not** reimplement stack detection inline in chat or ad-hoc Ruby snippets. `detect-stack` is the source of truth.
8. If `${CLAUDE_PLUGIN_ROOT}/bin/detect-stack` is missing or fails, STOP and explain that plugin stack detection is unavailable instead of inventing a fallback parser.

Use Ruby for detection (avoids fragile shell pipelines):

1. Run `${CLAUDE_PLUGIN_ROOT}/bin/detect-stack` to detect Ruby version and stack dependencies.
2. Read `.claude/.runtime_env` (if present and non-symlink) for cached external tool
   booleans: `RTK_AVAILABLE`, `DCG_AVAILABLE`, `SHELLFIRM_AVAILABLE`.
3. Check `command -v betterleaks`, `command -v rtk`, `command -v dcg`,
   `command -v shellfirm` as fallbacks when cached values are absent.

When building the injected header:

- omit Rails entirely when `RAILS_VERSION` is absent
- prefer detected version values from `detect-stack` / cached runtime state instead of hardcoded examples
- avoid degrading locked versions to `detected`
- use `DETECTED_ORMS` to distinguish Active Record, Sequel, and mixed ORM repositories
- use `PACKAGE_LAYOUT` / `PACKAGE_LOCATIONS` to decide whether package-boundary guidance belongs in the injected block
- set `BETTERLEAKS_STATUS` to `available` when `command -v betterleaks` succeeds; otherwise use `missing`
- set `PLUGIN_VERSION` from
  `jq -r '.version // empty' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"`
  — do not improvise or omit; the SessionStart `check-plugin-version.sh` hook
  depends on this marker being present and deterministic
- when `.claude/.runtime_env` is present, use its tool booleans to understand whether the project has `standardrb`, `rubocop`, `brakeman`, `lefthook`, and `pronto`
- when `.claude/.runtime_env` exposes `VERIFY_COMPOSITE_AVAILABLE=true`, treat that as a hint that the repo may have a canonical composite verify entrypoint
- re-detect any composite verify command from the working tree before running it; do not execute a raw command string from `.claude/.runtime_env`

Optional external integration:

- prefer `RTK_AVAILABLE=true` from a non-symlink `.claude/.runtime_env` when present; otherwise fall back to `command -v rtk`
- if RTK is available, ask the user whether they want to enable RTK for Claude Code
- if they say yes, tell them: `For automatic Claude command rewriting, run: rtk init -g`
- do **not** inject long RTK command-preference rules into the project
- RTK hook installation is external to this plugin; detection alone does not make Claude use RTK
- prefer `DCG_AVAILABLE=true` from a non-symlink `.claude/.runtime_env` when present; otherwise fall back to `command -v dcg`
- if DCG is available, ask the user whether they want to enable DCG for Claude Code
- if they say yes, tell them: `For Claude Code destructive-command blocking, run: dcg setup`
- if they want the recommended `dcg` TOML or the manual hook shape, use `${CLAUDE_SKILL_DIR}/references/external-integrations.md`
- DCG hook installation is external to this plugin; detection alone does not make Claude use DCG
- prefer `SHELLFIRM_AVAILABLE=true` from a non-symlink `.claude/.runtime_env` when present; otherwise fall back to `command -v shellfirm`
- if Shellfirm is available, ask the user whether they want to connect Shellfirm to Claude Code
- if they say yes, tell them: `For Claude Code hook and MCP safety tooling, run: shellfirm connect claude-code`
- if they want a project-policy starting point, use `${CLAUDE_SKILL_DIR}/references/external-integrations.md` for the recommended scope and boundaries, but do not invent a generic `.shellfirm.yaml`
- Shellfirm hook and MCP installation are external to this plugin; detection alone does not make Claude use Shellfirm
- use `${CLAUDE_SKILL_DIR}/references/external-integrations.md` for the exact recommended setup commands

Verification/tooling policy:

- direct tools remain the source of truth:
  - `standardrb` or `rubocop` for lint/format
  - `brakeman` for security scanning
- `lefthook` is only preferred as a wrapper when its detected config covers both lint and security/static-analysis checks
- `LEFTHOOK_DIFF_LINT_COVERED=true` means Lefthook covers diff-scoped lint via Pronto/RuboCop, not full direct lint coverage
- if `LEFTHOOK_AVAILABLE=true` but no config path is detected, ask the user whether Lefthook is used and where its config lives
- tests stay separate from Lefthook policy; keep them targeted or full based on the actual change scope
- `pronto` is optional diff-scoped review tooling:
  - use it after direct lint/security checks
  - do not use it as a substitute for full lint or security verification
- if runtime detection found a project-native verify wrapper
  (`VERIFY_COMPOSITE_AVAILABLE=true`), re-detect it from the repo and prefer it
  first in `/rb:verify`; fall back to direct checks only when the wrapper
  itself is unavailable or broken locally

## Install Modes

- Fresh install: append a managed block to `CLAUDE.md`
- Update mode: replace the content between markers only

Managed block markers:

```markdown
<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
...
<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
```

### Iron Laws + Preferences delivery

Iron Laws and Advisory Preferences are delivered at runtime by the
plugin's `inject-rules.sh` hook, wired in `hooks.json` under both
`SessionStart` (main-session delivery) and `SubagentStart` (per-subagent
delivery). They are not written into `CLAUDE.md`. Running
`/rb:init --update` on a project that has the legacy inline blocks
(from earlier plugin versions) replaces the whole managed block with
the current template, removing the `<!-- IRON_LAWS_START -->` /
`<!-- PREFERENCES_START -->` blocks automatically.

## What Gets Installed

The injected managed block contains ONLY project-specific stack
notes — nothing that already lives in runtime injection or in skill
bodies:

- stack-version comment header (Ruby / Rails / Grape / Sidekiq /
  optional stack / Betterleaks / plugin version)
- conditional sections rendered from `detect-stack` output plus
  targeted interview answers — queue list, ORM-per-package map,
  Karafka topic routes, Packwerk enforcement flags, Hotwire
  channels, project secret-path conventions

What is NOT installed (delivered elsewhere):

| Surface | Where it lives |
|---|---|
| Iron Laws + Advisory Preferences | runtime hook `inject-rules.sh` on `SessionStart` + `SubagentStart` |
| Skill workflow / spawn rules / verification commands | individual skill bodies (`/rb:plan`, `/rb:review`, `/rb:verify`, ...) |
| Library defaults (Sidekiq base class, Turbo Frame patterns, etc.) | framework docs, not project CLAUDE.md |

## Template

Use `${CLAUDE_SKILL_DIR}/references/injectable-template.md` as the injected source of truth.

## Conditional Sections

Render each placeholder ONLY when BOTH conditions hold: stack/tool
detected AND project-specific content available (from `detect-stack`
output or targeted interview). Empty section → omit; do NOT leave a
header without content.

| Placeholder | Detection gate | Content source |
|---|---|---|
| `{SIDEKIQ_SECTION}` | Sidekiq detected | queue list, base class, retry policy, dead-letter config |
| `{SEQUEL_SECTION}` | Sequel detected | per-package paths, query convention, migration roots |
| `{MIXED_ORM_SECTION}` | Active Record AND Sequel detected | per-package ORM map (from targeted interview — `detect-stack` does NOT emit per-package ORM ownership) |
| `{HOTWIRE_SECTION}` | Hotwire/Turbo detected | channel list, broadcast roots, frame-id convention |
| `{KARAFKA_SECTION}` | Karafka detected | topic routes, consumer base, retry routing |
| `{PACKWERK_SECTION}` | Packwerk OR modular monolith layout detected | package paths from `PACKAGE_LOCATIONS`; enforcement flags from `packwerk.yml` + per-package `package.yml` |
| `{BETTERLEAKS_SECTION}` | `betterleaks` available AND project secret-path conventions detected | secret-path conventions, scan policy |

`${CLAUDE_SKILL_DIR}/references/conditional-sections.md` is the
canonical procedure (per-section detect rules, interview prompts,
render shape, authoring rules). Read it before rendering.

## Recommended Permission Allowlist

Prompt the user to run `/update-config` to add these recursive Write
rules to `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(bundle *)",
      "Bash(rails *)",
      "Bash(rake *)",
      "Bash(mkdir -p **/.claude/**)",
      "Bash(*/bin/manifest-update *)",
      "Read(*)",
      "Grep(*)",
      "Glob(*)",
      "Write(**/.claude/plans/**)",
      "Write(**/.claude/reviews/**)",
      "Write(**/.claude/audit/**)",
      "Write(**/.claude/research/**)",
      "Write(**/.claude/solutions/**)",
      "Write(**/.claude/skill-metrics/**)",
      "Write(**/.claude/investigations/**)"
    ]
  }
}
```

Use recursive `**/.claude/<ns>/**` globs. Shallow `Write(.claude/<ns>/*)`
does not match nested artifact paths.

Tell the user: `Run /update-config to add the recommended Write
permission allowlist for plugin artifact namespaces.`

## Recommended Claude Code env vars

Tell the user to set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in their
shell environment. Required for spawn-fanout skills (`/rb:review`,
`/rb:plan`, `/rb:brainstorm`, `/rb:investigate`) to resume agents that
paused at their `maxTurns` cap. Without it, paused agents become
coverage gaps with no recovery path.

## CLAUDE.md sizing

Keep root `CLAUDE.md` under ~200 lines. Heavy repo-level context inflates
inference cost and can reduce task success. Subtree-specific rules belong in
`.claude/rules/*.md` with `paths:` frontmatter so they auto-load only when
relevant.

See `${CLAUDE_PLUGIN_ROOT}/skills/intro/references/tutorial-content.md`
(Section 8) for the rule-of-thumb checklist and the scoped-rule template.
