#!/usr/bin/env python3
"""Epistemic baseline presence gate.

Used by ``scripts/generate-iron-law-outputs.sh`` before regenerating
``inject-iron-laws.sh``. Blocks regeneration only when the active
provider's epistemic baseline is missing — without a baseline, any
later ``make eval-epistemic`` run has no reference point to measure
delta against.

Hash-mismatch between the baseline's stored ``system_prompt_hash`` and
the current injector is the NORMAL state during iteration (edit source
→ regen → maybe edit again → regen again). Baseline is a fixed
reference captured once (e.g. main-branch state); subsequent regens
produce new current states and the delta between each and the baseline
is what we measure. Blocking on hash mismatch would block every
iteration after the first — wrong.

Workflow:

1. Capture baseline against whatever state the user wants as their
   reference (typically released/main). Hash stored in JSON.
2. Iterate: edit source, regen, edit, regen, measure. Gate passes on
   every regen as long as baseline exists.
3. ``make eval-epistemic`` compares current injector output against
   baseline and reports delta.

Baseline correctness (was it captured against the intended reference
state?) is the contributor's responsibility — this gate cannot tell
intentional from accidental baseline content.

Active provider resolved via ``RUBY_PLUGIN_EVAL_PROVIDER`` env
(fallback ``ollama``). Gate only checks the active provider's
baseline — if measuring multiple providers, ensure each has a
baseline before its measurement (the eval suite itself errors on
missing baseline).

Exit codes:

- 0: baseline exists (or opt-out via ``EPISTEMIC_BASELINE_CHECK=0``).
- 2: baseline missing for active provider.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINES_BASE = REPO_ROOT / "lab" / "eval" / "baselines" / "epistemic"


def main() -> int:
    if os.environ.get("EPISTEMIC_BASELINE_CHECK") == "0":
        return 0

    # Reuse the same provider resolution as the eval tooling so this gate
    # stays in lockstep with what the contributor is actually measuring.
    sys.path.insert(0, str(REPO_ROOT))
    from lab.eval import results_dir as rd

    rd.set_active_provider(None)  # reads RUBY_PLUGIN_EVAL_PROVIDER
    namespace = rd.get_active_cache_namespace()
    baseline_path = BASELINES_BASE / namespace / "pre-posture.json"

    provider = rd.get_active_provider()

    if not baseline_path.is_file():
        print(
            f"ERROR: Epistemic baseline missing for provider={provider} "
            f"(namespace={namespace}).",
            file=sys.stderr,
        )
        print(f"  Expected at: {baseline_path}", file=sys.stderr)
        print(
            "  Regeneration without a baseline means `make eval-epistemic` "
            "has no reference point to measure delta against. Capture "
            "baseline first:",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(
            f"    python3 -m lab.eval.epistemic_suite --baseline-only "
            f"--provider {provider} --workers 4 --summary --pretty",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(
            "  Or skip the gate if no epistemic measurement is planned:",
            file=sys.stderr,
        )
        print(
            "    EPISTEMIC_BASELINE_CHECK=0 bash scripts/generate-iron-law-outputs.sh all",
            file=sys.stderr,
        )
        return 2

    # Baseline exists. Gate passes — hash-mismatch is the expected state
    # during iteration (edit/regen/edit/regen/measure). Baseline stays as
    # the fixed reference point; regen produces new current states; delta
    # is measured between them.
    #
    # Display baseline freshness info so the contributor can judge whether
    # this baseline is from the current PR (fresh) or left over from a
    # previous PR (stale after main has moved). The gate cannot decide
    # staleness automatically without git integration, so we surface the
    # data and trust the contributor to re-capture when needed.
    import json

    try:
        baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        baseline_data = {}
    baseline_hash = str(baseline_data.get("system_prompt_hash", "unknown"))
    baseline_generated_at = str(baseline_data.get("generated_at", "unknown"))
    print(
        f"NOTICE: Using existing baseline for provider={provider} "
        f"(namespace={namespace}):",
        file=sys.stderr,
    )
    print(f"  path:             {baseline_path}", file=sys.stderr)
    print(f"  generated_at:     {baseline_generated_at}", file=sys.stderr)
    print(f"  baseline hash:    {baseline_hash}", file=sys.stderr)
    print(
        "  If this baseline is from a previous PR and main has moved since, "
        "re-capture it before regenerating to keep the delta measurement "
        "scoped to THIS PR's changes. To re-capture:",
        file=sys.stderr,
    )
    print(f"    rm {baseline_path}", file=sys.stderr)
    print(
        f"    python3 -m lab.eval.epistemic_suite --baseline-only "
        f"--provider {provider} --workers 4 --summary --pretty",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
