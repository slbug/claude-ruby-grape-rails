# Verification-Output Compression — Telemetry Foundation

Hook-driven **measurement** of long shell output from verification
commands. Captures real-world compression potential; does **not**
replace the Bash tool stdout the model receives.

**Opt-in only.** The collector is disabled by default. Set
`RUBY_PLUGIN_COMPRESSION_TELEMETRY=1` to enable; until then nothing is
written to disk. This is privacy-respecting on purpose: the data this
collector produces is contributor-grade telemetry that may include
file paths and command shapes from your project, and the user is the
only one who should choose whether to record it.

## What this ships

- `PostToolUse` hook on `Bash` that, **when
  `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1`**, runs after a triggered
  verify command (rspec, rubocop, standardrb, brakeman, reek,
  `rails db:*`, whitelisted rake targets, with `rake_excluded`
  overriding `rake_verify_only`). When the env var is unset (the
  default), the hook exits 0 immediately.
- For each match (env var enabled): appends a JSONL stats entry to
  `${CLAUDE_PLUGIN_DATA}/compression.jsonl` and preserves raw stdout
  under `${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log`.
- Reader CLI `bin/compression-stats` aggregates the jsonl on demand
  (also a no-op when no jsonl exists).
- `SessionStart` advisory hook nudges the user when accumulated
  telemetry crosses either threshold from `rules.yml`
  (`advisory.size_threshold_bytes`, `advisory.sample_threshold`). The
  hook is read-only — it never deletes or rewrites telemetry. The
  advisory surfaces the relevant on-disk paths (jsonl + verify-raw
  directory). It deliberately does NOT print literal `rm` / `rm -rf`
  command strings into the SessionStart context — a model re-reading
  that context could otherwise misinterpret them as self-delete
  instructions. The user composes the cleanup command from the
  surfaced paths.
- `/rb:compression-report` skill bridges the reader to a markdown
  report draft. `compression-stats --redact` is the skill's
  intermediate input (privacy-reduced JSON), not the user-facing
  artifact: the skill drafts a markdown report from the redacted
  aggregate plus selective raw-log Reads, and the user reviews the
  markdown before filing it as a GitHub issue.

## Why no replacement (yet)

The original design called for an opt-in mode that would replace the
Bash tool stdout with a compressed form. That mechanism does not exist
for non-MCP tools. Per the Anthropic Claude Code hooks docs:

- A `PostToolUse` hook's plain stdout is written to the debug log; it
  is not added to the transcript or the model's context. The only
  events whose stdout becomes context are `UserPromptSubmit`,
  `UserPromptExpansion`, and `SessionStart`.
- The PostToolUse decision-control fields (`additionalContext`,
  `decision`, `reason`) layer extra context onto Claude rather than
  replacing the tool output. The only field that replaces output —
  `updatedMCPToolOutput` — is scoped to MCP tools and does not apply
  to `Bash`.

