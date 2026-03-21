# Enumerable Patterns

## Lazy Enumeration

```ruby
# Lazy enumeration for large datasets
def process_large_dataset
  File.open('huge_file.csv')
    .lazy
    .map { CSV.parse(it) }
    .select { it[2] == 'active' }
    .map { transform_row(it) }
    .first(100)
end
```

## Chunking and Batching

```ruby
# Chunking for batch operations
def process_in_batches(items, batch_size: 100)
  items.each_slice(batch_size) do |batch|
    yield batch
  end
end

# Grouping with transformation
def group_by_status(orders)
  orders.group_by(&:status).transform_values { it.count }
end

# Finding with fallback
def find_active_user(id)
  users.find { it.id == id && it.active? } || GuestUser.new
end
```
