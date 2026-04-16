---
name: rb:techdebt
description: "Use when identifying Ruby/Rails/Grape technical debt patterns such as overgrown services, repeated queries, callback sprawl, stale abstractions, and weak boundaries."
when_to_use: "Triggers: \"tech debt\", \"cleanup\", \"overgrown service\", \"callback sprawl\", \"stale code\"."
effort: medium
---
# Technical Debt

Look for:

- duplicated query logic
- callback-driven side effects
- jobs or services with too many responsibilities
- stale or decorative abstractions
- missing tests around risky legacy seams
