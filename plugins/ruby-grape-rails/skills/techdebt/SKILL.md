---
name: rb:techdebt
description: "Tech debt: overgrown services, query repetition, callback sprawl."
when_to_use: "Triggers: tech debt, cleanup, callback sprawl, stale code."
effort: medium
---
# Technical Debt

Look for:

- duplicated query logic
- callback-driven side effects
- jobs or services with too many responsibilities
- stale or decorative abstractions
- missing tests around risky legacy seams
