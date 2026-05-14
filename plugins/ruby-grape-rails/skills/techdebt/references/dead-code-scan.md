# Dead-Code Detection

Find constants, methods, and gems with zero usage outside the file that
defines them.

## Methods with zero callers

Use [`debride`](https://github.com/seattlerb/debride) (MIT, seattlerb) —
Ruby static analyzer for uncalled methods, with Rails-aware knowledge
of callbacks, route helpers, and view bindings.

```bash
gem install debride
debride --rails --whitelist whitelist.txt .
```

`whitelist.txt` suppresses known-good false positives — one method
name per line, `/regexp/` delimiters for patterns. Seed migration
methods (`up`, `down`, `change`) and add protocol / dynamic-dispatch
methods as the scan flags them.

Companion gem `debride_rails_whitelist` builds an empirical whitelist
from production logs:

```bash
debride_rails_whitelist routes.txt log/production.log | sort -u > whitelist.txt
```

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
