---
name: intent-detection
description: "Routing any Ruby/Rails/Grape/Sidekiq/AR/Sequel/Hotwire/Karafka work to the correct /rb: command BEFORE doing it. Pushy gateway: consult at session start, suggest the right command, never blocks. Triggers: \"this Ruby project\", \"my Rails app\", \"how should I approach\", \"which command\", informal multi-step task descriptions. Do NOT use when user typed /rb:<name>."
user-invocable: false
effort: low
---
# Intent Detection — Workflow Routing

When user describes work WITHOUT specifying a `/rb:` command, analyze their intent and suggest the appropriate workflow BEFORE starting work.

## Routing Table — Visible Skills

| Signal phrase | Detected intent | Workflow target |
|---|---|---|
| "bug", "error", "crash", "failing", "broken", stack trace | Bug investigation | `/rb:investigate` |
| "add", "implement", "build", "create" + multi-step | New feature | `/rb:plan` |
| "review", "check" code | Code review (changed files) | `/rb:review` |
| "audit code", "audit project", "codebase health" | Project audit (whole codebase) | `/rb:audit` |
| "fix" + small/specific scope | Quick fix | handle directly or `/rb:quick` |
| "refactor", "clean up", "improve" | Refactoring | `/rb:plan` (needs scope) |
| "research", "how to", "what's the best" | Research | `/rb:research` |
| "evaluate", "compare", "adopt", "library", "should we use" | Library evaluation | `/rb:research --library` |
| "test", "spec", "coverage" | Testing | handle directly or `/rb:plan` |
| Describes 1-2 file changes, < 50 lines | Small task | handle directly |
| "deploy", "release", "production" | Deployment | `/rb:verify` then deploy |
| "performance", "slow", "N+1", "memory" | Performance | `/rb:perf` |
| "PR review", "review comments", "address feedback", "respond to PR" | PR response | `/rb:pr-review` |
| "permission prompts", "stop asking", "settings.json", "allow commands", "permission fatigue" | Permission tuning | `/rb:permissions` |
| "that worked", "fixed it", "problem solved" | Knowledge capture | `/rb:compound` |
| "enhance plan", "more detail", "deepen" | Plan enhancement | `/rb:plan --existing` |
| "triage", "which findings", "prioritize fixes" | Finding triage | `/rb:triage` |
| "brainstorm", "explore options", "not sure how", "multiple approaches", "what's the best way to architect" | Design exploration | `/rb:brainstorm` |

## Routing Table (DMI roster — slash-only)

Skills below carry `disable-model-invocation: true`. They never auto-load
through the routing prompt; reach them via `/rb:<name>` slash invocation
when the signal matches. Suggest the right command when triggers appear.

<!-- BEGIN-GENERATED routing-table -->
| Signal | Detected Intent | Suggest |
|---|---|---|
| "interview", "brainstorm", "discovery", "explore ideas" | workflow on-ramp; pre-plan discovery | `/rb:brainstorm` |
| "adversarial review", "devil's advocate", "stress test" | adversarial-mode review | `/rb:challenge` |
| "YARD", "RDoc", "ADR", "write docs" | post-implementation docs | `/rb:document` |
| "show examples", "codebase patterns", "representative code" | codebase pattern surface | `/rb:examples` |
| "tutorial", "getting started", "what can you do" | onboarding | `/rb:intro` |
| "iron law", "non-negotiable rule", "Ruby safety rules" | SessionStart-injected; review BLOCKED path | `/iron-laws` |
| "learn from this", "remember this mistake", "correction" | in-flight lesson capture | `/rb:learn` |
| "slow", "latency", "memory", "p95", "queue backup" | performance analysis | `/rb:perf` |
| "permissions", "allow command", "approval prompts", "settings.json" | permission tuning | `/rb:permissions` |
| "PR feedback", "review comments", "reviewer said" | PR review-comment handling | `/rb:pr-review` |
| "quick fix", "typo", "one-liner" | trivial-fix path | `/rb:quick` |
| "research gem", "compare approaches", "upgrade path" | evidence-based research | `/rb:research` |
| "rubydoc", "gem docs", "API reference", "Rails Guides" | cheap doc lookup | `/rubydoc-fetcher` |
| "secrets", "leaked", "API key", "credentials", "betterleaks" | pre-push secret scan | `/rb:secrets` |
| "do everything", "full lifecycle", "end to end", "hands-off" | full lifecycle orchestration | `/rb:full` |
| "audit project", "codebase health", "architecture review" | project-wide audit | `/rb:audit` |
| "compression report", "share compression stats" | internal QA (telemetry report) | `/rb:compression-report` |
| "scan provenance", "audit research quality", "trust state" | research-trust audit | `/rb:provenance-scan` |
| "service boundaries", "split monolith", "fat controller", "package boundary" | service-boundary analysis | `/rb:boundaries` |
| "request state", "CurrentAttributes", "session leak", "Redis state" | request-state hygiene | `/rb:state-audit` |
| "Tidewave", "live runtime", "introspect models", "running app" | Tidewave runtime introspection | `/rb:runtime` |
| "tech debt", "cleanup", "callback sprawl", "stale code", "overgrown service", "decorative abstraction" | tech-debt logging | `/rb:techdebt` |
| "Karafka", "Kafka consumer", "event streaming" | Kafka consumer patterns | `/rb:karafka` |
| "Hotwire Native", "Turbo Native", "iOS bridge", "Android Hotwire" | native mobile Hotwire | `/rb:hotwire-native` |
| "async gem", "fiber concurrency", "Falcon server", "I/O-bound" | fiber concurrency | `/rb:async-patterns` |
| "dry-rb", "dry-validation", "dry-types", "dry-monads" | dry-rb gem patterns | `/rb:dry-rb-patterns` |
| "Sequel", "Sequel ORM", "Sequel dataset", "Sequel migration" | Sequel ORM patterns | `/rb:sequel-patterns` |
| "Kamal deploy", "Docker deploy", "Thruster", "release Rails" | deployment configuration | `/rb:deploy` |
| "discovery report", "trigger-table tuning", "injection telemetry" | internal eval-tuning tool — drafts a redacted report from skill-discovery telemetry | `/rb:discovery-report` |
<!-- END-GENERATED routing-table -->

