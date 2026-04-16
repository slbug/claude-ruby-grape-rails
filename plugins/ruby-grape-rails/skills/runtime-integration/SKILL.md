---
name: rb:runtime
description: "Use when integrating with Tidewave Rails for enhanced runtime context, code execution, SQL queries, and introspection of your running Rails application."
when_to_use: "Triggers: \"Tidewave\", \"runtime\", \"live Rails\", \"SQL query\", \"running server\"."
argument-hint: "[inspect|execute|query|docs|logs|models|source]"
effort: low
---
# Runtime Integration

Integrate with [Tidewave Rails](https://github.com/tidewave-ai/tidewave_rails) to enhance context with live system data from your running Rails application.

## Prerequisites

Tidewave Rails must be installed in your project:

```
bundle add tidewave --group development
```

And ensure Tidewave is [installed](https://github.com/tidewave-ai/tidewave_rails) and connected to your Rails app.

**Note:** Runtime features require both:

1. Tidewave gem in your project
2. Tidewave MCP tools available in your Claude Code session

## What Runtime Integration Provides

- **Execute Ruby code** in your running Rails app context
- **Query database** directly via SQL
- **Fetch documentation** for your exact gem versions
- **Read application logs** in real-time
- **Introspect models** and source locations
- **Auto-capture errors** during investigations

## Detection

The `detect-runtime.sh` hook runs automatically at session start and detects:

```
# Detected from Gemfile:
TIDEWAVE_GEM_PRESENT=true
TIDEWAVE_PROJECT_CAPABLE=true

# Example subset persisted in .claude/.runtime_env for hook coordination:
HOOK_MODE=default
BETTERLEAKS_AVAILABLE=true
RTK_AVAILABLE=true
```

These values are persisted in `${REPO_ROOT}/.claude/.runtime_env` as a
sourceable cache of startup detection results. Contributor tooling and hooks
may read or source that file when they want the cached values, but they are not
automatically exported into every hook process environment and current hooks do
not rely on it exclusively.

If Tidewave is not detected, runtime commands will provide setup guidance.

## Commands

### `/rb:runtime inspect`

Display runtime capability status:

```
/rb:runtime inspect
```

Shows:

- Tidewave gem detected in project
- MCP tool availability status
- Rails/Ruby version info

### `/rb:runtime execute <ruby-code>`

Execute Ruby code in Rails console context:

```
/rb:runtime execute "User.recent.count"
/rb:runtime execute "Rails.application.config.active_job.queue_adapter"
```

**Maps to:** `mcp__tidewave__project_eval`

### `/rb:runtime query <sql>`

Execute SQL queries directly against the database:

```
/rb:runtime query "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '1 day'"
```

**Maps to:** `mcp__tidewave__execute_sql_query`

### `/rb:runtime docs <module-or-method>`

Fetch documentation for your exact gem versions:

```
/rb:runtime docs "ActiveRecord::QueryMethods"
/rb:runtime docs "User#valid_email?"
```

**Maps to:** `mcp__tidewave__get_docs`

### `/rb:runtime logs [level]`

Read application logs:

```
/rb:runtime logs
/rb:runtime logs error
/rb:runtime logs warning
```

**Maps to:** `mcp__tidewave__get_logs`

### `/rb:runtime models`

List all models/modules for quick discovery:

```
/rb:runtime models
```

**Maps to:** `mcp__tidewave__get_models`

### `/rb:runtime source <module-or-method>`

Get source location for direct code reading:

```
/rb:runtime source "User"
/rb:runtime source "User#authenticate"
```

**Maps to:** `mcp__tidewave__get_source_location`

## Integration Points

### With /rb:investigate

When investigating issues:

1. Checks for recent errors via `mcp__tidewave__get_logs`
2. Queries related database state via `mcp__tidewave__execute_sql_query`
3. Inspects code via `mcp__tidewave__get_source_location`
4. Presents findings with context

### With /rb:plan

When planning features:

1. Shows current system state
2. Queries existing data patterns
3. Validates assumptions with real data

### With /rb:work

When implementing:

1. Executes code to test changes
2. Queries results
3. Validates against live state

## Available Tidewave MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `project_eval` | Execute Ruby code | `User.count` |
| `execute_sql_query` | Run SQL | `SELECT * FROM users` |
| `get_docs` | Fetch docs | `ActiveRecord::Base` |
| `get_logs` | Read logs | `level: :error` |
| `get_models` | List models | All app modules |
| `get_source_location` | Find source | `User#authenticate` |

## Configuration

Tidewave is configured via your Rails application. Common options:

```ruby
# config/environments/development.rb

# Allow remote access (default: localhost only)
config.tidewave.allow_remote_access = true

# Set your team ID
config.tidewave.team = { id: "my-company" }

# Specify preferred ORM (:active_record or :sequel)
config.tidewave.preferred_orm = :active_record
```

See [Tidewave Rails README](https://github.com/tidewave-ai/tidewave_rails) for full configuration options.

## Security Considerations

1. **Tidewave is development-only** - It raises an error if code reloading is disabled (production)
2. **Localhost by default** - Only accepts requests from localhost unless explicitly configured
3. **Never expose secrets** in runtime output
4. **Audit logging** - All runtime commands are logged by Tidewave

## When Tidewave Is Unavailable

If Tidewave is not installed or MCP tools are unavailable:

```
⚠️  Tidewave not detected

Runtime features require Tidewave Rails:

1. Add to Gemfile:
   bundle add tidewave --group development

2. Install and connect Tidewave:
   https://github.com/tidewave-ai/tidewave_rails

3. Restart Claude Code with MCP tools enabled

Without Tidewave, use:
- /rb:investigate for file-based debugging
- /rb:trace for code flow analysis
- rails console manually
```

## Examples

### Investigating a Bug

```
# Check recent errors
/rb:runtime logs error

# Query related state
/rb:runtime query "SELECT * FROM users WHERE email IS NULL"

# Inspect the code
/rb:runtime source "User#normalize_email"
```

### Planning with Live Data

```
# Check current data volume
/rb:runtime execute "User.where('created_at > ?', 1.year.ago).count"

# Review data patterns
/rb:runtime query "SELECT status, COUNT(*) FROM orders GROUP BY status"
```

### Validating Implementation

```
# After implementing a job
/rb:runtime execute "MyJob.perform_later(123)"

# Check Sidekiq queue status via Ruby
/rb:runtime execute "Sidekiq::Queue.new('default').size"
```

## References

- [Tidewave Rails README](https://github.com/tidewave-ai/tidewave_rails)
- [Proactive Patterns](references/proactive-patterns.md)
- [Validation Checklist](references/validation-checklist.md)
