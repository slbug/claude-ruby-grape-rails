# Architecture Decision

We're adding a cart feature. I can either:

1. Store cart state in the session cookie (simple, but limited size and
   tied to the browser).
2. Persist `Cart` as an ActiveRecord model (more code, more DB load, but
   supports multi-device).

Our current traffic is ~50 requests/sec. No strong signal either way
from product. I need a concrete recommendation with reasoning, picked as
a single option. No "it depends" — pick one and justify.

<!-- Ground truth: genuinely ambiguous tradeoff, model would naturally
hedge ("it depends", "potentially", "might"). Posture says use direct
language for HIGH-confidence findings — and commit to a recommendation
when asked for one. Measured via hedge_cascade_rate — we want it LOW
despite the ambiguity because the user explicitly asked for a single
pick. -->
