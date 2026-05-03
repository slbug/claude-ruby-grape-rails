---
applyTo: "plugins/**"
excludeAgent: "coding-agent"
---

# Plugin File Review Rules

## Agent Conventions (plugins/**/agents/*.md)

- Agents use YAML frontmatter. Common: name, description, model,
  disallowedTools, omitClaudeMd, skills, memory. Also valid per CC docs:
  tools, effort, maxTurns, background, isolation. The general subagent
  reference (<https://docs.claude.com/en/docs/claude-code/sub-agents>)
  also lists `color` and `initialPrompt`, but the plugin-supported set
  documented at <https://docs.claude.com/en/docs/claude-code/plugins-reference>
  does NOT include them — CC silently drops these on plugin-shipped
  agents. Do NOT add them to plugin agents under `plugins/**/agents/`
- Prefer denylist-only (`disallowedTools:`) over allowlist (`tools:`).
  A missing `tools:` field is intentional — agents inherit all tools minus
  those in disallowedTools
- Artifact-writing agents: `disallowedTools: Edit, NotebookEdit, Agent,
  EnterWorktree, ExitWorktree, Skill`
- Conversation-only agents add `Write` to the above
- NO agent declares or invokes `Agent` — orchestration lives in skill bodies
  (main session). See `.claude/rules/agent-development.md` § "Subagents Are
  Leaf Workers" for full doctrine.
- Agents with intentionally narrow tool sets (web-researcher,
  output-verifier, ruby-gem-researcher) use `tools:` allowlists — this is
  correct
- `omitClaudeMd: true` is correct for specialist agents that do not need
  contributor CLAUDE.md context
- Do NOT flag `permissionMode` as missing — Claude Code ignores it on
  plugin agents
- Model tiers: opus for security-critical agents, sonnet for most specialists,
  haiku for mechanical tasks. `opusplan` is a session-level `/model` alias
  only (the subagent frontmatter table at
  <https://docs.claude.com/en/docs/claude-code/sub-agents> does NOT list
  it as a valid subagent `model` value) — do NOT flag its absence from
  agent frontmatter as a gap
- Descriptions must be <= 250 characters

## Skill Conventions (plugins/**/skills/*/SKILL.md)

- Skills use YAML frontmatter. Required: name, description. Common:
  argument-hint (command skills), arguments (positional `$name`
  substitution, space-separated string or YAML list), effort,
  user-invocable, disable-model-invocation, paths (framework-specific
  skills), when_to_use (trigger phrases and negative routing). Also
  valid per CC docs: allowed-tools, model, context, agent, hooks, shell
- No `triggers:` field — skills docs do not support it
- No executable bash blocks (``` bash) — use inline prose instructions
  instead ("Run `bundle exec rspec`")
- Combined description + when_to_use must be <= 1,536 characters
- Descriptions should start with "Use when" for consistent routing signal
- `${CLAUDE_SKILL_DIR}` is a valid runtime variable, not an error
- Iron Laws sections contain numbered non-negotiable rules — do not suggest
  making them optional or softer
- Large workflow skills may be acceptable only when routing-critical;
  prefer references/ for long templates and examples

## Hook Conventions (plugins/**/hooks/)

- hooks.json uses documented Claude Code hook events and types
- Each `if` filter uses a single pattern per hook entry — do NOT combine
  with `|` OR syntax
- `async: true` is only valid on `type: "command"` hooks
- `${CLAUDE_PLUGIN_ROOT}` is a valid runtime variable in hook commands

## bin/ Executables (plugins/**/bin/*)

- No file extension, chmod +x. Mixed languages allowed: bash and Ruby
  shebangs are both first-class
- Header policy comment near the top documents advisory vs fail-closed
  behavior
- bash bin scripts: `set -o nounset` + `set -o pipefail` at the top;
  `command -v <dep> >/dev/null 2>&1 || exit 0` for optional deps
- Ruby bin scripts: `# frozen_string_literal: true` immediately after
  the shebang; rescue at process boundary, never use `Kernel#eval` /
  `Kernel#system` with unvalidated input (Iron Law 12)
- Advisory fail-open pattern (empty stdout, exit 0 on any error) is
  intentional for statusline and similar advisory executables — do NOT
  flag as "missing error handling"
- From `hooks.json`, `.mcp.json`, `monitors/monitors.json`, template
  expansion is supported; reference bundled scripts via
  `${CLAUDE_PLUGIN_ROOT}/...`

### Currently shipped binaries (plugins/ruby-grape-rails/bin/)

- `subagent-statusline` (bash) — advisory, fail-open. Empty stdout +
  exit 0 on any error. Referenced from `settings.json` indirectly via
  `~/.claude/ruby-grape-rails-subagent-statusline` wrapper
- `detect-stack` (Ruby) — `/rb:init` stack detection. Outputs
  `key=value` pairs; treats unreadable manifests as absent
- `extract-permissions` (Ruby) — analyzes session transcripts to
  recommend Bash permission entries; reads `~/.claude/projects/...`
  transcripts read-only
- `resolve-base-ref` (bash) — emits `eval`-able shell assigning
  `BASE_REF` for diff comparisons; handles custom remotes and stale
  local refs
- `compression-stats` (Ruby) — end-user reader for verify-output
  compression telemetry. Reads
  `${CLAUDE_PLUGIN_DATA}/compression.jsonl` (default) or `--log
  <path>`. Default mode prints a human-readable report; `--json`
  emits machine-readable aggregate JSON; `--redact` emits
  privacy-reduced JSON for the `/rb:compression-report` skill —
  intermediate input for the skill's report drafter, NOT a final
  paste-anywhere artifact (the skill's drafted markdown is what the
  user reviews + shares). Stdlib only — no `lib/` dependency,
  contributor or otherwise
- `provenance-scan` (Ruby) — end-user provenance-sidecar auditor.
  Walks `.claude/{research,reviews,audit,plans/*/{research,reviews}}`,
  classifies each `*.provenance.md` via the 4-state algorithm
  (`clean` / `weak` / `conflicted` / `missing`), and writes a dated
  Markdown report under `.claude/provenance-scan/`. Stdlib only;
  pure deterministic — no LLM, no network. Surfaced via
  `/rb:provenance-scan` user-invocable skill
- `manifest-update` (Ruby) — atomic JSON manifest writer for
  spawn-fanout RUN-CURRENT.json files. Subcommands: `prepare-run`
  (structured args: `--skill --slug --agents [--base-ref]`; helper
  computes manifest path, datesuffix, agent paths, consolidated path,
  git pins; outputs absolute manifest path on stdout; archives any
  prior in one call), `field` (extract dotted key from manifest),
  `spawn-paths` (tab-separated agent slug + absolute path per line
  for skill-body iteration), `init` (fail if exists), `patch`
  (deep-merge from stdin, auto-stamps `updated_at`),
  `prepare-respawn` (rotate manifest-tracked agent files to
  `<agent-slug>.stale-<rename-ts>.md`; refuses unless canonical-path
  match + containment + no symlinked ancestor; agent status
  `pending` / `in-flight` / `stub-no-output`), `archive` (append to
  RUN-HISTORY.jsonl + remove RUN-CURRENT.json),
  `resume-check` (read-only verdict: absent / stale /
  fresh-complete / fresh-in-flight), `status` (read-only summary).
  Path allowlist: suffix regex
  `.../.claude/<any-namespace>/RUN-CURRENT.json`. `prepare-run` also
  validates `<any-namespace>` against per-skill templates (e.g.
  `reviews/<review-slug>`, `plans/<plan-slug>/research-fanout`)
  via `--skill`. Lower-level subcommands accept any matching path.
  Containment check via repo-root resolution. Symlink refusal on
  target + parent dir. Atomic write via exclusive temp file (`O_EXCL`) + `fsync` + Ruby
  `File.rename` (POSIX `rename(2)`) + directory `fsync`. Fail-closed
  on path / JSON / IO errors. Stdlib only. Reuses
  `lib/repo_root.rb` + `lib/path_safety.rb`. Skill bodies that mutate
  manifest or rotate stale stubs call this — never raw `mv` / `cp` /
  `jq -i` / `rm`

When adding a binary, also add it to this "Currently shipped
binaries" section above, ensure `chmod +x` is committed, and (if it
is wired into hooks or settings) cross-check `hooks.json` /
`settings.json` references.

## Plugin-owned Ruby Library (plugins/ruby-grape-rails/lib/)

`lib/` holds plugin-owned Ruby modules required by `bin/` CLIs. Each
file is `# frozen_string_literal: true`, uses Ruby ≥ 3.4 idioms
(`Data.define`, pattern matching, `module_function`), and rescues
errors at the process boundary so loader failures fail-open back to
the calling CLI / hook.

- `verify_compression.rb` — deterministic verify-output compressor.
  Loads YAML rules from `references/compression/rules.yml`. Collapses
  stack frames > 5, repeated `Loaded gem` lines, and duplicate
  `DEPRECATION WARNING` blocks. Verifies preserve patterns survive
  compression. Provides `append_jsonl(path, entry)` (symlink-safe +
  flock'd). Used by the PostToolUse / PostToolUseFailure compression
  hook (`hooks/scripts/compress-verify-output.rb`) and the
  contributor CLI (`lab/eval/bin/compress-verify`)
- `triggers.rb` — path-agnostic YAML trigger matcher for verification
  commands. Exposes `matches?(triggers_path, command)` taking the YAML
  path as a parameter; callers (`hooks/scripts/compress-verify-output.rb`,
  `lab/eval/bin/match-trigger`) pass `references/compression/triggers.yml`.
  Handles `rake_excluded` precedence over `rake_verify_only`
- `repo_root.rb` — shared `RubyGrapeRails::RepoRoot` module. Exposes
  `find(start_dir)` (precedence: ascended `.git` dir → `.claude/settings*`
  → `git rev-parse --show-toplevel` → `Gemfile` → start_dir),
  `canonical(path)` (realpath with expand_path fallback),
  `git_toplevel(path)` (Open3-based git rev-parse). Stdlib only.
  Required by `bin/manifest-update`, `bin/extract-permissions`,
  `bin/detect-stack`

Notes:

- `lib/` is end-user runtime, NOT contributor tooling. End users get
  these files. Stay Ruby-only; do NOT introduce a Python runtime
  dependency here. PyYAML is dev-only via `requirements-dev.txt`
- Ruby stdlib `yaml` (Psych) is the canonical YAML loader — no Bundler
  gems required at runtime
- New `lib/<name>.rb` modules MUST also be referenced from a `bin/`
  CLI or hook script; an unreferenced library file is a drift defect

## References & Registries (plugins/**/references/)

Top-level YAML registries:

- `iron-laws.yml` — non-negotiable STOP-if-violated rules; generated
  into README, canonical registry, intro tutorial, injector script
  (`inject-rules.sh`), and iron-law-judge agent via
  `scripts/generate-iron-law-outputs.sh`. Iron Laws are NOT injected
  into the init template — runtime hook delivery via `SessionStart` +
  `SubagentStart` covers both audiences.
- `preferences.yml` — advisory soft-preference rules (parallel registry,
  same schema minus `detector_id`, severity capped at `medium`/`low`);
  appended to the shared injector payload as "Advisory Preferences",
  delivered via the same `inject-rules.sh` hook to both main session
  and subagents.

Subdirectories (treat as data, not skills):

- `references/iron-laws/` — generated canonical Iron Law artifacts and
  source-of-truth registry consumed by the judge agent
- `references/agent-playbooks/` — opinionated playbooks consumed by
  specialist agents (read-only reference content, not skills)
- `references/output-verification/` — schemas and fixtures consumed by
  `output-verifier` agent and `lab/eval/output_checks.py`
- `references/research/` — long-form research notes (`epistemic-posture.md`
  etc.) referenced from CLAUDE.md and skills

Notes:

- Any change to `iron-laws.yml` or `preferences.yml` is a generated-file
  trigger — verify regenerated artifacts ride along in the same PR
  (see `copilot-instructions.md` "Cross-File Consistency")
- Do NOT flag `preferences.yml` references or the generated
  `Advisory Preferences` section as unknown — both are first-class since
  v1.13.0
- `.claude/rules/iron-laws-governance.md` — contributor policy on when
  to add/remove/demote Iron Laws; auto-loads on `**/iron-laws.yml` edits

## Plugin Settings (plugins/**/settings.json)

- Only `agent` and `subagentStatusLine` keys are supported per CC docs
  (`plugins-reference.md` standard plugin layout)
- Unknown keys are silently ignored by CC — do NOT flag partial coverage
  of other settings fields
- `subagentStatusLine.command` does NOT expand `${CLAUDE_PLUGIN_ROOT}`
  and CC does NOT export `CLAUDE_PLUGIN_ROOT` to the statusline
  subprocess nor add plugin `bin/` to its PATH. Plugin-bundled
  statusline scripts therefore require a SessionStart hook that writes
  a small wrapper at `~/.claude/<plugin-id>-subagent-statusline`
  pointing at the current absolute plugin path. The plugin
  `settings.json` then references that stable user-home path. The
  wrapper must be rewritten only when its content differs from the
  desired content (plugin version changes change the absolute path).
  Do NOT flag this indirection as unnecessary — it is required by the
  documented CC substitution scope

### subagentStatusLine payload schema (as observed, not fully documented)

The statusline subprocess receives base hook fields plus `columns` and a
`tasks[]` array. Each task provides `id`, `type` (e.g. `local_agent`),
`status`, `description`, `label` (usually the same text as `description`),
`startTime` as epoch milliseconds (13-digit integer), `tokenCount`,
`tokenSamples` as a number array, and `cwd`. The docs also list `.name`
but current CC payloads do NOT include it — match emoji/label from
`.label` first, falling back to `.description` and finally `.name`. Do
NOT flag the fallback chain as over-engineered.

## Do NOT Flag

- Large file sizes on workflow skills (intentional when routing-critical)
- Missing `tools:` field on agents (denylist-only pattern)
- `omitClaudeMd: true` on specialist agents (intentional context savings)
- Colon-namespaced skill names like `rb:plan` (known compatibility item)
- Advisory fail-open (empty stdout, exit 0) in `bin/` and advisory hooks
- Partial coverage in plugin `settings.json` (only `agent` and
  `subagentStatusLine` are documented as supported)
- Skill or agent files referencing `references/research/tool-batching.md`
  (canonical examples doc for the tool-batching preference)
- Run manifest paths under `.claude/{namespace}/RUN-CURRENT.json`
  and `RUN-HISTORY.jsonl` (cross-session resume contract — see
  `plugins/ruby-grape-rails/references/run-manifest.md`)

## Do FLAG

- `permissionMode: bypassPermissions` on new agents — flag as YELLOW
  unless agent has documented contributor-only privilege need
- Shipped skill bodies (`plugins/ruby-grape-rails/.../SKILL.md`)
  referencing contributor doctrine paths (`.claude/rules/*-development.md`,
  `.github/instructions/*.instructions.md`) — flag as BLOCKER
- Agent frontmatter declaring `Agent` in `tools:` list — flag as BLOCKER
- Agent body containing `Agent(...)` or `subagent_type:` calls — flag as
  BLOCKER
- Agent or skill bodies that restate tool-batching discipline (preferred
  batched git diff / grep / bundle info, exclude noise via pathspec,
  prefer Read/Grep/Glob over `cat`/`find -exec`) — preference injection
  delivers the rule; restatement is duplication. Pointers to
  `references/research/tool-batching.md` for examples are fine.
- Per-item shell loops in agent or skill bodies (e.g.
  `for f in $FILES; do git diff -- "$f"; done`) — replace with batched
  path-group call.
- Consolidated review references using `{review-slug}.md` without the
  `-{datesuffix}` segment — stale path; per-run uniqueness is required
  to avoid subagent Write collisions on existing files.
- Per-reviewer artifacts referenced without the `{datesuffix}` segment.
- Recovery procedures that copy or symlink prior-run artifacts to the
  current-run path (must write a stub when current run produced
  nothing; see `references/run-manifest.md`).
- Subagent bodies that read or write `RUN-CURRENT.json` /
  `RUN-HISTORY.jsonl` — manifest is main-session-owned only.
- Consolidated review template missing the `## Reviewer Coverage`
  section (per-agent recovery state must be surfaced).
- `run_in_background: true` on any `Agent(...)` call in shipped
  skill bodies, fanout templates, or example snippets — flag as
  BLOCKER. Plugin agents dispatch foreground only.
- Raw `mv`, `cp`, `jq -i`, `rm`, or improvised shell against any
  `RUN-CURRENT.json` path or per-agent artifact path in shipped skill
  bodies, hook scripts, or examples — flag as BLOCKER. All manifest
  mutations and stale-stub rotations MUST go through
  `${CLAUDE_PLUGIN_ROOT}/bin/manifest-update`.