## Behavior

1. Read user's first message
2. Match against routing table (use keyword + context signals, not exact match)
3. If **lock** (single valid route): suggest the command directly — "This looks like [intent]. I'd suggest `[command]` — want me to run it, or should I just dive in?"
4. If **fork** (multiple valid routes): present top 2-3 options with one-sentence rationale each
5. If trivial task (typo, single-line fix, config change): skip suggestion, just do it
6. If user already specified a `/rb:` command: follow it, don't re-suggest
7. **NEVER block the user** — suggestion only, not mandatory

## Routing Modes

### Lock (single valid route — act immediately)

High confidence, one right answer. Don't deliberate — suggest directly:

- Stack trace or error message pasted → `/rb:investigate`
- "Fix CI" / "fix rubocop" → auto-fix pattern
- "Run checks" → `/rb:verify`
- "Permission prompts annoying" → `/rb:permissions`
- "That fixed it" → `/rb:compound`
- "Add [feature] with [multiple components]" → `/rb:plan`
- "Review my changes" or "check this PR" → `/rb:review`

### Fork (multiple valid routes — don't pick silently)

Genuinely ambiguous. Present top 2-3 options with one-sentence rationale each:

- "Work on billing feature" → `/rb:plan` or `/rb:work` depending on whether plan exists
- "Improve the auth flow" → `/rb:plan` (scope unclear) or `/rb:investigate` (if bugs mentioned)
- "Clean up this module" → `/rb:quick` (small) or `/rb:plan` (large) — ask about scope
- "Fix [thing]" — could be quick or complex, suggest based on scope description
- "Update [thing]" — could be small edit or refactor

### Trivial (just do it)

Low confidence or obvious scope. Don't suggest a workflow:

- Single file mentioned, clear change
- "Change X to Y"
- Configuration or dependency updates

## Complexity Signals

When a task matches a workflow command, check complexity before suggesting:

**Trivial signals** (suggest `/rb:quick` or handle directly):

- Single file mentioned explicitly
- "exclude X from Y", "add X to config", "rename", "change X to Y"
- Problem + solution both stated ("X is wrong, change to Y")
- One-line fix described

**Complex signals** (suggest `/rb:plan` or `/rb:investigate`):

- 3+ modules or files mentioned
- "intermittent", "race condition", "sometimes", "random"
- Stack trace with 5+ frames
- "across", "all", "every" (scope indicators)

**Override rule**: If user invokes `/rb:full` but task matches trivial signals:
"This looks like a quick fix. Want `/rb:quick` instead, or stick with the full cycle?"

## Iron Laws

1. **NEVER block on suggestion** — If user starts explaining, just do the work
2. **One suggestion max** — Don't re-suggest if user ignores first suggestion
3. **Commands are shortcuts, not gates** — All work can be done without commands

## Integration

This skill is consulted at session start. It works alongside:

- SessionStart hook (shows plugin loaded message + injects Iron Laws + Preferences)
- Individual workflow skills (activated by commands)
