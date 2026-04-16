---
name: rb:n1-check
description: "Use when diagnosing and explaining N+1 query patterns in Rails and Grape codepaths. Use for slow index pages, serializers, nested API responses, and Hotwire screens pulling associated data."
when_to_use: "Triggers: \"N+1\", \"slow query\", \"includes\", \"preload\", \"bullet\", \"query count\"."
argument-hint: "[path|feature]"
effort: medium
paths:
  - "app/{models,controllers,serializers,blueprints,graphql}/**"
  - "**/app/{models,controllers,serializers,blueprints,graphql}/**"
  - "{packs,engines,components}/*/{models,controllers,serializers,blueprints,graphql}/**"
  - "app/{packages,packs}/*/{models,controllers,serializers,blueprints,graphql}/**"
---
# N+1 Check

Look for:

- loops that hit associations lazily
- serializers/presenters causing repeated loads
- controller or endpoint code that fetches parents and then children one-by-one
- missing preload strategy for nested responses
- places where `strict_loading` or Bullet-style checks would surface the problem earlier
