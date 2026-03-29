# Research: Sidekiq Retry Configuration

Last Updated: 2026-03-28

## Summary

Sidekiq keeps retry settings in job options and middleware-facing configuration,
not in per-run mutable global state [T1]. For this plugin, the safest guidance
is to recommend explicit job-level retry/backoff configuration and to call out
version-sensitive behavior when Sidekiq docs or changelogs say so [T1][T2].

## Recommendation

Keep retry guidance tied to current Sidekiq docs and verify version-sensitive
claims before presenting them to the user.

## Risks

- Older blog posts can describe retry hooks or defaults that no longer match
  the current release [T3].

## Sources

- [T1] <https://github.com/sidekiq/sidekiq/wiki/Error-Handling>
- [T1] <https://github.com/sidekiq/sidekiq/blob/main/Changes.md>
- [T2] <https://github.com/sidekiq/sidekiq/discussions/0000>
