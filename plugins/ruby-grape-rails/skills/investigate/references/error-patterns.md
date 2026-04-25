# Error Patterns - Read Error LITERALLY

## Common Ruby/Rails/Grape Errors

| Error | Literal Meaning | Check |
|-------|-----------------|-------|
| `NoMethodError: undefined method 'foo' for nil:NilClass` | Called method on nil | Check if object was properly loaded |
| `NameError: uninitialized constant MyMod` | Class/module doesn't exist | Typo in class name? Missing require? |
| `ActiveRecord::RecordNotFound` | Record doesn't exist in DB | Wrong ID? Data deleted? |
| `ArgumentError: wrong number of arguments` | Method arity mismatch | Check method signature |
| `ActiveRecord::StatementInvalid` | SQL error | Check query syntax, missing table/column |
| `LoadError: cannot load such file` | Missing file or gem | Check gemfile, file path |
| `SyntaxError` | Ruby syntax issue | Check brackets, quotes, blocks |
| `TypeError: no implicit conversion` | Wrong type passed | Check data types in operation |

## Ralph Wiggum Checklist

Spawn `deep-bug-investigator` (writes to
`.claude/investigations/deep-bug-investigator/{slug}-{datesuffix}.md`) to check:

1. Is the file saved?
2. Nil checking - did you call method on nil?
3. Is data eager loaded? (includes/preload)
4. Is the variable name correct?
5. Is nil being passed somewhere unexpected?
6. Did the transaction rollback?
7. Did you restart the server / sidekiq?

## Debug Logging

```ruby
# Add to suspected location
Rails.logger.debug "DEBUG: data after transform: #{data.inspect}"
```

## When Stuck

1. `Rails.logger.debug binding.local_variables.inspect`
2. Add `debugger` (ruby/debug gem) and step through
3. Check if code is even being reached (add `Rails.logger.debug "HERE"`)
4. Compare working vs broken path
