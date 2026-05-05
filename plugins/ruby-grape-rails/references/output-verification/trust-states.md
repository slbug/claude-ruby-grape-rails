# Trust States

Compute `trust_state` from the provenance sidecar
(`*.provenance.md`) YAML frontmatter at read time. Do NOT author or
persist `trust_state` directly. Required frontmatter fields:
`claims`, `sources`, `conflicts`.

## States

| State | Conditions |
|---|---|
| `clean` | Every `claims[].id` appears in ≥ 2 distinct `sources[].supports`; `conflicts: []`. |
| `weak` | ≥ 1 claim supported by only 1 source, OR every source has `kind: tool-output` (no primary). `conflicts: []`. |
| `conflicted` | `conflicts[]` non-empty. |
| `missing` | No `.provenance.md` companion, OR sidecar lacks `---`-delimited frontmatter, has unterminated frontmatter, malformed YAML, non-mapping frontmatter, or empty `claims` / `sources`. |

## Workflow Behavior on State

| State | `/rb:plan --existing` | `/rb:work` | `/rb:review` | `/rb:triage` |
|---|---|---|---|---|
| `clean` | proceed silently | log to `progress.md` | proceed | rank normally |
| `weak` | warn; suggest `/rb:research` | warn; log | add provenance note; keep severity | flag as hint |
| `conflicted` | HALT | HALT | escalate finding severity by one level | surface prominently |
| `missing` | warn; suggest `/rb:research` | warn; log | tag finding `[unverified]`; do not gate merge | flag as hint |

End-user `/rb:provenance-scan` audits sidecar distribution across
`.claude/{research,reviews,audit,plans/*/{research,reviews}}` and
writes a dated report under `.claude/provenance-scan/`.

Compound + strategy cards inherit the source artifact's trust state.

## Telemetry handoff (end-user → contributor)

Trust-state is also a contributor-eval signal. The deterministic CI
gate counts the distribution across tracked fixtures. End-users do
NOT run the eval gate — that surface is contributor-only.

## References

- *Adaptation of Agentic AI: A Survey of Post-Training, Memory, and
  Skills* — <https://arxiv.org/abs/2512.16301v3>. Provenance sidecars
  function as the plugin's external adaptive memory (T2 in the
  survey's taxonomy). The trust-state split is this plugin's
  evidence-gate gap-fill, not a paper claim.
