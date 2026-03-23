---
name: rb:perf
description: Analyze performance issues in Rails, Grape, Active Record, Redis, and Sidekiq. Use for slow endpoints, queue latency, cache misses, object churn, or N+1 reports.
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
