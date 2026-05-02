# Agent Selection Guidelines

## When to Spawn Which Agents

Agent identifiers below are subagent_type names (frontmatter `name`
field). For the operational selection matrix used by `/rb:plan`
fanout, see `planning-workflow.md` § "Agent Selection Matrix" +
"Spawning Strategy" — that is canonical for the prepare-run
`--agents=` mapping. This table is the higher-level guideline.

| Feature Type | Agents to Spawn |
|--------------|-----------------|
| CRUD feature | rails-patterns-analyst, active-record-schema-designer |
| Interactive UI | rails-patterns-analyst, rails-architect |
| External integration | rails-patterns-analyst, ruby-runtime-advisor (+ ruby-gem-researcher ONLY if new lib) |
| Background processing | rails-patterns-analyst, sidekiq-specialist |
| Data-heavy | rails-patterns-analyst, active-record-schema-designer (+ ruby-gem-researcher ONLY if new lib) |
| Real-time | rails-patterns-analyst, rails-architect |
| Auth/permissions | rails-patterns-analyst, security-analyzer |
| Refactoring | rails-patterns-analyst, call-tracer |
| Review fix (simple) | rails-patterns-analyst only |
| Review fix (complex) | rails-patterns-analyst + relevant specialists |
| Full new feature | ALL relevant agents |

## When to Spawn ruby-gem-researcher

**Spawn ONLY when:**

- Feature requires a NEW gem not yet in Gemfile
- Evaluating ALTERNATIVE gems to replace an existing dep

**Do NOT spawn when:**

- Gem is already in Gemfile (use Read/Grep on gem source instead)
- Fixing review blockers (gems already chosen)
- Refactoring existing code
- Understanding API of an existing dependency
- Simple bug fixes or improvements

**To understand an existing gem's API:**

- Use `Read` on gem source code
- Use `Grep` to find method signatures and docs
- Use web search for documentation
- Do NOT spawn ruby-gem-researcher for this

## When to Spawn web-researcher

**Model**: haiku (cheap fetch worker — extraction, not reasoning)

**Spawn when:**

- Feature involves unfamiliar library/pattern
- Need community input (Ruby discussions)
- Looking for real-world examples
- Checking for known issues/gotchas
- CI/CD or infrastructure questions

**Do NOT spawn when:**

- Standard CRUD feature
- Well-known patterns (auth, pagination)
- Codebase already has similar implementation

**Spawn rules:**

- Pass a focused 5-15 word query OR pre-searched URLs, NEVER raw text
- If multiple web topics: spawn multiple agents in parallel (1 per topic)
- Max 5 URLs per agent (diminishing returns beyond that)
- Agent returns 500-800 word summary — synthesis happens in main session from per-agent research artifacts

## When to Spawn call-tracer

Spawn when planning involves:

- **Changing method signatures** — Need all callers and argument patterns
- **Moving/renaming methods** — Need all call paths
- **Refactoring service objects** — Need data flow understanding

## When to Ask Clarifying Questions

**Ask if:**

- Multiple valid approaches exist
- Scope is ambiguous
- Performance requirements unclear
- Integration points undefined

**Don't ask if:**

- Best practice is clear
- Codebase shows clear patterns
- Feature is well-specified

Max 3 questions. Make them count.
