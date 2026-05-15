# Callback Sprawl Detection

Find Active Record models with excessive callbacks or cross-model callback
chains.

## Per-model callback count

```bash
rg --no-heading -n '^\s*(after_create|after_save|after_update|after_destroy|after_commit|before_save|before_create|before_update|before_destroy|before_validation|after_validation)\b' app/models | sort -t: -k1,1 | awk -F: '{ counts[$1]++ } END { for (m in counts) if (counts[m] > 5) print counts[m], m }' | sort -rn
```

Threshold: > 5 callbacks per model = WARNING.

## Cross-model callbacks

Callbacks that reach into another model are higher risk. Detect via:

```bash
rg --no-heading -n 'after_(commit|save|create).*do' app/models -A 6 | rg -n '\.(create|update|destroy|save)!?\s'
```

Each hit = candidate finding. Investigate whether the callback should be:

- Extracted into a service object
- Moved to a Sidekiq job (after_commit + enqueue)
- Replaced with an explicit caller-level call

## Order-dependent callbacks

Callbacks whose effect depends on declaration order are fragile:

```bash
rg --no-heading -n '^\s*(after|before)_' app/models -A 1 -B 1 | rg -B 1 -A 1 'self\.' 
```

Document any order-sensitive sequences in the output artifact.