Net effect: an in-place "compress what the model receives" cannot be
implemented inside `PostToolUse`. The repo's own hook-development rule
already states this ("PostToolUse stdout is verbose-mode only — use
`exit 2` + stderr to feed messages to Claude").

A real replacement mechanism (PreToolUse rewrite, additionalContext
layer-add, or pre-compaction) is deferred until telemetry quantifies
which workloads actually benefit. The contributor reader is the
operator surface for that decision.

## Why collect anyway

Two recent reference points for terminal-output compression:

- TACO (Ren et al., *A Self-Evolving Framework for Efficient Terminal
  Agents via Observational Context Compression*, arxiv:2604.19572)
  reports ~10% token-overhead reduction.
- ACON (Kang et al., *ACON: Optimizing Context Compression for
  Long-horizon LLM Agents*, arxiv:2510.00615) reports 26-54%
  peak-token reduction on long-horizon agent tasks.

These are *bytes-into-the-model* metrics, achievable via redesign of
where compression sits in the toolchain. Before redesign, this plugin
collects real-world ratios on Ruby-stack verify commands so a future
release can prove the win is workload-relevant before doing the work.

## Promotion criteria (operator side)

The future release that ships replacement should land only when
`bin/compression-stats` reports, against ≥ 100 real samples per
command class:

- Zero preservation violations across the sample.
- Strong p50 (not just mean) compression ratio — a long tail of
  uncompressible runs should not be hidden by a few large wins.
- No command family consistently underperforming (`rake db:migrate`,
  for example, may dominate one class).
- Manual review of the worst 10 samples confirms rule integrity.

## Safety

- Preservation list in `rules.yml` is authoritative — never drop listed
  patterns.
- Raw output preserved under
  `${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log` and aggregated stats
  under `${CLAUDE_PLUGIN_DATA}/compression.jsonl`. Plugin does not
  auto-delete: the user opted in to collection, and they decide when
  to clean up. A `SessionStart` advisory hook surfaces a
  cleanup-paths message (the on-disk paths only — no literal `rm` /
  `rm -rf` command strings) once accumulated telemetry crosses
  either `rules.yml` `advisory.size_threshold_bytes` or
  `advisory.sample_threshold`.
- **Fail-open:** if `ruby` is unavailable, or the CLI binaries are
  missing / not executable, or the rules file is unreadable, the hook
  exits silently and the raw Bash output is preserved unchanged.
  Compression measurement is best-effort, never a gating step.
- **No destructive code path.** The plugin ships no command that
  deletes telemetry. The advisory hook is read-only; cleanup is a user
  action via plain `rm`.

## Runtime

Plugin runtime is Ruby (≥ 3.4) — the same baseline the plugin already
assumes for end users. No Python, no PyYAML on user machines. YAML
loading uses Ruby stdlib `yaml`. Contributor eval
(`make eval-compression`) stays in `lab/eval/` Python and shells out
to the Ruby CLI.

Concurrent invocations append to `compression.jsonl` under an
exclusive `flock`, so JSONL line integrity is preserved even when
Claude pipelines tool calls.

## Interaction with `rtk` (PreToolUse command rewriter)

[rtk](https://github.com/rtk-ai/rtk) installs a global `PreToolUse`
hook that rewrites verification commands (e.g. `rspec spec/foo` →
`rtk rspec spec/foo`) and emits structured JSON instead of raw test
output.

This plugin's triggers (`^rspec\b`, `^bundle exec rspec\b`, …) do
**not** match `rtk *`, so:

- No double-measurement. The hook exits silently when rtk has
  rewritten the command.
- If rtk is configured to rewrite every verify invocation, this
  collector becomes a no-op for that user. That is intended — rtk's
  JSON output is already compact and structured; running stack/gem
  collapsers over it would corrupt it.

Users of this plugin without rtk get the full collector. Users
running both keep rtk's output. If you want this collector to also
act on rtk-rewritten commands, extend `triggers.yml`
`verify_commands.direct` with
`^rtk (rspec|rubocop|standardrb|brakeman|reek)\b` *and* add a
JSON-detection short-circuit to `lib/verify_compression.rb` so JSON
payloads pass through unchanged.

## Fixture-eval gate

`make eval-compression` runs the fixture set. Success threshold:
≥ 40% mean **bytes** reduction (note: bytes, not tokens — this is the
upper-bound potential, not delivered savings; see "Why no replacement"
above for why delivered savings are deferred), zero preservation
violations, ≤ 15% diff against expected output.

## Telemetry reader

`bin/compression-stats` is the operator surface. It is shipped in the
plugin tree, so when the plugin is enabled it sits on the Bash tool
PATH; end users invoke it directly:

```text
compression-stats                  # human-readable report
compression-stats --json           # machine-readable JSON
compression-stats --log <path>     # alternate jsonl source
```

The reader reads `${CLAUDE_PLUGIN_DATA}/compression.jsonl` (default)
and reports:

- Sample count.
- Mean / p50 / p95 compression ratio (overall and per command class).
- Top weak-savings commands (ratio < 20%).
- Preservation-violation count.
- A textual recommendation against the promotion criteria above.

Contributors developing changes against the reader can run the binary
directly from the repo (`plugins/ruby-grape-rails/bin/compression-stats`)
or via the contributor test suite
(`pytest lab/eval/tests/test_compression_stats.py`). There is no
contributor `make` target — the reader is end-user tooling, not part
of the eval gate.
