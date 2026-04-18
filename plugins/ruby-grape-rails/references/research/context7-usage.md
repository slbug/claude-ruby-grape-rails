# Context7 MCP — Usage Reference

Context7 is an MCP server (Upstash) that returns up-to-date, version-specific
docs for libraries, gems, frameworks, and APIs. The Ruby/Rails/Grape plugin
treats Context7 as an **advisory preference** — use it when available, fall
back to WebFetch otherwise. Nothing in the plugin requires Context7 to be
installed.

## Detection

Context7 is available in the session when any tool matching the pattern
`mcp__*context7*__*` is listed in the tool manifest. Three concrete sources
expose this surface:

| Activation path | Tool prefix |
|-----------------|-------------|
| Server-side connector (claude.ai / CC-managed) | `mcp__claude_ai_Context7__*` |
| Per-user local MCP (`claude mcp add context7 ...`) | `mcp__context7__*` |
| Per-project plugin (`/plugin install context7-plugin@context7-marketplace`) | `mcp__plugin_context7_context7__*` |

All three expose the same two primary tools:

- `resolve-library-id` — take a library name (e.g., `rails`, `sidekiq`,
  `grape`) and return a canonical library identifier.
- `query-docs` (also `get-library-docs` on some variants) — retrieve
  versioned documentation for a resolved library id.

## Usage Flow

1. **Resolve first.** Call `resolve-library-id` with the library name.
2. **Query docs.** Pass the resolved id to `query-docs` with a specific
   question or topic.
3. **Version-pin when possible.** Context7 supports version filtering;
   prefer the version that matches the project's Gemfile.lock or similar.

Example (pseudo-code showing tool calls a subagent might emit):

```
resolve-library-id(libraryName: "sidekiq")
  -> { id: "sidekiq/sidekiq", latest: "8.0.4" }

query-docs(
  libraryId: "sidekiq/sidekiq",
  topic: "middleware registration",
  version: "7.3"
)
  -> <docs excerpt>
```

## Fallback

If the detection check fails (no `mcp__*context7*__*` tools visible), use
`WebFetch` against official sources:

- `https://rubydoc.info/gems/<gem>` — gem-level RubyDoc pages
- `https://guides.rubyonrails.org/` — Rails Guides
- `https://api.rubyonrails.org/` — Rails API reference
- Official gem repositories (`README.md`, `docs/`)

## When Not to Use Context7

- User explicitly asks for raw API fetch ("fetch the actual page").
- Topic is project-local business logic — Context7 is for public libraries.
- Looking up Ruby **stdlib** — use `rubydoc.info/stdlib/` or local `ri`.

## Related Files

- `plugins/ruby-grape-rails/references/preferences.yml` — the advisory
  preference itself.
- `plugins/ruby-grape-rails/hooks/scripts/inject-iron-laws.sh` — generated
  subagent payload; includes a one-line Advisory Preference section with
  Context7 guidance.
