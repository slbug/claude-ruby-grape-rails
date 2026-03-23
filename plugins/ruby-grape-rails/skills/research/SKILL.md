---
name: rb:research
description: Research Ruby gems, Rails/Grape patterns, upgrade paths, or architectural choices. Use when the team needs evidence before adding a gem or adopting a pattern.
argument-hint: <topic>
disable-model-invocation: true
effort: high
---
# Research Ruby Approaches

Research with primary sources first, synthesize findings, and provide actionable recommendations.

## Research Process

```

## Repository Topology Check

Before deep research in an existing codebase, identify:

- which package/app owns the code in question
- which ORM that package uses
- whether Packwerk or a similar modular-monolith structure is present

If the repo appears modular but explicit Packwerk signals are absent, ask:

`No Packwerk detected. Do you have something similar implemented? Where are the modules/packages and what stack/ORM does each use?`
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

## File-First Output Pattern

Write research to `.claude/research/{slug}.md`:

```markdown
# Research: [Topic]

**Date**: 2026-03-21
**Requested by**: [context]
**Researcher**: [agent name]

## Executive Summary
[2-3 sentences with recommendation]

## Findings

### [Aspect 1]
**Question**: [what we researched]

**Sources**:
- [Source 1](link) - [relevance]
- [Source 2](link) - [relevance]

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
