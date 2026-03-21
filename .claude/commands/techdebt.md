---
name: techdebt
description: Find and report technical debt in the codebase
---

# Tech Debt Scanner

Scan the codebase for common Ruby/Rails/Grape tech debt patterns.

## Check for

1. **Dead code**: Unused methods, classes, modules
   - Grep for `# TODO`, `# FIXME`, `# HACK`
   - Look for commented-out code blocks
2. **Duplicated code**: Similar method bodies across classes
3. **Missing documentation**: Public methods without YARD docs
4. **Large classes/methods**: Files > 300 lines, methods > 50 lines
5. **Missing tests**: Models/controllers without corresponding spec/test files
6. **Deprecated patterns**: Old Rails/Active Record anti-patterns
7. **Linter issues**: `bundle exec rubocop` or `bundle exec standardrb`
8. **Code complexity**: High cyclomatic complexity methods
9. **N+1 queries**: Missing `includes`/`preload` in Active Record queries

## Output format

Priority-sorted list with file:line references and suggested fixes.
