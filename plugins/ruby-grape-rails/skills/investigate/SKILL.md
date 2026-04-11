---
name: rb:investigate
description: "Root-cause analysis for bugs, errors, and failures. Use when something is broken and the cause is unknown. NOT for performance tuning (use perf) or code flow tracing (use rb:trace)."
argument-hint: <bug description>
effort: high
---
# Investigate Ruby Bugs

Run a structured investigation instead of guessing.

## Investigation Tracks

- request path and route trace
- data and transaction analysis
- background job / Redis analysis
- verification and reproduction loop

## Default Tools

- `bundle exec rspec path/to/spec.rb:LINE` or `bin/rails test`
- `bundle exec rails runner`
- `psql` for SQL inspection
- `redis-cli` for queue/cache inspection
- app logs and Sidekiq logs

## Output

Write a short investigation report with:

- observed behavior
- likely root cause
- confirming evidence
- safest next step (`/rb:plan` or `/rb:quick`)

## Agent Dispatch

This is a **skill** (`/rb:investigate`), not an agent. Do NOT spawn `investigate`
or `rb-investigate` via the Agent tool. For agent-based deep investigation, use
`deep-bug-investigator` (`subagent_type: "ruby-grape-rails:deep-bug-investigator"`).
