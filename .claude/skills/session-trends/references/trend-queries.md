# Trend Queries Reference

Common questions you can answer from `metrics.jsonl`, plus the caveats that
keep those answers honest.

## First Rule

Before interpreting a trend, ask:

1. am I mixing providers?
2. is the sample size large enough?
3. is this transcript-derived metric being treated too strongly?

If the ledger has fewer than 10 sessions, treat the report as an early snapshot
instead of a genuine time-series trend.

Also check:

- `time_series_signal`
- `distinct_dates`

If `time_series_signal` is `none`, do not narrate `7d` vs `30d` vs `all` as if
they show a meaningful trend.

## Adoption and Usage

### "Is plugin adoption increasing?"

Look at `plugin_adoption_rate` across windows, preferably with a provider
filter.

This rate now reflects only shipped plugin commands:

- `/rb:*`
- `/ruby-grape-rails:*`

Contributor-only analyzer commands like `/docs-check` and `/session-scan` are
intentionally ignored.

Interpretation:

- `7d > 30d > all` suggests recent adoption growth
- `7d < all` suggests recent usage is lagging

Action:

- inspect which fingerprints have low command usage
- confirm with manual transcript review before making product claims

### "Which commands are most used?"

Use a quick extraction from the ledger:

```bash
rg -o '"rb_commands_used":\\[[^]]*\\]' .claude/session-metrics/metrics.jsonl | sort | uniq -c | sort -rn
```

## Friction

### "Which session types look hardest?"

Use a grouped average:

```bash
python3 -c "
import json
from collections import defaultdict
data = defaultdict(list)
for line in open('.claude/session-metrics/metrics.jsonl'):
    entry = json.loads(line)
    data[entry.get('fingerprint', 'unknown')].append(entry.get('friction_score', 0))
for key, values in sorted(data.items(), key=lambda item: -sum(item[1]) / len(item[1])):
    print(f'{key}: avg={sum(values)/len(values):.2f} (n={len(values)})')
"
```

Use this to choose transcripts for review, not to declare one workflow
objectively worse.

### "Are our fixes working?"

Trend decreases in friction or Tier 2 eligibility are encouraging, but they are
still observational. Corroborate with:

- `lab/eval`
- docs-check results
- manual transcript review

## Plugin Opportunities

### "What commands are most frequently missed?"

Aggregate `could_use`:

```bash
python3 -c "
import json
from collections import Counter
missed = Counter()
for line in open('.claude/session-metrics/metrics.jsonl'):
    entry = json.loads(line)
    for cmd in entry.get('plugin_signals', {}).get('could_use', []):
        missed[cmd] += 1
for key, value in missed.most_common():
    print(f'/rb:{key}: missed in {value} sessions')
"
```

Treat this as a lead list for transcript inspection, not an automatic roadmap.

## Tooling and Domains

### "Is runtime tooling being used?"

Check `tidewave_pct` and the corresponding plugin signals, but remember this is
still transcript-derived tool detection.

### "What files are hotspots?"

Aggregate `file_hotspots`:

```bash
python3 -c "
import json
from collections import Counter
files = Counter()
for line in open('.claude/session-metrics/metrics.jsonl'):
    entry = json.loads(line)
    for hotspot in entry.get('file_hotspots', []):
        files[hotspot['path']] += hotspot.get('reads', 0) + hotspot.get('edits', 0)
for key, value in files.most_common(20):
    print(f'{value:4d}  {key}')
"
```

## Session Chaining

Do not use `session_chain` for real conclusions yet.

Current ledger entries only record that chaining is not implemented. If chaining
becomes important, it needs a real linker instead of placeholder values.
