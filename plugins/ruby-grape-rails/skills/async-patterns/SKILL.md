---
name: async-patterns
description: "Use when implementing fiber-based concurrency with the async gem, Falcon server, or concurrent I/O-bound Ruby operations."
when_to_use: "Triggers: \"async\", \"fiber\", \"Falcon\", \"concurrent\", \"async gem\"."
user-invocable: false
effort: medium
paths:
  - "lib/**/*.rb"
  - "**/lib/**/*.rb"
---
# Async Patterns

Fiber-based concurrency for Ruby using the `async` gem.

## Overview

The `async` gem provides fiber-based concurrency:

| Approach | Use Case | Concurrency Model |
|----------|----------|-------------------|
| **Threads** | CPU-bound work | OS threads |
| **Async** | I/O-bound work | Fibers (lightweight) |
| **Processes** | Isolation | Fork/spawn |

Use **async** when:

- Making many HTTP requests
- Reading from multiple files/streams
- Database queries that can run in parallel
- WebSocket handling
- High-concurrency I/O

## Installation

```ruby
# Gemfile
gem 'async'
gem 'async-http'       # HTTP client
gem 'async-io'         # I/O operations
gem 'falcon'           # Async web server (optional)

# Rails integration
gem 'async-job'        # Async job processor
gem 'async-cable'      # Async Action Cable (optional)
```

## Basic Async

### Simple Task

```ruby
require 'async'

Async do |task|
  task.sleep(1)
  puts "Done!"
end
```

### Concurrent Operations

```ruby
require 'async'

Async do |task|
  # Spawn multiple concurrent tasks
  tasks = []
  
  tasks << task.async do
    task.sleep(1)
    "Task 1 done"
  end

  tasks << task.async do
    task.sleep(0.5)
    "Task 2 done"
  end

  tasks << task.async do
    task.sleep(1.5)
    "Task 3 done"
  end
  
  # Wait for all and get results
  results = tasks.map(&:wait)
  puts results
  # Total time: ~1.5s (not 3s!)
end
```

### Error Handling

```ruby
Async do |task|
  tasks = []
  
  tasks << task.async do
    raise "Task 1 failed"
  end
  
  tasks << task.async do
    "Task 2 success"
  end
  
  results = tasks.map do |t|
    begin
      t.wait
    rescue => e
      { error: e.message }
    end
  end
  
  puts results
  # => [{:error=>"Task 1 failed"}, "Task 2 success"]
end
```

## Concurrent HTTP Requests

### Using async-http

```ruby
require 'async'
require 'async/http/internet'

Async do |task|
  internet = Async::HTTP::Internet.new
  
  # Fetch multiple URLs concurrently
  responses = []
  
  urls = [
    'https://api.example.com/users',
    'https://api.example.com/products',
    'https://api.example.com/orders'
  ]
  
  urls.each do |url|
    responses << task.async do
      response = internet.get(url)
      [url, response.read]
    end
  end
  
  # Wait for all responses
  data = responses.map(&:wait)
  
  # Process results
  data.each do |url, body|
    puts "#{url}: #{body.length} bytes"
  end
  
  internet.close
end
```

### With Timeout

```ruby
require 'async'
require 'async/io/timeout_error'

Async do |task|
  tasks = []
  
  urls.each do |url|
    tasks << task.async do
      Async::Timeout.timeout(5) do
        fetch_url(url)
      end
    rescue Async::TimeoutError
      { url: url, error: 'Timeout' }
    end
  end
  
  results = tasks.map(&:wait)
end
```

## Async Jobs

### Using async-job

```ruby
require 'async/job'
require 'async/job/adapter/active_job'

# Configure adapter
ActiveJob::Base.queue_adapter = :async_job

class MyJob < ActiveJob::Base
  queue_as :default
  
  def perform(user_id)
    user = User.find(user_id)
    # Do work
  end
end

# Enqueue job
MyJob.perform_later(123)

# Process jobs
Async do |task|
  processor = Async::Job::Processor.new
  processor.start
  
  # Jobs process asynchronously
  task.sleep(10)  # Let jobs process
  
  processor.stop
end
```

