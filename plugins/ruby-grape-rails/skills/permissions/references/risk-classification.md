# Risk Classification Rules

Comprehensive command classification for the Ruby permission analyzer.

## Classification Algorithm

1. Extract the command group from the session evidence.
2. Check RED rules first.
3. Then check GREEN rules.
4. Default to YELLOW if the command writes local state but is normally recoverable.

## GREEN — Safe to Recommend

Read-only commands and ordinary verification commands that should not mutate
project state.

### Universal Safe Commands

| Pattern | Rationale |
|---------|-----------|
| `ls *`, `cat *`, `head *`, `tail *`, `wc *` | Read-only inspection |
| `find *`, `grep *`, `rg *`, `ag *` | Read-only search |
| `jq *`, `sed *`, `awk *`, `sort *`, `cut *`, `uniq *` | Read-only transformation |
| `pwd`, `date`, `whoami`, `which *`, `file *` | Information only |
| `git status *`, `git log *`, `git diff *`, `git show *` | Read-only git inspection |

### Ruby Verification Commands

| Pattern | Rationale |
|---------|-----------|
| `bundle exec rspec *` | Read-only test execution |
| `bundle exec rails test *` | Read-only test execution |
| `bundle exec rake test *` | Read-only test execution |
| `bundle exec standardrb *` | Read-only lint / formatting check |
| `bundle exec rubocop *` | Read-only lint / static analysis |
| `bundle exec brakeman *` | Read-only security scan |
| `bundle exec pronto *` | Read-only diff-scoped review |
| `bundle exec rails zeitwerk:check *` | Read-only autoload verification |
| `bundle exec rails routes *` | Read-only route listing |
| `bundle exec rails runner *` | Usually read-only, but review the actual command first |

## YELLOW — Recommend with Caution

Commands that change local state or publish local work, but are generally
recoverable and often necessary during normal development.

### Ruby / Project Write Operations

| Pattern | Note |
|---------|------|
| `bundle install *` | Changes local dependencies |
| `bundle exec rails db:migrate *` | Database mutation, but normally reversible |
| `bundle exec rake db:migrate *` | Database mutation, but normally reversible |
| `bundle exec rails db:rollback *` | Database mutation |
| `bundle exec rails generate *` | Generates files |
| `bundle exec rake *` | Mixed bag; inspect the specific task |
| `lefthook run *` | Project wrapper command; usually safe but executes configured steps |

### Git / Filesystem Write Operations

| Pattern | Note |
|---------|------|
| `git add *`, `git commit *` | Local VCS mutation |
| `git push *` | Remote mutation without force |
| `mkdir *`, `touch *`, `cp *`, `mv *` | Local filesystem writes |
| `make *`, `just *` | Wrapper commands; inspect the target first |

## RED — Never Auto-Allow

Commands that can destroy data, rewrite history, escalate privileges, or affect
systems beyond ordinary project-local development.

| Pattern | Risk |
|---------|------|
| `rm *`, `rm -rf *`, `rmdir *` | File deletion |
| `sudo *`, `su *` | Privilege escalation |
| `kill *`, `killall *`, `pkill *` | Process termination |
| `git reset --hard *`, `git clean -f *` | Discards local work |
| `git push --force *`, `git push -f *` | Rewrites remote history |
| `bundle exec rails db:drop *`, `bundle exec rails db:reset *` | Destructive DB operations |
| `bundle exec rake db:drop *`, `bundle exec rake db:reset *` | Destructive DB operations |
| `curl * \| sh`, `curl * \| bash`, `wget * \| sh` | Remote code execution |
| `chmod 777 *`, `chown *` | Dangerous permissions / ownership changes |

## Edge Cases

- Compound commands inherit the highest-risk segment.
- Wrapper commands (`make`, `just`, `bundle exec rake`) are not automatically
  GREEN; inspect the concrete target.
- If a command group is ambiguous, classify it YELLOW and keep manual approval
  unless the user explicitly wants to broaden trust.
