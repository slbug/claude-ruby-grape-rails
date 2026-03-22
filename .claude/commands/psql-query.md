---
name: psql-query
description: Run ad-hoc PostgreSQL analytics queries against dev/test database
---

# PostgreSQL Analytics

Run analytics queries against the local database using Tidewave Rails MCP tools.

## Rules

- NEVER run against production
- Use READ-ONLY queries (SELECT only)
- For complex analysis, use `mcp__tidewave__project_eval` with ActiveRecord
- Format results as ASCII tables or pipe to `column -t`

## Runtime Tooling Integration

Uses Tidewave Rails MCP tools for database queries:

- `mcp__tidewave__execute_sql_query` for direct SQL queries
- `mcp__tidewave__project_eval` for Active Record-based queries

## Workflow

1. Check if Tidewave is available via `.claude/.runtime_env`
2. If available, use `mcp__tidewave__execute_sql_query "YOUR QUERY"`
3. If Tidewave is not available, explain setup requirements and stop
4. Summarize results

## Example prompts

- "How many users signed up this week?"
- "Show me the slowest queries from pg_stat_statements"
- "What's the table size distribution?"
- "Show index usage stats"
