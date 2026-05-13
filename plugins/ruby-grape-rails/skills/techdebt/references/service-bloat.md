# Service-Object Bloat Detection

Identify service objects whose responsibilities have grown past the
single-purpose threshold.

## Line-count threshold

```bash
find app/services app/interactors app/operations app/commands -name '*.rb' 2>/dev/null \
  | xargs wc -l \
  | awk '$1 > 200 { print }'
```

Threshold: > 200 lines = CRITICAL.

## Public-method count

```ruby
ruby -r ripper -e '
  ARGV.each do |path|
    src = File.read(path)
    tokens = Ripper.lex(src)
    public_defs = 0
    in_private = false
    tokens.each do |(_, kind, text, _)|
      in_private = true if kind == :on_ident && text == "private"
      in_private = false if kind == :on_kw && text == "class"
      public_defs += 1 if !in_private && kind == :on_kw && text == "def"
    end
    puts "#{public_defs}\t#{path}" if public_defs >= 5
  end
' app/services/*.rb app/interactors/*.rb 2>/dev/null
```

Threshold: 5+ public methods on one service = WARNING.

## Controller bloat

```bash
find app/controllers -name '*.rb' \
  | xargs wc -l \
  | awk '$1 > 150 { print }'
```

Plus action count:

```bash
rg --no-heading -n '^\s*def\s+(index|show|new|create|edit|update|destroy|[a-z_]+)\s*(\(|$)' app/controllers \
  | awk -F: '{ counts[$1]++ } END { for (c in counts) if (counts[c] >= 7) print counts[c], c }' \
  | sort -rn
```

Threshold: > 150 lines OR 7+ actions = WARNING.

## Model bloat

```bash
find app/models -name '*.rb' \
  | xargs wc -l \
  | awk '$1 > 300 { print }'
```

Plus scope/association count per model:

```bash
rg --no-heading -n '^\s*(scope|has_many|has_one|belongs_to|has_and_belongs_to_many)\b' app/models \
  | awk -F: '{ counts[$1]++ } END { for (m in counts) if (counts[m] >= 10) print counts[m], m }' \
  | sort -rn
```

Threshold: > 300 lines OR 10+ scopes/associations = WARNING.
