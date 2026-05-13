---
name: rubydoc-fetcher
description: "Looking up Ruby or gem documentation cheaply via WebFetch: rubydoc.info, Rails Guides, official gem docs, API references. Low-MCP-token doc retrieval. Triggers: \"rubydoc\", \"gem docs\", \"API reference\", \"Rails Guides\", \"look up method\". Do NOT use for: gem-vs-gem evaluation, implementing the API."
effort: low
disable-model-invocation: true
---
# Ruby Doc Fetcher

Use `WebFetch` with focused prompts on:

- `guides.rubyonrails.org`
- `ruby-doc.org`
- `rubydoc.info`
- official gem docs or repository docs
- Sidekiq wiki pages

Extract only the relevant API, examples, and caveats for the current task.
