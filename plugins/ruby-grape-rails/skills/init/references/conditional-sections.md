# Conditional Sections for Injectable Template

Render each placeholder in `injectable-template.md` with PROJECT-SPECIFIC
detected or interview-collected items only. Reject generic library
defaults and already-injected Iron Laws / Preferences. Render empty
string (omit section entirely) when detection + interview produce zero
project-specific content.

## Render Procedure (per section)

Two-step, in this order:

1. **DETECT.** Run every detection rule listed for the section against
   the current repo (file scan, `detect-stack` keys, config-file parse).
   Collect every concrete project-specific value found.
2. **INTERVIEW.** For each section item where detection was inconclusive
   (file present but value ambiguous, multiple candidates, `detect-stack`
   key missing or empty, or detected pattern needs disambiguation), ask
   the user one targeted question. Skip detected items that already
   have unambiguous values.

After detect + targeted interview: render the section using only
project-specific content. If both passes leave the section empty,
omit it.

## Authoring Rules (apply to every section)

| Rule |
|---|
| Do NOT restate Iron Laws or Advisory Preferences. The runtime injector delivers them on `SessionStart` + `SubagentStart`. |
| Do NOT inject library defaults (e.g. "Workers MUST include `Sidekiq::Job`", "Use `turbo_frame_tag`"). Only project-specific deviations or detected facts. |
| Render only items derived from `detect-stack` output or from interview answers in the current `/rb:init` run. |
| Empty section → omit. Do NOT leave a header without content. |
| Render shape per section: each "What to render" cell below is the literal output line; emit those bullets as-is, one per detected/asked item. No verbose narration, no extra wrapper headings. |
| Do NOT skip detection in favor of interview — detect-stack output is authoritative for items it covers. |
| Do NOT skip interview when detection is ambiguous — guessing produces drift. |

## SIDEKIQ_SECTION

Render IF Sidekiq detected AND any of the following project-specific
facts are available; otherwise omit.

| Source | What to render |
|---|---|
| `config/sidekiq.yml` queue list | `**Queues**: <name>(<weight>), <name>(<weight>), ...` |
| Detected non-default base class (e.g. `ApplicationJob`, custom worker) | `**Base class**: <ClassName>` |
| Interview answer on retry strategy | `**Retry policy**: <answer>` |
| Detected dead-letter / morgue queue config | `**Dead letter**: <queue or path>` |

Skip any of the above bullets when no detected/asked value exists.

## SEQUEL_SECTION

Render IF Sequel detected.

| Source | What to render |
|---|---|
| `PACKAGE_LOCATIONS` / `DETECTED_ORMS` | `**Sequel-owned packages**: <comma-separated paths>` |
| Detected `dataset_module` patterns / interview answer | `**Custom query convention**: <pattern>` |
| Detected `db/migrations/` (Sequel) vs `db/migrate/` (AR) split | `**Migration roots**: Sequel=<path>, AR=<path>` |

Omit bullets without detected/asked values. Omit section if nothing
project-specific.

## MIXED_ORM_SECTION

Render IF `DETECTED_ORMS` includes both `active_record` AND `sequel`.
`detect-stack` does NOT emit per-package ORM ownership — it lists
package paths in `PACKAGE_LOCATIONS` only. Per-package ORM mapping
must come from a targeted interview question. Ask the user once:
`Both Active Record and Sequel detected. Which ORM owns each package
(<comma-separated paths from PACKAGE_LOCATIONS>)? Reply with one
"<path> -> AR" or "<path> -> Sequel" per line, or "skip" if not yet
mapped.`

| Source | What to render |
|---|---|
| Interview answer mapping each `PACKAGE_LOCATIONS` path to its ORM | `**ORM map**: <pkg> → AR, <pkg> → Sequel, ...` |

Omit if the user skips or detection produces no package paths.
Do NOT fabricate ORM ownership from package names alone.

## HOTWIRE_SECTION

Render IF Hotwire/Turbo detected.

| Source | What to render |
|---|---|
| `app/channels/*.rb` | `**Channels**: <ChannelName>, ...` |
| Detected Turbo Stream broadcast targets in models | `**Broadcast roots**: <Model> → <stream-name>` |
| Interview answer on Frame ID convention | `**Frame ID convention**: <answer>` |

