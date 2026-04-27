---
name: rb:research
description: "Use when the team needs evidence-based research on Ruby/Rails/Grape/Sidekiq gems, upgrade paths, security-sensitive choices, or architectural trade-offs before implementation or adopting a pattern."
when_to_use: "Triggers: \"research this gem\", \"compare approaches\", \"what are the options\", \"upgrade path\", \"evidence for\". Does NOT handle: debugging, implementation, code review, brainstorming."
argument-hint: <topic>
disable-model-invocation: true
effort: high
---
# Research Ruby Approaches

Research with primary sources first, synthesize findings, and provide actionable recommendations.

## Iron Laws

1. Start with T1 primary sources before using community commentary.
2. Mark source tiers explicitly in every research artifact.
3. Do not make version-specific claims without a cited source.
4. Separate reusable cross-plan research from plan-local repo findings.
5. Use `output-verifier` before high-impact recommendations that depend on external evidence.

## Research Process

## Repository Topology Check

Before deep research in an existing codebase, identify:

- which package/app owns the code in question
- which ORM that package uses
- whether Packwerk or a similar modular-monolith structure is present

If the repo appears modular but explicit Packwerk signals are absent, ask:

`No Packwerk detected. Do you have something similar implemented? Where are the modules/packages and what stack/ORM does each use?`

```
START ──▶ DECOMPOSE_QUERY ──▶ SPAWN_RESEARCHERS ──▶ PARALLEL_RESEARCH
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │  WAIT FOR ALL   │
                                            └────────┬────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  SYNTHESIZE     │
                                            │  FINDINGS       │
                                            └────────┬────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  STRUCTURE      │
                                            │  OUTPUT         │
                                            └────────┬────────┘
                                                     │
                                                     ▼
                                                   OUTPUT
```

## Query Decomposition

Break complex research into sub-queries:

| Topic | Sub-queries |
|-------|-------------|
| Gem comparison | Usage, maintenance, performance, compatibility |
| Upgrade path | Breaking changes, migration guide, timeline |
| Pattern adoption | Best practices, anti-patterns, alternatives |
| Architecture | Pros/cons, examples, community adoption |
| Modular monolith | Package boundaries, public APIs, stack ownership |

Example:

```
Query: "Should we switch from Sidekiq to Solid Queue?"

Sub-queries:
1. Sidekiq vs Solid Queue performance comparison
2. Migration guide and breaking changes
3. Feature parity (retries, scheduled jobs, batches)
4. Community adoption and maintenance
5. Operational requirements (Redis vs PostgreSQL)
```

## Parallel Researcher Spawning

Spawn multiple `web-researcher` agents in parallel:

```
Spawn Order:
1. web-researcher (Gem A docs)      ──┐
2. web-researcher (Gem B docs)       ├──▶ Wait all ──▶ Synthesize
3. web-researcher (Comparison blog) ──┘
4. web-researcher (GitHub issues)
5. web-researcher (Performance benchmarks)
```

### Agent Briefing Template

```
Task: Research [specific aspect] of [topic]

Research questions:
1. [Question 1]
2. [Question 2]
3. [Question 3]

Sources to check:
- Official documentation
- GitHub repository
- Recent blog posts (within 1 year)
- Community discussions

Output: Structured findings with sources
```

## Primary Sources Priority

Research in this order:

1. **Official Documentation**
   - Rails Guides (guides.rubyonrails.org)
   - Ruby docs (ruby-doc.org)
   - Gem README and wiki
   - Grape documentation
   - Sidekiq wiki

2. **Source Code**
   - GitHub repository
   - CHANGELOG/NEWS
   - Release notes
   - Code examples

3. **Community Sources**
   - Ruby Weekly newsletter
   - Thoughtbot blog
   - GoRails tutorials
   - RubyKaigi talks

4. **Caution**
   - Stack Overflow (verify date)
   - Blog posts (check author credibility)
   - Reddit discussions

## Source Quality Rules

Classify sources as part of the final synthesis:

- `T1` authoritative primary sources
  - official docs, source code, changelogs, release notes
- `T2` first-party ecosystem sources
  - maintainer posts, maintainer comments, official conference talks
- `T3` credible community sources
  - high-quality blogs, issue threads, talks with working examples
- `T4` low-confidence sources
  - SEO listicles, uncited summaries, generic aggregators
