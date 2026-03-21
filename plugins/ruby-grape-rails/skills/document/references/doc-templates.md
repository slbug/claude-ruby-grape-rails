# Documentation Templates

## YARD/RDoc Module Documentation Template

```ruby
# {Brief description of module purpose}.
#
# @example Basic usage
#   MyApp::Module.function(arg)
#
# @param [Hash] options the options to create a message with
# @option options [String] :option Description of option
#
# @return [Type] Description of return value
#
# @raise [StandardError] When something goes wrong
#
# @see https://example.com/docs
#
# @author Name
# @since 1.0.0
#
module MyApp
  module Module
    # Method implementation
  end
end
```

## Method Documentation Template

```ruby
# {Brief description}.
#
# @param [Type] param Description of parameter
# @param [Type] options Optional parameters
# @option options [Type] :key Description
#
# @return [Type] Description of return value
# @return [Hash] On success with :ok status
# @return [Hash] On failure with :error status
#
# @example Basic usage
#   result = my_method(:arg)
#   # => { status: :ok, data: ... }
#
# @example With options
#   my_method(:arg, option: value)
#
# @raise [ArgumentError] When param is invalid
#
def my_method(param, options = {})
  # implementation
end
```

## README Section Template

For features users interact with:

````markdown
## {Feature Name}

{Brief description}

### Configuration

```ruby
# config/application.rb or config/environments/*.rb
config.my_app.feature.option = value
```

Or using an initializer:

```ruby
# config/initializers/my_feature.rb
MyApp.configure do |config|
  config.feature.option = value
end
```

### Usage

{How to use the feature}
````

## ADR Template

Create `docs/adr/{number}-{title}.md`:

```markdown
# ADR-{n}: {Title}

**Date**: {date}
**Status**: Accepted
**Context**: {Why this decision was needed}

## Decision

{What was decided}

## Consequences

### Positive

- {benefit}

### Negative

- {tradeoff}

## Alternatives Considered

### {Alternative 1}

- Rejected because: {reason}
```

## RDoc Format Alternative

For projects using RDoc instead of YARD:

```ruby
# Description of the method
#
# ==== Parameters
#
# * +param1+ - Description of param1 (Type)
# * +param2+ - Description of param2 (Type)
#
# ==== Returns
#
# * Description of return value
#
# ==== Examples
#
#   my_method(:arg)  # => result
#
def my_method(param1, param2)
  # implementation
end
```

## Rails Generator Documentation

```ruby
# lib/generators/my_app/install/install_generator.rb

module MyApp
  module Generators
    # Generator for installing MyApp in a Rails application.
    #
    # This generator:
    # - Creates initializer file
    # - Copies migration files
    # - Adds routes
    #
    # @example Run the generator
    #   rails generate my_app:install
    #
    class InstallGenerator < Rails::Generators::Base
      source_root File.expand_path('templates', __dir__)

      desc "Installs MyApp in your Rails application"

      def create_initializer
        template 'initializer.rb', 'config/initializers/my_app.rb'
      end
    end
  end
end
```
