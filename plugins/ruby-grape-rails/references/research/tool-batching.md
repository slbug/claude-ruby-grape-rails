# Tool Batching

BAD/GOOD pairs for batched tool usage. Companion to the Batch Tool
Calls preference in `references/preferences.yml`.

## git diff

BAD — per-file loop:

```bash
for f in $CHANGED_FILES; do
  git diff "$MERGE_BASE"...HEAD -- "$f"
done
```

GOOD — single batched call by path group:

```bash
git diff "$MERGE_BASE"...HEAD -- app/ lib/
```

GOOD — exclude noise via pathspec:

```bash
git diff "$MERGE_BASE"...HEAD -- . \
  ':(exclude)spec/cassettes/' \
  ':(exclude)spec/fixtures/' \
  ':(exclude)db/schema.rb' \
  ':(exclude)Gemfile.lock'
```

OK — per-file diff when the file is genuinely the unit of
investigation (e.g. deep dive on a single complex change). Note the
reason briefly.

## git log / git blame

BAD — per-file loop:

```bash
for f in $FILES; do git log --oneline -- "$f"; done
```

GOOD — batched by path group:

```bash
git log --oneline "$MERGE_BASE"...HEAD -- app/ lib/
```

## Gem inspection

BAD — per-gem loop:

```bash
for g in rails sidekiq grape; do bundle info "$g"; done
```

GOOD — read Gemfile.lock once, parse:

```bash
grep -E '^\s+(rails|sidekiq|grape) \(' Gemfile.lock
```

GOOD — single inspection when only one gem matters:

```bash
bundle info rails
```

## File reading

BAD — shell `cat`:

```bash
cat app/models/user.rb
```

GOOD — Read tool with a known path. Returns numbered lines, no shell
escaping, no context bloat.

BAD — `cat | grep`:

```bash
cat app/**/*.rb | grep -n "before_action"
```

GOOD — `Grep` tool with a glob (when the tool is available):

```text
Grep(pattern: "before_action", glob: "app/**/*.rb")
```

GOOD — `ugrep` over `app/` when the `Grep` tool is unavailable
(native CC 2.1.117+ macOS/Linux):

```bash
ugrep -n 'before_action' app/
```

## find

BAD — multiple `find` passes:

```bash
find . -name '*.rb'
find . -name '*.erb'
find . -name '*.haml'
```

GOOD — single combined `bfs` pass:

```bash
bfs . -name '*.rb' -o -name '*.erb' -o -name '*.haml'
```

GOOD — `Glob` tool when available.

## Find-exec / xargs cat

BAD — dumps every match into stdout:

```bash
find app -name '*.rb' -exec cat {} +
```

GOOD — `ugrep` (or `Grep` tool) to scope inspection. `Read` tool for
full content of the few files that matter.

## When > 5 shell calls

Stop. Check whether wider batching, `bfs`, `ugrep`, the `Glob` /
`Grep` tools, or fewer `Read`s replaces some of them.

## Exception: skill-body composition

Multi-line bash that runs once at the workflow boundary (e.g.
`resolve-base-ref`, `git diff --stat`, manifest assembly) is allowed.
Discipline targets per-item agent loops, not workflow-boundary
composition.