Omit bullets without detected values. Omit section if empty.

## KARAFKA_SECTION

Render IF Karafka detected.

| Source | What to render |
|---|---|
| `karafka.rb` topic routes | `**Consumed topics**: <topic>(<consumer>), ...` |
| Detected consumer base class | `**Base consumer**: <ClassName>` |
| Interview answer on retry routing | `**Retry routing**: <answer>` |

Omit bullets without detected values.

## PACKWERK_SECTION

Render IF Packwerk detected (`HAS_PACKWERK=true`) OR `PACKAGE_LAYOUT`
indicates a modular monolith. `detect-stack` emits raw package paths
in `PACKAGE_LOCATIONS` only — no boundary labels. Read `packwerk.yml`
plus each package's `package.yml` (Packwerk per-package metadata)
for enforcement flags and boundary names. Do NOT fabricate boundary
labels from path names.

| Source | What to render |
|---|---|
| `PACKAGE_LOCATIONS` | `**Packages**: <comma-separated paths>` |
| `packwerk.yml` `enforce_dependencies` / `enforce_privacy` keys | `**Enforcement**: dependencies=<true\|false>, privacy=<true\|false>` |
| Per-package `<pkg>/package.yml` `enforce_dependencies` / `enforce_privacy` overrides | `**Per-package enforcement overrides**: <pkg>=<dep:bool,priv:bool>, ...` |

Omit any bullet whose source is missing or unparsable.

## BETTERLEAKS_SECTION

Render IF `command -v betterleaks` succeeds AND project has
detected sensitive-path conventions.

| Source | What to render |
|---|---|
| Detected `.gitignore` entries for `*.env`, `*.key`, etc. | `**Project secret-path conventions**: <list>` |
| Interview answer on pre-commit scan policy | `**Scan policy**: <answer>` |

If the only available content is generic install instructions or
generic command examples, omit the section. Generic Betterleaks usage
belongs in `/rb:secrets` skill body, not in project `CLAUDE.md`.

## Placeholder Substitution

| Placeholder | Source | Example |
|---|---|---|
| `{DATE}` | Current date | 2026-05-04 |
| `{RUBY_VERSION}` | `detect-stack` `INTERPRETER_RUBY_VERSION` (locked → `RUBY_VERSION` from Gemfile.lock) | 3.4.7 |
| `{RAILS_VERSION}` | `detect-stack` `RAILS_VERSION` | 7.1.3 |
| `{GRAPE_VERSION}` | `detect-stack` `GRAPE_VERSION` | 2.0.0 |
| `{SIDEKIQ_VERSION}` | `detect-stack` `SIDEKIQ_VERSION` | 7.2.0 |
| `{OPTIONAL_STACK}` | `detect-stack` extra-stack keys, comma-prefixed | `, Karafka 2.5.8, Hotwire detected` |
| `{SIDEKIQ_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{SEQUEL_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{MIXED_ORM_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{HOTWIRE_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{KARAFKA_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{PACKWERK_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{BETTERLEAKS_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{BETTERLEAKS_STATUS}` | `command -v betterleaks` result | available / missing |
| `{PLUGIN_VERSION}` | `jq -r '.version // empty' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"` | 1.16.7 |

## Detection Commands

```bash
${CLAUDE_PLUGIN_ROOT}/bin/detect-stack
command -v betterleaks &>/dev/null && echo "betterleaks"
```

Compose the header from `detect-stack` output:

- Prefer exact `*_VERSION` outputs from the script. Fall back to
  `detected` only when the direct gem is present but no resolved
  version is available from `Gemfile.lock`.
- Read `DETECTED_ORMS` / `PACKAGE_LAYOUT` / `PACKAGE_LOCATIONS`.
- If `PACKAGE_QUERY_NEEDED=true`, ask the user for module/package
  locations and stack details.

`detect-stack` is the only supported stack detector. Do NOT
recreate its logic inline. If it is missing or fails, stop and
surface that as a plugin/detection issue rather than guessing.
