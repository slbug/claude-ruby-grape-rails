# Data Transformation Patterns

## Functional Pipelines

```ruby
# Chain transformations with `then`
data
  .reject { it.nil? || it.empty? }
  .map { it.strip.downcase }
  .uniq
  .sort
  .then { |items| items.first(10) }

# Object transformation
def transform_user(raw_data)
  raw_data
    .slice(:name, :email, :phone)
    .transform_values { it.to_s.strip }
    .compact
    .then { |data| User.new(**data) }
end
```

## Data Pipeline Example

```ruby
class DataPipeline
  def initialize(data)
    @data = data
  end
  
  def clean
    @data = @data.reject(&:nil?).map(&:strip)
    self
  end
  
  def normalize
    @data = @data.map(&:downcase).uniq
    self
  end
  
  def limit(n)
    @data = @data.first(n)
    self
  end
  
  def to_a
    @data
  end
end

# Usage
result = DataPipeline.new(raw_data)
  .clean
  .normalize
  .limit(100)
  .to_a
```
