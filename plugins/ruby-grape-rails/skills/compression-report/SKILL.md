---
name: rb:compression-report
description: "Use when sharing verify-output compression telemetry with the plugin maintainers as an anonymized GitHub-issue-ready report. Drafts a redacted, actionable PII-safe report for the user to copy into a GitHub issue."
when_to_use: "Triggers: \"share my compression stats\", \"send compression report\", \"compression telemetry report\", \"file compression issue\", \"contribute compression data\". Does NOT handle: per-run compression diagnosis (use Bash tool against compression-stats directly), changing rules.yml (edit the file)."
argument-hint: "[--log PATH]"
effort: medium
user-invocable: true
---

# Compression Telemetry Report

Drafts an anonymized markdown report from the verify-output compression
telemetry the plugin collects under
`${CLAUDE_PLUGIN_DATA}/compression.jsonl` and hands it back for the
user to file as a GitHub issue. The report is contributor-grade signal
that helps decide whether a future release should ship a real
replacement mechanism.

## Iron Laws

1. **Never include redacted output verbatim from `--redact` without
   reviewing it first.** The redactor handles common PII shapes
   (env-var values, file paths, freeform args) but is not an
   adversarial sanitizer. Read each cited raw_log file before
   quoting from it.
2. **Never run `compression-stats` without `--redact` for issue
   bodies.** The non-redact JSON contains absolute home-dir paths
   inside `raw_log` fields and full `cmd` strings. That is contributor
   debug output, not public-issue data.
3. **Never auto-create the GitHub issue.** Hand the drafted report to
   the user and let them open the issue manually. Telemetry is the
   user's data; only the user can choose to publish it.
4. **Never read more raw logs than needed to explain the worst few
   samples.** The report is a digest, not a dump. Keep raw-log Reads
   scoped to the redacted_stats `weak_samples` and `violation_samples`
   lists, capped at the most interesting ~5.
5. **Never delete the user's telemetry yourself.** The skill ships no
   destructive command. After drafting the report, list the exact
   cleanup paths the user can remove when they choose to clean up.
   The user composes and runs the deletion command themselves; the
   skill never does. Do not embed literal `rm` / `rm -rf` strings in
   the drafted output — that mirrors the SessionStart advisory's
   safer-context posture.
6. **Never quote reconstructed absolute paths in the drafted report
   body.** `${CLAUDE_PLUGIN_DATA}` substitutes inline to a path that
   contains the user's home directory and plugin install id. Use the
   resolved path locally for `Read` and for the cleanup-paths block
   at the very end of the workflow. Do NOT paste it into the
   per-sample explanations, citations, or any other prose the user
   will paste into a shared report.

## Workflow

1. Run the redacted aggregator:

    ```text
    compression-stats --redact
    ```

   (Optional `--log <path>` argument is forwarded if the user supplied
   one.) Treat the resulting JSON as the canonical input. Stop
   immediately if the CLI exits non-zero with "no jsonl at ..." OR if
   `samples == 0`. Both conditions mean no telemetry exists to report
   — most commonly because the user has not opted in. Tell the user
   to set `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1` in their shell
   environment, run a few representative verify commands (rspec,
   rubocop, brakeman, rails db:migrate), and re-invoke this skill
   once the jsonl has accumulated samples.

2. Inspect the JSON structure:

   - `samples` — total measurements
   - `preservation_violations` — count across all samples
   - `by_class` — per-command-class `count`, `mean`, `p50`, `p95`
   - `weak_samples` — up to 10 samples with `ratio < 20%`, redacted
     `cmd`, plus a `raw_log_id` pointer
   - `violation_samples` — up to 10 samples whose preservation check
     flagged something, with redacted `cmd`, `raw_log_id`,
     `violation_count`
   - `recommendation` — verdict against the documented promotion
     criteria

   The redacted JSON deliberately omits absolute paths. The raw
   captures live next to the jsonl on the user's local machine; you
   reconstruct the path yourself per Step 3 below.

3. **Decide which raw logs are worth quoting.** Read the raw log file
   only for samples that genuinely need explaining (worst weak
   ratios; preservation-violation samples). Reconstruct the absolute
   path locally as
   `${CLAUDE_PLUGIN_DATA}/verify-raw/<raw_log_id>.log`. Claude Code
   substitutes `${CLAUDE_PLUGIN_DATA}` inline in this skill's
   content before you see it (per the Anthropic plugins-reference
   docs), so the variable resolves to the user's actual data dir at
   load time — do NOT shell to `echo "$CLAUDE_PLUGIN_DATA"`, the env
   var is not inherited by Bash subprocesses you spawn from a skill.
   Use the `Read` tool with a modest line budget; if the file is
   large (verify outputs often are), read the first 100 lines plus
   tail 50 to characterize what compressed well or poorly.

