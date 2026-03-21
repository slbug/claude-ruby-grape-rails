# Solid Queue Migration Guide

## When to Migrate

Use Solid Queue when:

- No Redis available
- Moderate throughput (<1,000 jobs/sec)
- Prefer simplicity over performance
- Want database-level job visibility
- Rails 8+ new application

## Database Schema

Solid Queue uses three tables:

```ruby
# solid_queue_jobs - Queued jobs
SolidQueue::Job.where(class_name: "MyJob").count

# solid_queue_claimed_executions - Currently processing
SolidQueue::ClaimedExecution.where(class_name: "MyJob").count

# solid_queue_recurring_executions - Recurring schedules
```

## Configuration

```ruby
# config/application.rb
config.active_job.queue_adapter = :solid_queue

# config/solid_queue.yml
production:
  workers:
    - queues: [critical, default]
      threads: 5
      polling_interval: 1
    - queues: [low]
      threads: 3
      polling_interval: 5
```

## Mission Control UI

```ruby
# Gemfile
gem "mission_control-jobs"

# config/routes.rb
mount MissionControl::Jobs::Engine => "/jobs"
```

Access at `/jobs` for queue management.

## Recurring Tasks

```yaml
# config/recurring.yml
production:
  daily_cleanup:
    class: DailyCleanupJob
    schedule: every day at 2am
    
  hourly_sync:
    class: SyncJob
    schedule: every hour
```

## Migration Checklist

- [ ] Change queue adapter
- [ ] Update job classes (ActiveJob)
- [ ] Configure recurring tasks
- [ ] Set up Mission Control
- [ ] Update deployment (no Redis needed)
