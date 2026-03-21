# Async Rails Integration and Performance

Rails-specific patterns and performance considerations for async code.

## Rails Integration

### Async Controller Actions

```ruby
class ApiController < ApplicationController
  def parallel_fetch
    Async do |task|
      user_task = task.async { User.find(params[:user_id]) }
      posts_task = task.async { Post.where(user_id: params[:user_id]) }
      
      user = user_task.wait
      posts = posts_task.wait
      
      render json: { user: user, posts: posts }
    end
  end
end
```

### Async Background Processing

```ruby
class DataImporter
  def import(file_paths)
    Async do |task|
      semaphore = Async::Semaphore.new(3)
      
      file_paths.each do |path|
        task.async do
          semaphore.acquire do
            process_file(path)
          end
        end
      end
    end
  end
  
  private
  
  def process_file(path)
    File.open(path) do |file|
      CSV.foreach(file) do |row|
        import_row(row)
      end
    end
  end
end
```

## Performance Comparison

### Sequential vs Async HTTP Requests

```ruby
# Sequential: 3 seconds
urls.each { |url| Net::HTTP.get(URI(url)) }

# Async: ~1 second (depending on slowest)
Async do |task|
  urls.map { |url| task.async { Net::HTTP.get(URI(url)) } }
      .map(&:wait)
end
```

### Memory Usage

| Approach | Memory per Connection | 1000 Connections |
|----------|----------------------|------------------|
| Threads  | ~2-4 MB              | ~2-4 GB          |
| Fibers   | ~4 KB                | ~4 MB            |

## When NOT to Use Async

- CPU-intensive calculations (use threads/processes)
- Blocking C extensions (will block reactor)
- Heavy database writes (transaction conflicts)
- Operations requiring strict ordering

## Migration from Synchronous Code

```ruby
# Before: Synchronous
results = urls.map { |url| fetch(url) }

# After: Asynchronous
results = Async do |task|
  urls.map { |url| task.async { fetch(url) } }
      .map(&:wait)
end.wait
```
