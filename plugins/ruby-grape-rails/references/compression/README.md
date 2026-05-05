# Verification-Output Compression — Telemetry

End-user collector for verify-command stdout. Records real
compression ratios + raw verify output for contributor analysis. Does
NOT replace the Bash stdout the model receives.

Opt-in. Default OFF. Set `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1` to
collect; otherwise hooks exit silently.

Data flow:

| Stage | Actor | Action |
|---|---|---|
| Collect | end-user | `PostToolUse` / `PostToolUseFailure` hooks on `Bash` append JSONL stats + raw logs to `${CLAUDE_PLUGIN_DATA}` |
| Read | end-user | `bin/compression-stats` aggregates JSONL on demand |
| Share | end-user | `/rb:compression-report` skill drafts an anonymized Markdown report from `compression-stats --redact` |
| Analyze | contributor | Eval-gate fixture suite verifies the compressor against tracked inputs |

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

`SessionStart` advisory hook nudges the user once accumulated
telemetry crosses either threshold from `rules.yml`
(`advisory.size_threshold_bytes`, `advisory.sample_threshold`).
Hook is read-only. Surfaces on-disk paths only — no literal `rm`
strings (a re-read of the SessionStart context could otherwise
misinterpret them as self-delete instructions). User composes
cleanup commands from the surfaced paths.

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

## End-User → Contributor Handoff

`/rb:compression-report` skill drafts an anonymized Markdown report
from `compression-stats --redact` plus selective raw-log Reads. User
reviews the markdown, files it as a GitHub issue. The redacted JSON
is intermediate input — NOT a paste-anywhere artifact.

## Contributor Consumption

Contributor eval suite consumes the same `lib/verify_compression.rb`
behavior the end-user collector exercises. CI gate runs against
tracked fixtures, asserts:

- ≥ 40% mean bytes reduction (bytes, not tokens — upper-bound
  potential per the "no Bash replacement path" note below)
- 0 preservation violations
- ≤ 15% diff against expected output

Promotion to a real Bash-replacement mechanism requires
`bin/compression-stats` reporting against ≥ 100 real samples per
command class:

- 0 preservation violations
- strong p50 (not just mean) ratio
- no command family consistently underperforming
- manual review of the worst 10 samples confirms rule integrity

## Megastring Middle-Collapse

Line-oriented collapsers (stack frames, deprecation runs, repeated
warnings, K-line block dedup) do NOT reduce a single logical line
encoding a large payload (canonical case: inline rspec expectation
diff `expected: { ... } got: { ... }` with the whole JSON dump on
one line). Megastring pass rewrites every line whose byte length
exceeds `megastring.threshold_bytes`:

- keep `keep_head` bytes from the start
- emit the rendered `collapse.megastring` template
- keep `keep_tail` bytes from the end
- elide the middle bytes

Tunables in `rules.yml`:

| Key | Default | Effect |
|---|---|---|
| `megastring.threshold_bytes` | 2048 | Lines at or below this length pass through. Raise for build banners / schema dumps; lower to chase smaller blobs. |
| `megastring.keep_head` | 500 | Preserves leading identifier (`expected:`, test description, file path). |
| `megastring.keep_tail` | 500 | Preserves terminating syntax (`}`, `)`, `got:`). |

Pass disables itself when `keep_head + keep_tail >= threshold_bytes`.
Boundaries are byte-aligned; multibyte UTF-8 split points scrubbed
via `String#scrub('')` so downstream regex passes never see invalid
byte sequences. Reported elided-byte count reflects actual surviving
sizes after scrub.

## No Bash Replacement Path

`PostToolUse` cannot replace Bash stdout. CC delivers tool output to
the model directly; only `updatedMCPToolOutput` replaces output
(MCP-only, not Bash). PostToolUse stdout goes to the debug log; only
`UserPromptSubmit`, `UserPromptExpansion`, `SessionStart` stdout
becomes context.

A real replacement (PreToolUse rewrite, additionalContext layer-add,
or pre-compaction) is deferred until telemetry quantifies which
workloads benefit. The contributor reader is the operator surface
for that decision.

Reference points:

- TACO (Ren et al., arxiv:2604.19572) — ~10% token-overhead reduction
- ACON (Kang et al., arxiv:2510.00615) — 26-54% peak-token reduction
  on long-horizon agent tasks

These are bytes-into-the-model metrics. This collector measures the
upper bound on Ruby-stack verify commands so a future release can
prove workload-relevance before redesign.

## Interaction with `rtk`

[rtk](https://github.com/rtk-ai/rtk) installs a global `PreToolUse`
hook that rewrites verification commands (e.g. `rspec spec/foo` →
`rtk rspec spec/foo`) and emits structured JSON.

Collector triggers (`^rspec\b`, `^bundle exec rspec\b`, …) do NOT
match `rtk *`:

- No double-measurement. Hook exits silently when rtk has rewritten
  the command.
- If rtk rewrites every verify invocation, the collector is a no-op
  for that user. Intended — rtk's JSON output is already compact;
  running stack/gem collapsers over it would corrupt it.

To collect on rtk-rewritten commands, extend `triggers.yml`
`verify_commands.direct` with
`^rtk (rspec|rubocop|standardrb|brakeman|reek)\b` AND add a
JSON-detection short-circuit to `lib/verify_compression.rb` so JSON
payloads pass through unchanged.

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
