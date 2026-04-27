# Trust States

Every provenance sidecar has a `trust_state` computed at read time from its
`claims`, `sources`, and `conflicts` fields. Workflows call
`lab.eval.output_checks.compute_trust_state(path)` and adjust behavior based
on the result.

## States

| State | Meaning | Evidence |
|-------|---------|----------|
| `clean` | All claims have ≥2 independent sources; no contradictions | every `claims[].id` appears in at least two `sources[].supports` lists; `conflicts: []` |
| `weak` | Some claims single-sourced OR only tool-derived (no primary) | ≥1 claim with only 1 source, OR all sources have `kind: tool-output` |
| `conflicted` | ≥2 sources disagree on the same claim | Non-empty `conflicts[]` list |
| `missing` | No usable provenance schema | Target file has no `.provenance.md` companion, OR the sidecar lacks a `---`-delimited frontmatter block, has unterminated frontmatter, malformed YAML, non-mapping frontmatter, or empty `claims`/`sources` |

## Workflow consumption

Computed via `lab.eval.output_checks.compute_trust_state(path)` — never
authored by hand, never persisted.

Live consumers:

- Eval reporter — `make eval-output` prints the distribution.
- `/rb:plan --existing` — warns + suggests `/rb:research` on `weak` /
  `missing`; halts on `conflicted`. See plan SKILL "Trust States".
- `/rb:triage` — surfaces `conflicted` prominently; flags `missing` as
  hints. See triage SKILL "Trust States".
- `/rb:work` — logs consumed state to `progress.md`; warns on `weak` and
  `missing`; halts on `conflicted`. See work SKILL "Trust States".
- `/rb:review` — cross-checks sidecar trust against findings; escalates
  severity on `conflicted`. See review SKILL "Trust States".
- End-user `/rb:provenance-scan` — audits sidecar distribution and writes
  a dated report under `.claude/provenance-scan/`.

Compound + strategy cards inherit their source's trust state.

## Computation

Trust state is **runtime-derived**, not stored. Callers invoke
`lab.eval.output_checks.compute_trust_state(path)` and act on the result.
The provenance frontmatter declares only `claims`, `sources`, and
`conflicts`; the state is read from those fields each time it is needed.

## References

- Paper context: *Adaptation of Agentic AI: A Survey of Post-Training,
  Memory, and Skills* — <https://arxiv.org/abs/2512.16301v3>. Provenance
  sidecars are the plugin's "external adaptive memory" (T2 in the survey's
  taxonomy: agent-supervised tool/memory adaptation). The survey notes
  that mechanisms for grading memory reliability are an open gap —
  trust-state splitting is this plugin's gap-fill, not a paper claim.
- Anti-pattern: trusting derived memory without evidence gate. Source-tier
  weighting and the `clean`/`weak`/`conflicted` split exist to make
  evidence quality visible at every read.
