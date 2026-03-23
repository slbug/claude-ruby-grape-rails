# Iron Law Violation Patterns

Detailed patterns for detecting Iron Law violations.

## Critical Violations (Must Fix)

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
DB.after_commit { MyJob.perform_async(record.id) }  # CORRECT
```

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

## Warning Violations (Should Fix)

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

### Law 18: Bare Rescue

**Pattern**: `rescue` without specifying exception class.

```ruby
rescue  # Catches Exception!
```

**Fix**:

```ruby
rescue StandardError => e
```

### Law 19: DB Queries in Turbo Streams

**Pattern**: Querying DB during turbo_stream template rendering.

**Fix**: Pre-compute in controller, render from local variable.

### Law 20: Missing Turbo Frame Tags

**Pattern**: Full page content without turbo_frame_tag.

**Fix**: Wrap partial update content in `turbo_frame_tag`.

## Grep Patterns

```bash
# Law 1: Money as float
grep -r "t\.float.*\(price\|amount\|cost\|balance\)" db/migrate/

# Laws 2, 15: SQL interpolation
grep -r "where.*#{" app/
grep -r "order.*#{" app/
grep -r "find_by_sql" app/

# Law 14: html_safe
grep -r "\.html_safe" app/
grep -r "raw(" app/

# Law 6: Validation bypass
grep -r "update_columns\|update_column\|save.*validate.*false" app/

# Law 7: default_scope
grep -r "default_scope" app/models/

# Law 10: Sidekiq with objects
grep -r "perform_later.*current_user\|perform_async.*current_user" app/

# Laws 4, 11: after_save with jobs
grep -r "after_save.*:\|after_save do" app/models/ | grep -v "after_commit"

# Law 12: eval
grep -r "eval(" app/ | grep -v "# eval"

# Law 16: method_missing
grep -r "def method_missing" app/ | xargs grep -L "respond_to_missing"

# Law 18: Bare rescue
grep -r "rescue\s*$\|rescue\s*=>" app/ | grep -v "StandardError"

# Law 19: DB in turbo streams
grep -r "\.where\|\.find\|\.find_by" app/views/*.turbo_stream.*
```

## Confidence Levels

**High**: Pattern is unambiguous violation (e.g., `t.float :price`, `where("id = #{id}")`)

**Medium**: Pattern is likely violation, needs context (e.g., `update_columns` in controller)

**Low**: Pattern might be okay, flag for review (e.g., `raw()` with hardcoded string)