- `T5` rejected sources
  - dead links, fabricated URLs, inaccessible sources without evidence

Rules:

- every cited source should carry `[T1]`, `[T2]`, etc.
- recommendations should say what quality mix they rely on
- conflicts should mention source tier when choosing which claim to trust
- T4/T5 material should never be the sole basis for a recommendation

## File-First Output Pattern

Write reusable cross-plan research to `.claude/research/{topic-slug}.md`:

```markdown
# Research: [Topic]

Last Updated: {YYYY-MM-DD}
**Requested by**: [context]
**Researcher**: [agent name]

## Executive Summary
[2-3 sentences with recommendation]

## Findings

### [Aspect 1]
**Question**: [what we researched]

**Sources**:
- [T1] Source 1 - <official-docs-url> - [relevance]
- [T1] Source 2 - <source-code-or-changelog-url> - [relevance]

**Key Points**:
- [Finding 1]
- [Finding 2]

### [Aspect 2]
...

## Comparison Matrix

| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Performance | ★★★☆☆ | ★★★★★ | ★★★★☆ |
| Maintenance | ★★★★★ | ★★★☆☆ | ★★★★☆ |
| Migration Cost | Low | High | Medium |
| Community | Large | Medium | Small |

## Decision Matrix

| Factor | Weight | Option A | Option B | Option C |
|--------|--------|----------|----------|----------|
| Performance | 30% | 3 | 5 | 4 |
| Maintenance | 25% | 5 | 3 | 4 |
| Compatibility | 25% | 5 | 2 | 4 |
| Learning Curve | 20% | 5 | 2 | 3 |
| **Weighted Score** | | **4.2** | **3.1** | **3.8** |

## Trade-offs

### Option A (Current approach)
**Pros**:
- [advantage]

**Cons**:
- [disadvantage]

### Option B (Recommended)
**Pros**:
- [advantage]

**Cons**:
- [disadvantage]

## Recommendation

**Recommended**: Option B

**Source quality**: Based on {n} T1, {n} T2, and {n} T3 sources.

**Rationale**:
1. [reason]
2. [reason]
3. [reason]

**Migration path**:
1. [step]
2. [step]
3. [step]

**Risks**:
- [risk] → [mitigation]

## Next Steps
- [ ] [action item]
- [ ] [action item]

## Sources
- [Full citation list]
```

## Provenance Check

For high-impact research, verify the draft before final recommendation.

Provenance is required when the research will drive:

- a gem adoption or rejection decision
- an upgrade plan
- a security-sensitive recommendation
- a version-specific implementation choice
- a recommendation supported partly by T3 sources

For informal "how do I do X?" research that does not drive a durable decision,
provenance is optional.

When you use it:

1. Write the draft research artifact first.
2. Spawn `output-verifier` against that artifact.
3. Save the verifier result alongside the research as:
   - `.claude/research/{topic-slug}.provenance.md` for reusable research
   - `.claude/plans/{slug}/research/{topic-slug}.provenance.md` for plan-local research
4. Apply the report:
   - remove unsupported claims
   - soften weakly sourced claims
   - call out unresolved conflicts explicitly

Use the shared provenance contract:

- `${CLAUDE_PLUGIN_ROOT}/references/output-verification/provenance-template.md`

## Reuse Rules

Use the research filesystem deliberately:

- `{topic-slug}` = stable kebab-case identifier for the research topic
  (example: `sidekiq-vs-solid-queue`)
- `{slug}` = plan slug for one `/rb:plan` namespace

- `.claude/research/{topic-slug}.md`
  - cross-plan research that may be reused by future `/rb:plan` runs
  - best for gem evaluations, upgrade paths, framework/tooling
    comparisons, and community research
- `.claude/plans/{slug}/research/*.md`
  - feature-specific research scoped to a single plan namespace
    (it remains associated with that plan even after the plan is no
    longer active)
  - best for current codebase findings, architecture decisions, and
    plan-local agent output

Planning reuses fresh research conservatively:

- files with a parseable in-file `Date:`, `Last Updated:`,
  `**Date**:`, or `**Last Updated**:` value within the last 48 hours
  can suppress duplicate
  `web-researcher` / `ruby-gem-researcher` work when the topic clearly
  matches
- stale files are background context only
- files without parseable freshness metadata are background context only
- current-code agents still need to inspect the live repo
