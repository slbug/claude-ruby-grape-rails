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

Render IF Sequel detected. Do NOT label every package as Sequel-owned
in mixed AR + Sequel repos — `PACKAGE_LOCATIONS` is the full path list,
not an ownership map.

| Source | What to render | Condition |
|---|---|---|
| `PACKAGE_LOCATIONS` (all paths) | `**Sequel-owned packages**: <comma-separated paths>` | ONLY when `DETECTED_ORMS` is exactly the literal string `sequel` (single-ORM Sequel project). `detect-stack` emits `DETECTED_ORMS=<comma-joined>`, so mixed repos read as `active_record,sequel` — skip and let `MIXED_ORM_SECTION` handle ownership via interview. |
| Detected `dataset_module` patterns OR interview answer | `**Custom query convention**: <pattern>` | always |
| Detected `db/migrations/` (Sequel) AND `db/migrate/` (AR) directories present | `**Migration roots**: Sequel=<path>, AR=<path>` | only when both directories exist |

Omit bullets without detected/asked values. Omit section if nothing
project-specific.

## MIXED_ORM_SECTION

Render IF `DETECTED_ORMS` includes both `active_record` AND `sequel`.
Ask the user once for per-package ORM ownership:

```text
Both Active Record and Sequel detected. Which ORM owns each package
(<comma-separated paths from PACKAGE_LOCATIONS>)? Reply with one
"<path> -> AR" or "<path> -> Sequel" per line, or "skip" if not yet
mapped.
```

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
indicates a modular monolith. Read `packwerk.yml` and each package's
`package.yml` for enforcement flags and boundary names. Do NOT
fabricate boundary labels from path names.

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
| `{STACK_HEADER}` | Composed: always emit `Ruby <RUBY_VERSION>`. Append `, Rails <RAILS_VERSION>` ONLY when `detect-stack` emits `RAILS_VERSION`. Same conditional rule for `, Grape <GRAPE_VERSION>` and `, Sidekiq <SIDEKIQ_VERSION>`. Append `{OPTIONAL_STACK}` (already comma-prefixed) for extra detected stacks. Omit any stack whose version is absent — do NOT emit a bare label (e.g. literal `Rails` followed by empty version). | `Ruby 3.4.7, Rails 7.1.3, Grape 2.0.0, Sidekiq 7.2.0, Karafka 2.5.8` |
| `{RUBY_VERSION}` | `detect-stack` `RUBY_VERSION` (project's pinned Ruby; falls back to interpreter's `RUBY_VERSION` constant when no project pin found). `INTERPRETER_RUBY_VERSION` only emitted when interpreter differs from project pin — informational, not the placeholder source. | 3.4.7 |
| `{RAILS_VERSION}` | `detect-stack` `RAILS_VERSION` (absent on non-Rails projects — drives `{STACK_HEADER}` omission) | 7.1.3 |
| `{GRAPE_VERSION}` | `detect-stack` `GRAPE_VERSION` (absent on non-Grape projects) | 2.0.0 |
| `{SIDEKIQ_VERSION}` | `detect-stack` `SIDEKIQ_VERSION` (absent on non-Sidekiq projects) | 7.2.0 |
| `{OPTIONAL_STACK}` | `detect-stack` extra-stack keys, comma-prefixed; consumed by `{STACK_HEADER}` composition | `, Karafka 2.5.8, Hotwire detected` |
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
