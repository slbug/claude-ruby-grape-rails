# Trend Queries Reference

## Audience: Agents, Not Humans

Imperative-only.

## First Rule

Before interpreting a trend, verify:

| Check | Action |
|---|---|
| mixing providers? | segment with `--provider` |
| sample size large enough? | < 10 sessions → early snapshot, not trend |
| transcript-derived metric treated too strongly? | downgrade confidence |

`time_series_signal == none` → do NOT narrate `7d` vs `30d` vs `all` as
meaningful trend.

Also check `distinct_dates`.

## Adoption and Usage

### "Is plugin adoption increasing?"

Look at `plugin_adoption_rate` across windows, preferably with provider
filter.

Rate reflects only shipped plugin commands:

- `/rb:*`
- `/ruby-grape-rails:*`

Contributor-only analyzer commands (`/docs-check`, `/session-scan`) are
intentionally ignored.

| Pattern | Interpretation |
|---|---|
| `7d > 30d > all` | recent adoption growth |
| `7d < all` | recent usage lagging |

Action: inspect which fingerprints have low command usage. Confirm with
manual transcript review before making product claims.

### "Which commands are most used?"

Quick extraction from ledger:

```bash
rg -o '"rb_commands_used":\[[^]]*\]' .claude/session-metrics/metrics.jsonl | sort | uniq -c | sort -rn
```

## Friction

### "Which session types look hardest?"

Grouped average:

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

Use to choose transcripts for review, NOT to declare one workflow
objectively worse.

### "Are our fixes working?"

Trend decreases in friction or Tier 2 eligibility are encouraging but
observational. Corroborate with:

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

Lead list for transcript inspection, NOT automatic roadmap.

## Tooling and Domains

### "Is runtime tooling being used?"

Check `tidewave_pct` + corresponding plugin signals. Transcript-derived
tool detection — confidence stays observational.

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

Do NOT use `session_chain` for real conclusions yet.

Current ledger entries only record that chaining is not implemented.
Real linker required when chaining matters — placeholder values are not
a substitute.
