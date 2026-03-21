# Scoring Methodology

How health scores are calculated for each category.

## Score Ranges

| Score | Grade | Status | Meaning |
|-------|-------|--------|---------|
| 90-100 | A | Excellent | No critical issues, minor improvements only |
| 80-89 | B | Good | Few warnings, solid foundation |
| 70-79 | C | Needs Attention | Some issues to address |
| 60-69 | D | Needs Work | Multiple issues, prioritize fixing |
| <60 | F | Critical | Significant problems, immediate action |

## Category Scoring

### Architecture (100 points)

| Criterion | Points | Deductions |
|-----------|--------|------------|
| Context boundaries respected | 25 | -5 per violation |
| Module naming consistency | 15 | -3 per inconsistency |
| Fan-out <5 contexts per module | 15 | -5 per over-coupled module |
| API surface reasonable (<30 funcs/context) | 15 | -5 per bloated context |
| No circular dependencies | 15 | -10 per cycle |
| Folder structure follows conventions | 15 | -5 per deviation |

**Commands used:**

```bash
# Analyze architecture and dependencies
bundle exec rubocop --only Metrics/ClassLength,Metrics/ModuleLength
bundle exec flay lib/ --mass 50
find app -name "*.rb" -type f | wc -l
```

### Performance (100 points)

| Criterion | Points | Deductions |
|-----------|--------|------------|
| No N+1 patterns detected | 30 | -5 per N+1 |
| Indexes for common queries | 20 | -5 per missing index |
| Preloads used appropriately | 15 | -3 per missing preload |
| No Sidekiq bottlenecks | 15 | -10 per bottleneck |
| Hotwire/Turbo streams for large lists | 10 | -5 per regular assign list |
| Queries avoid SELECT * | 10 | -2 per SELECT * |

**Commands used:**

```bash
# Detect N+1 patterns
grep -B5 -A5 "\.map\|\.each" app/ -r --include="*.rb" | grep -E "User\.find|Order\.where"

# Check for eager loading usage
grep -r "\.includes\|\.preload\|\.eager_load" app/ --include="*.rb"

# Check Hotwire/Turbo stream usage in views
grep -r "turbo_stream\|turbo_frame" app/views/ --include="*.erb" --include="*.haml"
```

### Security (100 points)

| Criterion | Points | Deductions |
|-----------|--------|------------|
| No brakeman critical issues | 30 | -15 per critical |
| No brakeman high issues | 20 | -5 per high |
| Authorization in all controller actions | 15 | -10 per missing auth |
| No constantize with user input | 10 | -10 per violation |
| No raw() with untrusted content | 10 | -10 per violation |
| Secrets in ENV only | 15 | -15 per hardcoded secret |

**Commands used:**

```bash
# Run Brakeman security scanner
bundle exec brakeman --exit-on-warn 2>&1 || true

# Check for dangerous constantize calls
grep -r "\.constantize\|constantize" app/ --include="*.rb"

# Check for raw HTML output
grep -r "\.html_safe\|raw(" app/ --include="*.rb" --include="*.erb"

# Check controller authorization patterns
grep -r "before_action\|before_action" app/controllers/ -A5 | grep -v "authorize\|authenticate"
```

### Test Quality (100 points)

| Criterion | Points | Deductions |
|-----------|--------|------------|
| Coverage >70% | 30 | -5 per 10% below 70% |
| No flaky test patterns | 20 | -5 per sleep in test |
| Tests use factories properly | 15 | -2 per raw SQL |
| Database cleaning configured | 15 | -5 per missing |
| Reasonable test duration (<30s avg) | 10 | -5 if slow |
| Error paths tested | 10 | -5 if only happy path |

**Commands used:**

```bash
# Run test suite
bundle exec rspec 2>&1 | tail -30

# Check for sleep in tests (flaky pattern)
grep -r "sleep " spec/ test/ --include="*.rb"

# Check factory usage
grep -r "FactoryBot\|create\|build" spec/ --include="*.rb" | head -20

# Check for database cleaner configuration
grep -r "DatabaseCleaner" spec/ test/ --include="*.rb"
```

### Dependencies (100 points)

| Criterion | Points | Deductions |
|-----------|--------|------------|
| No bundle-audit vulnerabilities | 40 | -20 per vulnerability |
| No gems with known CVEs | 20 | -10 per CVE |
| No major version behind (>2) | 20 | -5 per outdated |
| No unused dependencies | 10 | -3 per unused |
| Version pinning appropriate | 10 | -5 if all loose |

**Commands used:**

```bash
# Check for gem vulnerabilities
bundle exec bundle-audit 2>&1

# List outdated gems
bundle exec bundle outdated 2>&1
```

## Overall Score Calculation

```
overall_score = (
  architecture_score * 0.20 +
  performance_score * 0.25 +
  security_score * 0.25 +
  test_quality_score * 0.15 +
  dependencies_score * 0.15
)
```

**Weighting rationale:**

- Security and Performance weighted highest (25% each) - runtime impact
- Architecture weighted at 20% - long-term maintainability
- Tests and Dependencies at 15% each - important but less immediate

## Grade Assignment

```ruby
case overall_score
when 90..100 then grade = "A"
when 80..89 then grade = "B"
when 70..79 then grade = "C"
when 60..69 then grade = "D"
else grade = "F"
end
```

## Critical Issues Override

Regardless of score, flag as CRITICAL if any:

- Security vulnerability detected
- Hardcoded secrets found
- Rails deprecation warnings present
- Test suite failing
