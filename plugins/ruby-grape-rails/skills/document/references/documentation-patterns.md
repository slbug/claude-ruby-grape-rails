# Documentation Patterns

## Contents

- [Module Documentation Templates](#module-documentation-templates)
- [Method Documentation Templates](#method-documentation-templates)
- [ADR Template](#adr-template)
- [README Section Template](#readme-section-template)

## Module Documentation Templates

### Context Module

```ruby
# The Accounts context manages user registration, authentication, and profile management.
#
# This context is the public API for all user-related operations. Controllers and
# views should call methods here rather than accessing models directly.
#
# ## Methods
#
# ### Registration
#
# * `register_user(attrs)` - Creates a new user account
# * `confirm_user(user)` - Confirms email address
#
# ### Authentication
#
# * `authenticate_user(email, password)` - Validates credentials
# * `create_session(user)` - Creates a new session
#
# ## Examples
#
#     Accounts.register_user(email: "user@example.com", password: "secret123")
#     # => #<User id: 1, ...>
#
#     Accounts.authenticate_user("user@example.com", "wrong")
#     # => nil
#
module Accounts
  extend self
  # ...
end
```

### Model Class

```ruby
# Schema representing a user account.
#
# ## Fields
#
# * `email` - User's email address (unique, required)
# * `password_digest` - BCrypt hashed password
# * `confirmed_at` - When email was confirmed (nil if unconfirmed)
# * `role` - User role: 'member' | 'admin'
#
# ## Validations
#
# * Validates email presence and uniqueness
# * Validates password length (min 8 characters)
#
# ## Associations
#
# * `posts` - Has many posts
# * `comments` - Has many comments
#
class User < ApplicationRecord
  # ...
end
```

### Controller/View Module (Hotwire/Turbo)

```ruby
# Controller for user registration with Hotwire/Turbo support.
#
# ## Instance Variables
#
# * `@user` - The registration form object
# * `@form` - Form builder object
#
# ## Actions
#
# * `new` - Renders registration form
# * `create` - Submits registration form
# * `validate` - Validates form via Turbo (AJAX)
#
# ## Routes
#
#     get '/users/register', to: 'registrations#new'
#     post '/users/register', to: 'registrations#create'
#
class RegistrationsController < ApplicationController
  # ...
end
```

### Service Class

```ruby
# Service that tracks request rates per IP address.
#
# ## Why a Service?
#
# This uses a service class (rather than model callbacks) because:
# - Needs periodic cleanup of expired entries
# - Coordinates with external rate limit service
# - Requires atomic check-and-increment operations
#
# ## State
#
# Stores IP addresses to request counts and timestamps in Redis:
#
#     { "192.168.1.1" => { count: 5, window_start: Time.now } }
#
# ## Configuration
#
#     RateLimiter.configure do |config|
#       config.max_requests = 100
#       config.window_seconds = 60
#     end
#
# ## Usage
#
#     case RateLimiter.check("192.168.1.1")
#     when :ok then proceed
#     when :rate_limited then return_429
#     end
#
class RateLimiter
  # ...
end
```

### Sidekiq Job

```ruby
# Sidekiq job for sending emails asynchronously.
#
# ## Idempotency
#
# Uses `email_id` as idempotency key. Safe to retry - checks if email
# already sent before processing.
#
# ## Arguments
#
# * `email_id` - ID of the Email record to send
# * `template` - Email template name
#
# ## Queue
#
# Runs on `:mailers` queue with rate limiting.
#
# ## Example
#
#     SendEmailWorker.perform_async(email_id: 123, template: "welcome")
#
class SendEmailWorker
  include Sidekiq::Job
  # ...
end
```

## Method Documentation Templates

### Context Method

```ruby
# Creates a magic link token for passwordless authentication.
#
# Generates a secure random token, stores it in the database with an expiration
# time, and returns the token for inclusion in an email link.
#
# @param user [User] The user to create a token for
# @param expires_in [Integer] Token lifetime in seconds (default: 86400)
# @return [MagicToken] The magic link token
# @raise [ActiveRecord::RecordInvalid] If token creation fails
#
# @example
#   Auth.create_magic_token(user)
#   # => #<MagicToken token: "abc123...">
#
# @example With custom expiration
#   Auth.create_magic_token(user, expires_in: 3600)
#   # => #<MagicToken token: "def456...">
#
def create_magic_token(user, expires_in: 86_400)
```

### Query Method

```ruby
# Lists users matching the given criteria.
#
# @param criteria [Hash] Filter options
# @option criteria [String] :role Filter by role
# @option criteria [Boolean] :confirmed Filter by confirmation status
# @option criteria [String] :search Search in email/name
# @param opts [Hash] Pagination options
# @option opts [Integer] :page Page number (default: 1)
# @option opts [Integer] :per_page Items per page (default: 20)
# @return [Array<User>] List of users (may be empty)
#
# @example
#   Accounts.list_users(role: :admin)
#   # => [#<User role: :admin>, ...]
#
# @example With search and pagination
#   Accounts.list_users(search: "john", page: 2)
#   # => [#<User>, ...]
#
def list_users(criteria = {}, page: 1, per_page: 20)
```

### Controller Action

```ruby
# Handles the create action from the registration form.
#
# Attempts to register the user. On success, redirects to confirmation page.
# On failure, re-renders form with errors.
#
# @param params [Hash] Form parameters with "user" key
# @return [void] Redirects or renders
#
def create
  @user = Accounts.register_user(params[:user])
  if @user.persisted?
    redirect_to confirmation_path(@user)
  else
    render :new
  end
end
```

## ADR Template

```markdown
# ADR-{number}: {Title}

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-X
**Deciders**: {who made the decision}
**Technical Story**: {link to issue/PR if applicable}

## Context and Problem Statement

{Describe the context and problem in 2-3 sentences. What forces are at play?
What decision needs to be made?}

## Decision Drivers

* {driver 1, e.g., performance requirement}
* {driver 2, e.g., team familiarity}
* {driver 3, e.g., maintenance burden}

## Considered Options

1. {Option 1}
2. {Option 2}
3. {Option 3}

## Decision Outcome

Chosen option: **"{Option X}"**, because {justification}.

### Positive Consequences

* {positive consequence 1}
* {positive consequence 2}

### Negative Consequences

* {negative consequence 1}
* {mitigation for negative consequence}

## Pros and Cons of the Options

### {Option 1}

{Description}

* Good, because {argument a}
* Good, because {argument b}
* Bad, because {argument c}

### {Option 2}

{Description}

* Good, because {argument a}
* Bad, because {argument b}
* Bad, because {argument c}

## Links

* {Link to related ADR}
* {Link to relevant documentation}
* {Link to discussion/issue}
```

## README Section Template

````markdown
## {Feature Name}

{One paragraph description of what this feature does and why it exists.}

### Configuration

```ruby
config :my_app, :feature_name,
  option_a: "value",
  option_b: 123
```

### Usage

```ruby
MyApp.Feature.do_thing()
```

### Troubleshooting

**Problem**: {Common issue}
**Solution**: {How to fix}
````
