## Rails 8.1 Features

### ActiveJob::Continuable

Long-running jobs that exceed timeout limits can use continuations to resume from the last checkpoint:

```ruby
class ProcessLargeDatasetJob < ApplicationJob
  include ActiveJob::Continuable

  def perform(dataset_id)
    @dataset = Dataset.find(dataset_id)

    step :validate do
      @dataset.validate!
    end

    step(:process_records) do |step|
      @dataset.records.find_each(start: step.cursor) do |record|
        process(record)
        step.advance! from: record.id
      end
    end

    step :finalize
  end

  def finalize
    @dataset.mark_complete!
  end
end
```

**Step API:**

- `step :name` - Execute a named method
- `step(:name) { |step| ... }` - Execute a block with step context
- `step.cursor` - Current position in the step (resumes from here if interrupted)
- `step.advance!` - Move cursor forward (uses `succ` on cursor value)
- `step.advance! from: value` - Set cursor to specific value
- `step.set! value` - Set cursor explicitly
- `step.checkpoint!` - Create checkpoint without changing cursor

**Isolated Steps:**

For steps that may exceed the job timeout, use `isolated: true` to ensure the step completes in its own job execution:

```ruby
step :slow_external_api_call, isolated: true
```

**Benefits:**

- Job resumes automatically after interruption (worker restart, timeout)
- Each step has its own retry semantics
- Progress is preserved via cursor
- Natural fit for batch processing and data imports

### Event Reporter - Structured logging

```ruby
Rails.event.notify("order.completed",
  order_id: order.id,
  total: order.total,
  user_id: order.user_id
)
```

### Local CI DSL

```ruby
# config/ci.rb
CI.run do
  step "setup", "bin/setup"
  step "lint", "bin/rubocop"
  step "test", "bin/rspec"
  step "security", "bin/brakeman"
end
```

### Markdown rendering

```erb
<%= markdown @post.content %>
```

### Deprecated associations

```ruby
class User < ApplicationRecord
  has_many :old_orders, -> { where("created_at < ?", 1.year.ago) },
           class_name: "Order",
           deprecated: "Use User.orders.with_deleted instead"
end
```
