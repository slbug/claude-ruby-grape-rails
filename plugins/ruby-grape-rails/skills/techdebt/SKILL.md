---
name: rb:techdebt
description: "Scanning a Ruby/Rails/Grape codebase for tech-debt items: overgrown services, query repetition, callback sprawl, decorative abstractions, dead code, missing tests around legacy seams. Read-only — logs items, routes fixes elsewhere."
effort: medium
disable-model-invocation: true
---
# Technical Debt

Read-only scan that logs tech-debt items and routes fixes to other commands.
Never applies fixes itself.

## Iron Laws

1. Read-only scan; never auto-apply fixes.
2. Multi-fix findings route to `/rb:plan`; one-line fixes route to `/rb:quick`.
3. Architectural debt routes to `/rb:boundaries`; whole-codebase context routes to `/rb:audit`.
4. Each finding records evidence (path:line, count, ripgrep snippet) — never opinion alone.

## Debt Categories

| Category | Detection signal | Severity |
|---|---|---|
| Callback sprawl | `after_*` count per model > 5; cross-model callbacks | Warning |
| Query repetition | Same `where(...).order(...)` pattern in 3+ places | Warning |
| Oversized service objects | Service > 200 lines OR 5+ public methods | Critical |
| Decorative abstractions | Wrapper classes adding zero behavior | Info |
| Missing tests around legacy seams | Public method with 0 spec coverage in `lib/legacy/` or untouched modules | Critical |
| Dead code | Constants/methods with 0 references in repo (exclude fixtures) | Info |
| Controller bloat | Controller > 150 lines OR 7+ actions | Warning |
| Model bloat | Model > 300 lines OR 10+ scopes/associations | Warning |
| N+1 patterns at scale | `.each { ... .association }` in serializers | Critical |
| Stale gem dependencies | Gemfile entries pinned 2+ years stale | Warning |
| Duplicate config sources | Same setting in `application.rb` + `initializers/*.rb` + `.env` | Info |
| Unused gems | Gemfile entry with 0 require references | Info |

Detection commands per category live in `references/`:

- `references/callback-sprawl.md`
- `references/service-bloat.md`
- `references/dead-code-scan.md`

## Scan Procedure

1. **Identify scope.** Whole repo / single package / single subsystem path. Default = current package boundary inferred from `Gemfile`, `packwerk.yml`, or `app/packages/`.
2. **Per-category scan.** Walk the Debt Categories table; for each row, run the detection signal:
   - `wc -l`, `find -name '*.rb'`, `rg --count` for size/count thresholds.
   - `rg --no-heading` for pattern presence.
   - `bundle outdated`, `bundle list --paths` for gem staleness.
   Skip categories already known stable for the package.
3. **Score each finding.** Assign severity tier (Critical / Warning / Info) per the table. Estimate fix-effort: small (<30 min), medium (1-4 h), large (>4 h).
4. **Record evidence per finding.** Every entry MUST carry path:line, raw command output snippet, or count. Never opinion alone.
5. **Write artifact.** Append one YAML block per finding to `.claude/audit/techdebt/{datesuffix}.md` using the output template below.
6. **Route findings.** Multi-fix → `/rb:plan`; one-liner → `/rb:quick`; architectural / boundary → `/rb:boundaries`; if scope crosses packages → `/rb:audit`.
7. **Stop.** Never apply fixes inline. Hand off to the chosen routing command.

## Output Artifact Path

```
.claude/audit/techdebt/{YYYYMMDD-HHMMSS}.md
```

`.claude/audit/` is gitignored by convention; debt artifacts are local
to the contributor's workspace and shared explicitly via PR description
or paste when needed.

## Output Template

```yaml
- category: <category-name>
  location: <path:line OR directory>
  severity: critical | warning | info
  fix_effort: small | medium | large
  evidence: |
    <ripgrep output, file excerpt, OR count>
  suggested_action: <next /rb: command + 1-line plan>
```

Append one block per finding. One file per scan run.

## Routing

| Finding scope | Route to |
|---|---|
| Multi-file fix | `/rb:plan` |
| One-line fix | `/rb:quick` |
| Architectural / boundary | `/rb:boundaries` |
| Whole-codebase context | `/rb:audit` |

## Integration Hooks

| Hub | Where techdebt surfaces |
|---|---|
| `audit` | Findings flow into a techdebt artifact when audit categorises an item as debt rather than blocking quality issue |
| `review` | Pre-existing items the reviewer flags as WARNING (not blocker) route here for logging without blocking the review |
| `rb-boundaries` | Boundary analysis emits architectural-debt entries; techdebt logs them with `/rb:boundaries` as suggested action |
| `investigate` | Edge cases noticed during root-cause work that are outside the immediate fix scope log here |
| `quick` | Adjacent debt seen during a one-line fix routes here so the quick fix stays narrow |
| `work` | Plan-execution completion can offload follow-up debt items here |

## Anti-patterns

- Writing fixes inline. Always log + route.
- Subjective complaint without evidence. Each finding ties to a path:line or count.
- Mixing severity tiers. Critical entries belong with Critical; do not soften.
- Skipping the routing step. A finding without a route is unactionable.

## References

- `references/callback-sprawl.md` — callback count + cross-model detection commands
- `references/service-bloat.md` — service-object + controller + model bloat thresholds
- `references/dead-code-scan.md` — zero-reference method / gem / config detection

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Service-boundary or split-monolith decision → `/rb:boundaries` (service-boundary analysis)
<!-- END-GENERATED related-footer -->
