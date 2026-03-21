# Sidekiq::Iteration Deep Dive

## Batch Processing

Process large datasets in resumable chunks:

```ruby
class ProcessUsersJob
  include Sidekiq::Job
  include Sidekiq::Iteration

  def build_enumerator(cursor:)
    Product.all.cursor_rows(cursor: cursor)
  end

  def each_iteration(product)
    product.update_search_index!
  end
end
```

## With Batch Size

```ruby
class ProcessInBatchesJob
  include Sidekiq::Job
  include Sidekiq::Iteration

  def build_enumerator(cursor:)
    Product.in_batches(of: 100).cursor_rows(cursor: cursor)
  end

  def each_iteration(batch)
    batch.each(&:update_search_index!)
  end
end
```

## Custom Enumerator

```ruby
class ProcessCsvJob
  include Sidekiq::Job
  include Sidekiq::Iteration

  def build_enumerator(cursor:)
    CSV.read('large_file.csv', headers: true).each_with_index.drop(cursor || 0).to_enum
  end

  def each_iteration((row, index))
    process_row(row)
  end
end
```

## Benefits

- **Resumable**: Stops cleanly, resumes from last position
- **Memory efficient**: One record at a time
- **Interruptible**: Responds to shutdown signals
- **Observable**: Progress in Web UI
