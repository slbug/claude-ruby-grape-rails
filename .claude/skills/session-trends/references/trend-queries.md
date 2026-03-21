# Trend Queries Reference

Common questions you can answer with `/session-trends` data,
and how to interpret the results.

## Adoption & Usage

### "Is plugin adoption increasing?"

Look at `plugin_adoption_rate` across windows:

```
7d: 15% → 30d: 10% → all: 8%
```

**Interpretation**: If 7d > 30d > all, adoption is accelerating.
If 7d < all, recent sessions aren't using the plugin.

**Action**: If declining, check which session types (fingerprints)
are least likely to use plugin commands. These are automation targets.

### "Which commands are most used?"

Not directly in trends — run `/session-scan --list` and grep
`rb_commands_used` from metrics.jsonl:

```bash
grep -o '"rb_commands_used":\[[^]]*\]' .claude/session-metrics/metrics.jsonl | sort | uniq -c | sort -rn
```

### "Are sessions getting longer or shorter?"

Compare `duration_minutes` averages across windows. Longer sessions
may indicate harder problems or more friction.

## Friction Analysis

### "Which session types have most friction?"

Cross-reference fingerprint with friction in metrics.jsonl:

```bash
python3 -c "
import json
from collections import defaultdict
data = defaultdict(list)
for line in open('.claude/session-metrics/metrics.jsonl'):
    e = json.loads(line)
    data[e.get('fingerprint','?')].append(e.get('friction_score',0))
for k,v in sorted(data.items(), key=lambda x: -sum(x[1])/len(x[1])):
    print(f'{k}: avg={sum(v)/len(v):.2f} (n={len(v)})')
"
```

**Typical findings**: `bug-fix` and `refactoring` tend to have higher
friction than `exploration` or `maintenance`.

### "Are our fixes working?"

Compare friction trends over time. If friction is decreasing after
plugin improvements:

```
30d avg: 0.28 → 7d avg: 0.22 (improvement)
```

Also check: Tier 2 eligible percentage declining = fewer high-friction
sessions.

### "What are the biggest friction sources?"

Aggregate friction signals across sessions:

```bash
python3 -c "
import json
from collections import Counter
signals = Counter()
for line in open('.claude/session-metrics/metrics.jsonl'):
    e = json.loads(line)
    for k,v in e.get('friction_signals',{}).items():
        if isinstance(v,(int,float)) and v > 0:
            signals[k] += v
for k,v in signals.most_common():
    print(f'{k}: {v}')
"
```

## Plugin Opportunities

### "What commands are most frequently missed?"

Aggregate `could_use` from `plugin_signals`:

```bash
python3 -c "
import json
from collections import Counter
missed = Counter()
for line in open('.claude/session-metrics/metrics.jsonl'):
    e = json.loads(line)
    for cmd in e.get('plugin_signals',{}).get('could_use',[]):
        missed[cmd] += 1
for k,v in missed.most_common():
    print(f'/rb:{k}: missed in {v} sessions')
"
```

### "Is runtime tooling being utilized?"

Check `tidewave_pct` in tool profiles and `tidewave_available` vs
`tidewave_used` in plugin signals.

## File & Code Patterns

### "What files are hotspots?"

Aggregate `file_hotspots` across sessions to find frequently
touched files:

```bash
python3 -c "
import json
from collections import Counter
files = Counter()
for line in open('.claude/session-metrics/metrics.jsonl'):
    e = json.loads(line)
    for h in e.get('file_hotspots',[]):
        files[h['path']] += h.get('reads',0) + h.get('edits',0)
for k,v in files.most_common(20):
    print(f'{v:4d}  {k}')
"
```

### "What domains get the most work?"

Aggregate `file_categories`:

```bash
python3 -c "
import json
from collections import Counter
cats = Counter()
for line in open('.claude/session-metrics/metrics.jsonl'):
    e = json.loads(line)
    for k,v in e.get('file_categories',{}).items():
        cats[k] += v
for k,v in cats.most_common():
    print(f'{k}: {v} edits')
"
```

## Session Chaining

### "Is session chaining decreasing?"

Track `chain_length` distribution. High chaining = related sessions
not completing in one sitting.

Note: Session chaining detection requires the scan to identify
same-project sessions within 2 hours. Currently set to basic
detection — chain_length defaults to 1.

## Backfill Quality

### "How reliable are backfilled metrics?"

Backfilled sessions (`"backfilled": true`) have limited signals:

- `retry_loops`: always 0 (can't detect from v1 extracts)
- `approach_changes`: always 0
- `context_compactions`: always 0
- `tool_bigrams`: empty
- `file_hotspots`: empty

Use `backfilled_count` in trends to know what percentage of data
is lower-quality. For trend analysis, consider filtering to
non-backfilled sessions only.
