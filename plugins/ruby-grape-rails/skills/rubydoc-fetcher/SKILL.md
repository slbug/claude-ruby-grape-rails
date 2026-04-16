---
name: rubydoc-fetcher
description: "Use when looking up Ruby or gem documentation via WebFetch. Covers rubydoc.info, Rails Guides, official gem docs, and API references."
when_to_use: "Triggers: \"rubydoc\", \"gem docs\", \"API reference\", \"Rails Guides\", \"look up method\"."
effort: low
---
# Ruby Doc Fetcher

Use `WebFetch` with focused prompts on:

- `guides.rubyonrails.org`
- `ruby-doc.org`
- `rubydoc.info`
- official gem docs or repository docs
- Sidekiq wiki pages

Extract only the relevant API, examples, and caveats for the current task.
