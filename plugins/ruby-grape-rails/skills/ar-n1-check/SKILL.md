---
name: rb:n1-check
description: Diagnose and explain N+1 query patterns in Rails and Grape codepaths. Use for slow index pages, serializers, nested API responses, and Hotwire screens pulling associated data.
argument-hint: "[path|feature]"
effort: medium
paths:
  - app/models/**
  - app/controllers/**
  - app/serializers/**
  - app/graphql/**
  - "**/app/models/**"
  - "**/app/controllers/**"
  - "**/app/serializers/**"
---
# N+1 Check

Look for:

- loops that hit associations lazily
- serializers/presenters causing repeated loads
- controller or endpoint code that fetches parents and then children one-by-one
- missing preload strategy for nested responses
- places where `strict_loading` or Bullet-style checks would surface the problem earlier