4. **Draft the markdown report.** Suggested sections:

   - **Headline summary.** Sample count, recommendation verdict,
     overall mean/p50/p95 if available.
   - **Per-class breakdown table.** One row per command class with
     count, mean, p50, p95.
   - **Why compression worked (or did not).** 2-4 short observations
     grounded in the raw logs you read. Example: "rspec p50 = 0.71
     because failure stacks routinely exceed 5 frames; rake p50 =
     0.05 because routes output is already compact." Cite raw_log_id
     references like `raw_log_id=abc-123` so a contributor can
     correlate against their own data if they reproduce.
   - **Preservation issues.** If `preservation_violations > 0`,
     describe the pattern (e.g. "violations centered on
     `file_colon_line` regex matching gem-internal stack frames").
   - **Suggested rule tweaks.** Optional. Only if the raw logs
     suggest a concrete fix to `rules.yml`.

5. **Show the draft to the user.** Print the full report inside a
   fenced code block so it is easy to copy. Append a short footer
   with the GitHub issue URL: read `repository` from
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` and append
   `/issues/new` (e.g. `https://github.com/<owner>/<repo>/issues/new`).
   Forks automatically point at the fork's repo via the same
   manifest field. Do not run `gh issue create`.

6. **Hand cleanup back to the user.** After the draft, list the
   exact paths the user can remove once they have filed the report.
   Use `${CLAUDE_PLUGIN_DATA}` directly — Claude Code has already
   substituted the variable inline by the time you read this skill,
   so the resolved path appears in your context. Path shape:
   `${CLAUDE_PLUGIN_DATA}/compression.jsonl` for the aggregate jsonl
   and `${CLAUDE_PLUGIN_DATA}/verify-raw` for the raw-log directory.
   This is the ONE place in the workflow where the absolute path is
   allowed to appear (the deletion happens locally on the user's
   machine; the absolute path never leaves it). Do not run any
   destructive command yourself, and do not embed literal `rm` /
   `rm -rf` strings in the drafted output — surface only the paths,
   per Iron Law 5. Suggested wording:

   ```text
   When you (the user) decide to clean up, the relevant paths are:
     jsonl:     ${CLAUDE_PLUGIN_DATA}/compression.jsonl
     raw logs:  ${CLAUDE_PLUGIN_DATA}/verify-raw  (directory)
   ```

## Privacy posture

- The redactor strips: `KEY=value` env-var values; `spec/...` and
  `test/...` file paths; absolute paths; trailing freeform `--` args;
  full `raw_log` paths (replaced with the basename `raw_log_id`).
- Raw-log files themselves are NOT auto-included in the report. If
  the user wants to attach a raw log, they decide.
- Violation message strings (which can quote raw output) are dropped;
  only the count is reported.

If you observe what looks like a real secret leaking through
redaction, stop, name the pattern, and ask the user to extend the
redactor before continuing. Do not paste the suspicious line into the
draft.

## Example draft (shape only — do not copy literally)

```markdown
## Verify-output compression report

**Recommendation:** keep-collecting (unmet:
underpowered-classes=rubocop,brakeman; weak-p50=rake)

**Aggregate**

| class       | count | mean   | p50    | p95    |
|-------------|------:|-------:|-------:|-------:|
| rspec       | 142   | 71.2%  | 69.4%  | 83.1%  |
| rubocop     | 18    | 22.0%  | 19.5%  | 35.0%  |
| migration   | 31    | 64.0%  | 62.5%  | 78.0%  |
| rake        | 9     | 6.0%   | 5.0%   | 9.0%   |

**Why compression worked**

- rspec failures routinely include 30-50 frame backtraces
  (`raw_log_id=...`); the >5-frame collapse drives p50 ≈ 70%.
- migration output has long Loaded-gem preambles before the actual
  schema diff (`raw_log_id=...`); collapsing those preambles drives
  p50 ≈ 63%.

**Why compression did not work**

- `rake routes` output is already a compact table
  (`raw_log_id=...`); no stack frames or gem preambles to collapse.
  Triggering on `rake routes` should likely be moved to
  `rake_excluded`.

**Preservation**

- 0 violations across 200 samples.

**Suggested rule tweaks**

- Move `rake routes` to `rake_excluded`. (See `raw_log_id=...`.)
```