### Custom Job Processor

```ruby
class AsyncJobProcessor
  def initialize
    @queue = Async::Queue.new
  end
  
  def enqueue(job)
    @queue.enqueue(job)
  end
  
  def start
    Async do |task|
      loop do
        job = @queue.dequeue
        task.async { process(job) }
      end
    end
  end
  
  private
  
  def process(job)
    job.perform
  rescue => e
    logger.error "Job failed: #{e.message}"
  end
end
```

## Falcon Web Server

Falcon is an async web server for Ruby:

### Configuration

```ruby
# falcon.rb
load :rack, :lets_encrypt

rack 'myapp', :lets_encrypt do
  endpoint 'https://example.com'
  
  # SSL
  ssl_certificate_path '/path/to/cert.pem'
  ssl_private_key_path '/path/to/key.pem'
end
```

### Running Falcon

```
# Development
bundle exec falcon serve

# Production
bundle exec falcon host falcon.rb
```

### Rails Integration

```ruby
# config/application.rb
config.middleware.insert_before ActionDispatch::Static, Async::Rack::Adapter

# Or use Falcon as server
# Gemfile
gem 'falcon'
gem 'rackup'

# Start server
bundle exec falcon serve -b tcp://localhost:3000
```

## Async Cable (WebSockets)

```ruby
require 'async/cable'

class ChatChannel < Async::Cable::Channel
  def subscribed
    stream_from "chat_#{params[:room_id]}"
  end
  
  def receive(data)
    broadcast_to "chat_#{params[:room_id]}", {
      user: current_user.name,
      message: data['message']
    }
  end
end
```

## Database Queries

### Concurrent Queries

```ruby
require 'async'
require 'async/postgres'  # or async-mysql2

Async do |task|
  db = Async::Postgres::Pool.new(
    host: 'localhost',
    dbname: 'myapp'
  )
  
  # Run queries concurrently
  results = []
  
  results << task.async { db.query('SELECT * FROM users') }
  results << task.async { db.query('SELECT * FROM products') }
  results << task.async { db.query('SELECT * FROM orders') }
  
  users, products, orders = results.map(&:wait)
  
  db.close
end
```

## Iron Laws

1. **Use async for I/O-bound, threads for CPU-bound**
2. **Always handle fiber scheduling with I/O** - Don't block the reactor
3. **Don't mix sync and async without care** - Use barriers/semaphores
4. **Limit concurrent operations** - Prevent resource exhaustion
5. **Handle errors in each task** - Don't let one failure crash all
6. **Use timeouts for external calls** - Prevent indefinite waits

## Concurrency Patterns

### Semaphore (Limit Concurrent Operations)

```ruby
require 'async/semaphore'

Async do |task|
  semaphore = Async::Semaphore.new(5)  # Max 5 concurrent
  
  urls.each do |url|
    task.async do
      semaphore.acquire do
        download(url)
      end
    end
  end
end
```

### Barrier (Wait for Multiple Tasks)

```ruby
require 'async/barrier'

Async do |task|
  barrier = Async::Barrier.new
  
  urls.each do |url|
    barrier.async(task) do
      download(url)
    end
  end
  
  # Wait for all to complete
  barrier.wait
end
```

### Condition Variable

```ruby
require 'async/condition'

Async do |task|
  condition = Async::Condition.new
  result = nil
  
  task.async do
    result = fetch_data
    condition.signal
  end
  
  # Wait for signal
  condition.wait
  puts result
end
```

## Testing Async Code

```ruby
require 'async/rspec'

RSpec.describe 'Async operations' do
  include Async::RSpec::Reactor
  
  it 'runs tasks concurrently' do
    results = []
    
    Async do |task|
      3.times do |i|
        task.async do
          sleep(0.1)
          results << i
        end
      end
    end
    
    expect(results).to eq([0, 1, 2])
  end
end
```

## Rails Integration & Performance

See: [references/rails-integration.md](references/rails-integration.md) — Rails controller patterns, background processing, performance comparison, and migration guide
