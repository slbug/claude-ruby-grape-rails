# Conditional Sections for Injectable Template

Each placeholder in `injectable-template.md` renders only PROJECT-SPECIFIC
detected or interview-collected items. Generic library defaults and
already-injected Iron Laws / Preferences MUST NOT be written into
`CLAUDE.md`. If detection + interview produce zero project-specific
content for a section, render it as an empty string (omit the section
entirely).

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
| Format as a `**{Stack} (project)**:` bolded label followed by 1–6 bullets. No verbose narration. |
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

| Source | What to render |
|---|---|
| `PACKAGE_LOCATIONS` (per-package ORM) | `**ORM map**: <pkg> → AR, <pkg> → Sequel, ...` |

Omit if the per-package map cannot be assembled.

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

Render IF Packwerk detected OR `PACKAGE_LAYOUT` indicates a modular
monolith.

| Source | What to render |
|---|---|
| `PACKAGE_LOCATIONS` | `**Packages**:` followed by a bulleted list of `path → declared boundary` pairs |
| `packwerk.yml` `enforce_dependencies` / `enforce_privacy` | `**Enforcement**: dependencies=<bool>, privacy=<bool>` |

Omit bullets without detected values.

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
| `{RUBY_VERSION}` | `ruby --version` / detect-stack | 3.4.7 |
| `{RAILS_VERSION}` | Gemfile.lock / detect-stack | 7.1.3 |
| `{GRAPE_VERSION}` | Gemfile.lock | 2.0.0 |
| `{SIDEKIQ_VERSION}` | Gemfile.lock | 7.2.0 |
| `{OPTIONAL_STACK}` | Comma-prefixed extra versioned deps from detector output when available | `, Karafka 2.5.8, Hotwire detected` |
| `{SIDEKIQ_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{SEQUEL_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{MIXED_ORM_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{HOTWIRE_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{KARAFKA_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{PACKWERK_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{BETTERLEAKS_SECTION}` | Render per rules above; empty string if no project-specific content |
| `{BETTERLEAKS_STATUS}` | `command -v betterleaks` result | available / missing |
| `{PLUGIN_VERSION}` | `jq -r '.version // empty' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"` | 1.16.6 |

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
