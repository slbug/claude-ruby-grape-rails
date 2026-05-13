# Dead-Code Detection

Find constants, methods, and gems with zero usage outside the file that
defines them.

## Methods with zero callers

For each public method defined in `app/` outside controllers/jobs, grep for
calls to that method elsewhere. A method whose only reference is its own
definition is a dead-code candidate.

```bash
rg --no-heading -n '^\s*def\s+([a-z_][a-z_0-9?!]*)' app/ \
  --replace '$1' -o \
  | sort -u \
  > /tmp/method-names.txt

while read -r name; do
  count=$(rg --no-heading -c "\b${name}\b" app/ lib/ 2>/dev/null | wc -l)
  if [ "${count:-0}" -le 1 ]; then
    echo "candidate dead method: ${name}"
  fi
done < /tmp/method-names.txt
```

Reduce false positives by:

- Skipping protocol methods (`call`, `to_s`, `==`, `<=>`, `inspect`, …)
- Skipping Rails callbacks invoked by name (`before_action :name`)
- Skipping serializer/jbuilder method references (declared elsewhere)

Severity: INFO.

## Unused gems

```bash
ruby -r bundler -e '
  Bundler.load.specs.each do |spec|
    name = spec.name
    next if %w[rails bundler rake].include?(name)
    refs = `rg --count "require[\\s(]+[\\\"\\\x27]#{name}[\\\"\\\x27]" app/ lib/ config/ 2>/dev/null`.lines.size
    autoref = `rg --count "^\\s*#{name.split('-').map(&:capitalize).join('::')}" app/ lib/ 2>/dev/null`.lines.size
    puts "candidate unused gem: #{name}" if refs.zero? && autoref.zero?
  end
'
```

Manual confirmation required — Bundler autoload or initializer code may
reference the gem implicitly.

Severity: INFO.

## Duplicate config sources

```bash
rg --no-heading -n 'config\.([a-z_]+)\s*=' config/ \
  | awk -F'[:=]' '{ print $4 }' \
  | sort \
  | uniq -c \
  | awk '$1 > 1 { print }'
```

Settings appearing in more than one file (e.g., `config/application.rb` +
`config/environments/production.rb` + `config/initializers/*.rb`) are
candidates for consolidation.

Severity: INFO.
