# Iron Law Violation Patterns

Detailed patterns for detecting Iron Law violations.

## Blocker Violations (Must Fix)

All Iron Law violations are Blockers per
`plugins/ruby-grape-rails/skills/triage/references/triage-patterns.md`
§ "Always Fix". Subsections below cover Laws 1-20 by detection
pattern, not Law number. The "Detection Patterns" section at the
bottom contains per-law fenced regex blocks for Laws 1, 2, 4, 6, 7,
10-12, 14-16, 18-19. Laws 3, 5, 8, 9, 13, 17, 20 require manual
review (context check or absence check — no single grep covers
them). Laws 21 + 22 (discipline rules) are equally Blockers — see
`fix-priority.md`.

### Law 1: Float for Money

**Patterns**:

- `t.float :price`, `t.float :amount`, `t.float :cost`, `t.float :balance`

**Fix**:

```ruby
t.decimal :price, precision: 10, scale: 2
t.decimal :amount, precision: 15, scale: 4
```

### Laws 2, 15: SQL Injection

**Patterns**:

```ruby
User.where("name = '#{name}'")
User.order("#{column} #{direction}")
User.find_by_sql("SELECT * FROM users WHERE id = #{id}")
```

**Fix**:

```ruby
User.where(name: name)
User.order(column => direction)
User.where(id: id)
```

### Law 14: html_safe on Untrusted Content

**Patterns**:

```ruby
user_input.html_safe
raw(user_input)
content_tag(:div, user_input.html_safe)
```

**Fix**: Don't mark untrusted content as safe. Use Rails' auto-escaping.

### Law 6: Validation Bypass

**Patterns**:

```ruby
user.update_columns(name: "John")
user.update_column(:name, "John")
user.save(validate: false)
```

**Fix**: Use normal `update()` unless you have a documented exception.

### Law 7: Default Scope

**Pattern**: `default_scope { where(active: true) }`

**Fix**: Use explicit named scopes.

### Law 10: Sidekiq with Objects

**Pattern**: Passing ORM objects to jobs

```ruby
MyJob.perform_later(current_user)  # WRONG
```

**Fix**: Pass IDs only.

```ruby
MyJob.perform_later(current_user.id)  # CORRECT
```

### Laws 4, 11: after_save with Jobs

**Pattern**: Using `after_save` or inline-before-commit enqueueing instead of a commit-safe ORM hook

```ruby
after_save :enqueue_job  # WRONG
```

**Fix (Active Record)**:

```ruby
after_commit :enqueue_job, on: :create  # CORRECT
```

**Fix (Sequel transaction)**:

```ruby
DB.transaction do
  record = Order.create(...)
  DB.after_commit { MyJob.perform_async(record.id) }  # CORRECT
end
```

Use `DB.after_commit` when the job depends on an explicit transaction or on
multiple writes committing together. If there is no surrounding transaction and
the job only depends on the just-created row, `record = Order.create(...)`
followed by `MyJob.perform_async(record.id)` can be acceptable, because Sequel
uses autocommit by default and `Model#save` is one of the operations that uses
an implicit transaction. Treat that as a narrow Sequel exception, not the
default recommendation: the plugin's default guidance remains "prefer the
active ORM's commit-safe hook when enqueue timing matters."

### Law 12: Eval with User Input

**Pattern**: `eval(params[:code])`, `instance_eval(user_input)`

**Fix**: Never eval user input. Use safe alternatives like JSON.parse.

### Law 16: method_missing Without respond_to_missing?

**Pattern**:

```ruby
def method_missing(method, *args)
  @target.send(method, *args)
end
```

**Fix**:

```ruby
def method_missing(method, *args)
  @target.send(method, *args)
end

def respond_to_missing?(method, include_private = false)
  @target.respond_to?(method, include_private)
end
```

### Law 13: Missing Authorization

**Pattern**: Controller actions without explicit authorization checks.

**Fix**: Add authorization in every action or use `before_action` with per-action verification.

### Law 3: N+1 Queries

**Pattern**: Loop accessing associations without eager loading.

```ruby
@users = User.all
@users.each { |u| puts u.orders.count }  # Query per user
```

**Fix**:

```ruby
@users = User.includes(:orders)
@users.each { |u| puts u.orders.count }
```

### Law 18: No Rescue Exception

**Pattern**: `Exception` (or `::Exception`) appearing as a rescued
class in any `begin/rescue` clause or Rails `rescue_from`, including
multi-class lists. All forms catch `SignalException` / `SystemExit`,
hanging processes on interrupt and hiding crashes. Bare `rescue`
defaults to `StandardError` and is not a Law 18 violation. Silent
swallow without re-raise is a separate bug, orthogonal to Law 18.

```ruby
rescue Exception => e             # catches SIGINT, SystemExit — DANGEROUS
rescue ::Exception => e           # same — DANGEROUS
rescue IOError, Exception => e    # multi-class list — DANGEROUS
rescue_from Exception              # Rails controller form — DANGEROUS
rescue_from ActiveRecord::RecordNotFound, Exception, with: :foo  # DANGEROUS
```

**Fix**:

```ruby
rescue => e                # defaults to StandardError — not a Law 18 violation
rescue SomeSpecificError => e
rescue_from SomeSpecificError, with: :foo
# Either form handles or re-raises. Silent swallow is a separate bug.
```

### Law 19: DB Queries in Turbo Streams

**Pattern**: Querying DB during turbo_stream template rendering.

**Fix**: Pre-compute in controller, render from local variable.

### Law 20: Missing Turbo Frame Tags

**Pattern**: Full page content without turbo_frame_tag.

**Fix**: Wrap partial update content in `turbo_frame_tag`.

## Detection Patterns

Search paths in `app/` unless noted. Run each regex with `rg`,
`grep -E`, or Python `re`.

### Law 1 (path: `db/migrate/`)

```regex
t\.float.*(price|amount|cost|balance)
```

### Laws 2, 15

```regex
where.*#\{
```

```regex
order.*#\{
```

```regex
find_by_sql
```

### Law 6

```regex
update_columns|update_column|save.*validate.*false
```

### Law 7 (path: `app/models/`)

```regex
default_scope
```

### Law 10

```regex
perform_later.*current_user|perform_async.*current_user
```

### Laws 4, 11 (path: `app/models/`, excluding `after_commit`)

```regex
after_save.*:|after_save do
```

### Law 12 (excluding lines containing `# eval`)

```regex
eval\(
```

### Law 14

```regex
\.html_safe
```

```regex
raw\(
```

### Law 16

`def method_missing` files lacking `respond_to_missing`. Manual review.

### Law 18

Matches `Exception` as a rescued class anywhere in the clause —
single class, multi-class list, or Rails `rescue_from(Exception)`.
Bare `rescue` defaults to `StandardError` and does NOT match.
`MyException` / `Exception::Foo` / `MyApp::Exception` may surface as
false positives — confirm by reading the hit.

```regex
\b(?:rescue|rescue_from)\b[^#\n]*?[\s,(]:{0,2}Exception\b
```

### Law 19 (path: `app/views/*.turbo_stream.*`)

```regex
\.where|\.find|\.find_by
```

## Confidence Levels

**High**: Pattern is unambiguous violation (e.g., `t.float :price`, `where("id = #{id}")`)

**Medium**: Pattern is likely violation, needs context (e.g., `update_columns` in controller)

**Low**: Pattern might be okay, flag for review (e.g., `raw()` with hardcoded string)
