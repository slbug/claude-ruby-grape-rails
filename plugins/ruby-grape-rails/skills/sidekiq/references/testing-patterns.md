# Sidekiq Testing Patterns Reference

> **Official docs**: <https://github.com/sidekiq/sidekiq/wiki/Testing>

## Configuration

```ruby
# spec/support/sidekiq.rb
require 'sidekiq/testing'

# Choose your testing mode:
# :inline - executes jobs immediately
# :fake - stores jobs in arrays (default, recommended)
Sidekiq::Testing.fake!

RSpec.configure do |config|
  config.before do
    Sidekiq::Job.clear_all
  end
end
```

## Assert Enqueued

```ruby
require 'rails_helper'

RSpec.describe UserRegistration do
  describe '#create' do
    let(:user) { create(:user, email: 'test@example.com') }

    before { user }

    it 'enqueues welcome email job' do
      expect {
        UserRegistration.new(email: 'test@example.com').create
      }.to change(WelcomeJob.jobs, :size).by(1)

      # Verify job args
      expect(WelcomeJob.jobs.last['args']).to eq([user.id])
    end

    it 'enqueues with specific args' do
      UserRegistration.new(email: 'test@example.com').create

      expect(WelcomeJob).to have_enqueued_sidekiq_job(user.id)
    end

    it 'does not enqueue for invalid email' do
      expect {
        UserRegistration.new(email: 'invalid').create
      }.not_to change(WelcomeJob.jobs, :size)
    end
  end
end
```

## Execute Jobs

```ruby
RSpec.describe OrderJob do
  describe '#perform' do
    it 'processes valid order' do
      order = create(:order, status: 'pending')
      
      # Inline execution
      OrderJob.new.perform(order.id)
      
      expect(order.reload.status).to eq('processed')
    end
    
    it 'handles missing order' do
      expect {
        OrderJob.new.perform(-1)
      }.to raise_error(ActiveRecord::RecordNotFound)
    end
  end
end
```

## Drain Queues

```ruby
RSpec.describe 'Import workflow' do
  it 'processes all jobs' do
    # Enqueue multiple jobs
    3.times do |i|
      RowImportJob.perform_async(row_ids[i])
    end
    
    # Drain all jobs
    expect {
      RowImportJob.drain
    }.to change { RowImportJob.jobs.size }.from(3).to(0)
    
    # Verify all rows processed
    expect(Row.all.pluck(:status)).to all(eq('processed'))
  end
  
  it 'processes specific queue' do
    # Enqueue to different queues
    CriticalJob.perform_async('urgent')
    LowPriorityJob.perform_async('later')
    
    # Drain only critical queue
    Sidekiq::Queues['critical'].each do |job|
      worker = job['class'].constantize
      worker.new.perform(*job['args'])
    end
    Sidekiq::Queues['critical'].clear
    
    expect(LowPriorityJob.jobs).not_to be_empty
  end
end
```

## Testing Job Options

```ruby
RSpec.describe UniqueJob do
  it 'has correct queue' do
    expect(described_class.get_sidekiq_options['queue']).to eq('critical')
  end
  
  it 'has retry limit' do
    expect(described_class.get_sidekiq_options['retry']).to eq(3)
  end
end
```

## Testing with Time/Scheduling

```ruby
RSpec.describe ReminderJob do
  describe 'scheduled jobs' do
    let(:user) { create(:user) }

    it 'schedules for future' do
      reminder_time = 1.day.from_now

      ReminderJob.perform_at(reminder_time, user.id)

      job = ReminderJob.jobs.first
      expect(job['at']).to eq(reminder_time.to_f)
    end

    it 'processes scheduled jobs', :sidekiq_scheduler do
      # Note: This requires the sidekiq-scheduler gem (not core Sidekiq)
      travel_to(Time.current) do
        ReminderJob.perform_at(1.hour.from_now, user.id)

        # Before time - not executed
        expect {
          Sidekiq::Scheduler.enqueue_scheduled_jobs
        }.not_to change { ReminderJob.jobs.size }

        # After time - executed
        travel 2.hours
        expect {
          Sidekiq::Scheduler.enqueue_scheduled_jobs
        }.to change { ReminderJob.jobs.size }.by(-1)
      end
    end
  end
end
```

**Note:** `Sidekiq::Scheduler` requires the [sidekiq-scheduler](https://github.com/sidekiq-scheduler/sidekiq-scheduler) gem, which is not part of core Sidekiq.

## Mocking External Services

```ruby
RSpec.describe ChargeJob do
  describe '#perform' do
    let(:stripe_double) { class_double(Stripe::Charge).as_stubbed_const }
    
    it 'charges with idempotency key' do
      allow(stripe_double).to receive(:create).and_return(success_response)
      
      ChargeJob.new.perform(user.id, 1000, 'unique-key-123')
      
      expect(stripe_double).to have_received(:create).with(
        hash_including(idempotency_key: 'unique-key-123')
      )
    end
    
    it 'does not double charge' do
      # First attempt
      expect {
        ChargeJob.new.perform(user.id, 1000, 'key-123')
      }.to change(Payment, :count).by(1)
      
      # Second attempt with same key - no new payment
      expect {
        ChargeJob.new.perform(user.id, 1000, 'key-123')
      }.not_to change(Payment, :count)
    end
  end
end
```

## Testing Batches (with sidekiq-batch)

```ruby
RSpec.describe ImportBatchJob do
  it 'creates batch and enqueues jobs' do
    import = create(:import)
    
    expect {
      ImportBatchJob.new.perform(import.id)
    }.to change { Sidekiq::Batch.all.size }.by(1)
    .and change(RowImportJob.jobs, :size).by(3)
  end
end
```

## Anti-patterns

```ruby
# ❌ Testing Sidekiq internals instead of behavior
it 'adds job to queue' do
  MyJob.perform_async('arg')
  expect(Sidekiq::Queues['default'].size).to eq(1)
end

# ✅ Test the behavior/job args
it 'enqueues job with correct args' do
  expect {
    MyService.call
  }.to change(MyJob.jobs, :size).by(1)
  expect(MyJob.jobs.last['args']).to eq(['expected_arg'])
end

# ❌ Not clearing jobs between tests
RSpec.describe 'Tests' do
  it 'first test' do
    MyJob.perform_async('a')
  end
  
  it 'second test - may see job from first!' do
    expect(MyJob.jobs).to be_empty  # Might fail!
  end
end

# ✅ Clear jobs in before hook
RSpec.configure do |config|
  config.before do
    Sidekiq::Job.clear_all
  end
end

# ❌ Testing private job methods directly
it 'processes data' do
  worker = MyJob.new
  worker.instance_variable_set(:@data, 'test')
  worker.send(:process_data)  # Testing private method!
end

# ✅ Test through public interface
it 'processes data' do
  expect {
    MyJob.new.perform('test')
  }.to change { Data.count }.by(1)
end
```
