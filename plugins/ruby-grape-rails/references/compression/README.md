# Verification-Output Compression — Telemetry

| Setting | Value |
|---|---|
| Purpose | Collect local verify-command Bash output for compression analysis. Opt-in only. |
| Captured streams | stdout + stderr on success; top-level `error` blob on `PostToolUseFailure` |
| Replaces tool output? | NO — Bash stdout flows to the model unchanged |
| Activation | Set `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1` to enable. Default OFF; hooks exit silently when unset. |

Data flow:

| Stage | Action |
|---|---|
| Collect | `PostToolUse` / `PostToolUseFailure` hooks on `Bash` append JSONL stats + raw logs to `${CLAUDE_PLUGIN_DATA}` |
| Read | `bin/compression-stats` aggregates JSONL on demand |
| Share | `/rb:compression-report` drafts an anonymized Markdown report from `compression-stats --redact` for the user to file as a GitHub issue |

## End-User Collection

Hook trigger families: `rspec`, `rubocop`, `standardrb`, `brakeman`,
`reek`, `rails db:(migrate|rollback|schema:load|seed)`, and
`(rake|rails) (ci|test|spec|verify|lint|brakeman|...)`.

`rake_excluded` overrides every trigger:

- `(rake|rails) (routes|db:drop|db:create|assets:|stats|notes)`
- `--version` invocations across the verify-tool family
- any command piped into `| tail` / `| head` (operator pre-trim
  produces a sliced output line-oriented collapsers cannot
  meaningfully reduce; recording 0% ratios from those samples
  inflates the underpowered-class denominator)

On match (env var enabled):

- Append a JSONL stats entry to `${CLAUDE_PLUGIN_DATA}/compression.jsonl`.
- Preserve captured Bash output (stdout + stderr on success;
  top-level `error` blob on failure) under
  `${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log`.

`SessionStart` advisory hook (read-only):

- Trigger: accumulated telemetry crosses `advisory.size_threshold_bytes`
  OR `advisory.sample_threshold` from `rules.yml`.
- Output: on-disk paths only. NEVER emit literal `rm` strings — a
  re-read of the SessionStart context could misinterpret them as
  self-delete instructions.
- User composes cleanup commands from the surfaced paths.

## End-User Reader

`bin/compression-stats` ships in the plugin tree; on plugin enable
it sits on the Bash PATH:

```text
compression-stats                  # human-readable report
compression-stats --json           # machine-readable JSON
compression-stats --log <path>     # alternate jsonl source
compression-stats --redact         # privacy-reduced JSON for /rb:compression-report
```

Reports:

- sample count
- mean / p50 / p95 compression ratio (overall + per command class)
- top weak-savings commands (ratio < 20%)
- preservation-violation count
- recommendation against the promotion criteria below

## Sharing a Report

`/rb:compression-report` drafts an anonymized Markdown report from
`compression-stats --redact` plus selective raw-log Reads. Review
the markdown, file it as a GitHub issue. The redacted JSON is
intermediate input — NOT a paste-anywhere artifact.

## Megastring Middle-Collapse

Line-oriented collapsers (stack frames, deprecation runs, repeated
warnings, K-line block dedup) do NOT reduce a single logical line
encoding a large payload (canonical case: inline rspec expectation
diff with full JSON on one line). Megastring pass rewrites every
line whose byte length exceeds `megastring.threshold_bytes`:

1. Keep `keep_head` bytes from the start.
2. Emit the rendered `collapse.megastring` template.
3. Keep `keep_tail` bytes from the end.
4. Elide the middle bytes.

Tunables in `rules.yml`:

| Key | Default | Effect |
|---|---|---|
| `megastring.threshold_bytes` | 2048 | Lines at or below this length pass through. Raise for build banners / schema dumps; lower to chase smaller blobs. |
| `megastring.keep_head` | 500 | Preserves leading identifier (`expected:`, test description, file path). |
| `megastring.keep_tail` | 500 | Preserves terminating syntax (`}`, `)`, `got:`). |

Disable conditions + scrub:

- Pass disables itself when `keep_head + keep_tail >= threshold_bytes`.
- Boundaries byte-aligned. Scrub multibyte UTF-8 split points via
  `String#scrub('')` so downstream regex passes never see invalid
  byte sequences.
- Reported elided-byte count reflects actual surviving sizes after scrub.

## No Bash Replacement Path

| Hook surface | Replaces tool output the model receives? |
|---|---|
| `PostToolUse` (Bash) | NO — stdout goes to debug log only |
| `updatedMCPToolOutput` | YES — MCP-only, not Bash |
| `UserPromptSubmit` / `UserPromptExpansion` / `SessionStart` | stdout becomes context (not a tool-output replacement) |

Defer a real replacement (PreToolUse rewrite, additionalContext
layer-add, or pre-compaction) until telemetry quantifies workload
benefit. `bin/compression-stats` is the operator surface for that
decision.

Reference benchmarks (bytes-into-the-model, NOT this collector's
direct metric):

- TACO (Ren et al., arxiv:2604.19572) — ~10% token-overhead reduction
- ACON (Kang et al., arxiv:2510.00615) — 26-54% peak-token reduction
  on long-horizon agent tasks

This collector measures the upper bound on Ruby-stack verify
commands so a future release can prove workload-relevance before
redesign.

## Interaction with `rtk`

[rtk](https://github.com/rtk-ai/rtk) installs a global `PreToolUse`
hook that rewrites verification commands (e.g. `rspec spec/foo` →
`rtk rspec spec/foo`) and emits structured JSON.

Collector triggers (`^rspec\b`, `^bundle exec rspec\b`, …) do NOT
match `rtk *`:

- Hook exits silently when rtk has rewritten the command — no
  double-measurement.
- Universal rtk users see the collector as a no-op. Intended: rtk's
  JSON output is compact; running stack/gem collapsers over it
  would corrupt it.

To collect on rtk-rewritten commands:

1. Extend `triggers.yml` `verify_commands.direct` with `^rtk (rspec|rubocop|standardrb|brakeman|reek)\b`.
2. Add a JSON-detection short-circuit to `lib/verify_compression.rb` so JSON payloads pass through unchanged.

## Safety

- `rules.yml` preservation list is authoritative — never drop listed
  patterns.
- Plugin does NOT auto-delete telemetry. User opted in; user owns
  cleanup. SessionStart advisory surfaces paths only.
- Concurrent hook invocations append under exclusive `flock`; JSONL
  line integrity preserved when Claude pipelines tool calls.
- Fail-open: if `ruby` is unavailable, CLI binaries are missing /
  not executable, or the rules file is unreadable, the hook exits
  silently and raw Bash output is preserved unchanged. Compression
  is best-effort, never gating.

## Runtime

Plugin runtime is Ruby (≥ 3.4). Stdlib `yaml` only. No Python on
end-user machines.
