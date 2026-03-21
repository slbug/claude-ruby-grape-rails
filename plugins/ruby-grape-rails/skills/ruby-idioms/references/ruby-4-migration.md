# Ruby 4.0 Migration Guide

## What's New in Ruby 4.0

Ruby 4.0.0 was released on **2025-12-25**.

| Feature | Status | Notes |
|---------|--------|-------|
| ZJIT | Experimental | Successor to YJIT, early benchmarks promising |
| Prism parser | Default | Improved error messages |
| Frozen strings | Enforced | No magical comment needed |
| `it` parameter | Stable | Preferred over numbered params |
| `Ruby::Box` | Experimental | Not recommended yet |

## ZJIT (Ruby 4.0+)

**Status: Experimental** — Not yet recommended for production use.

```ruby
# Verify ZJIT is enabled
puts RubyVM::ZJIT.enabled?  # => true

# Enable:
# - At runtime: ruby --zjit
# - Environment: RUBY_ZJIT=1

# ZJIT goals (in development):
# - Faster warmup compared to YJIT
# - Better memory efficiency
# - Potential performance improvements over YJIT
```

**Note:** Per Ruby 4.0 release notes, ZJIT is experimental. YJIT remains the practical
recommendation for production workloads today.

## Migration Notes

- **Rails 8+**: Fully compatible with Ruby 4.0
- **Rails 7.x**: Compatible, may need gem updates
- **Rails 6.x**: Not recommended for Ruby 4.0

## Version Compatibility

| Feature | Ruby Version | Notes |
|---------|--------------|-------|
| ZJIT | 4.0+ | Experimental successor to YJIT |
| `it` keyword | 3.4+ | Block argument shorthand |
| Pattern matching | 3.0+ | Mature in 3.4+ |
| YJIT | 3.2+ | Still recommended for production (3.2-4.0) |
| Prism parser | 3.4+ | Default in 4.0 |
| Frozen strings | 3.4+ | Enforced in 4.0 |

**Production Recommendation:** Use YJIT on Ruby 3.3+ or 4.0. Rails 7.2+ enables YJIT by default
when available. ZJIT is experimental—test in staging only.
