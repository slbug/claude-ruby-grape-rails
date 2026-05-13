---
name: rb:perf
description: "Analyzing performance issues in Rails, Grape, Active Record, Redis, and Sidekiq: slow endpoints, queue latency, cache misses, object churn, memory bloat, p95 spikes. Triggers: \"slow\", \"performance\", \"latency\", \"memory\", \"cache miss\", \"queue backup\", \"p95\", \"throughput\". Do NOT use for: confirmed N+1, unknown-cause bugs, code review."
argument-hint: "[path|area] [--focus ar|rails|grape|sidekiq|redis]"
disable-model-invocation: true
effort: high
---
# Performance Analysis

Look for the highest-value improvements first.

## Priorities

- N+1 queries and missing preload strategy
- missing or weak indexes
- avoidable serialization and object churn
- slow background jobs and queue congestion
- Redis key misuse or missing TTL discipline
- heavy controller/API endpoint orchestration

## Output

Return the top findings ordered by impact and effort, then suggest:

- `/rb:plan` for multi-fix work
- `/rb:quick` for one or two small changes
- `/rb:investigate` if the root cause is still uncertain

## References

| Need | Reference |
|---|---|
| benchmark-ips, EXPLAIN ANALYZE, MemoryProfiler, StackProf, flame graphs | `${CLAUDE_SKILL_DIR}/references/benchmarking.md` |
