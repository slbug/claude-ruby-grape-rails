# Ruby Documentation Best Practices

## RDoc/YARD Documentation

- First line: One sentence summary
- Include usage examples with Ruby code
- Include `## Options` if configurable
- Link to related classes/modules with `See also`

## Method Documentation

- First line: What it does (imperative)
- `@param` with types and descriptions
- `@return` with type and description
- `@example` with Ruby code

## Type Signatures

Use Sorbet or RBS for type signatures:

```ruby
# Sorbet example
sig { params(user: User).returns(T.any(MagicToken, ActiveRecord::RecordInvalid)) }
def create_magic_token(user)
  # ...
end
```
