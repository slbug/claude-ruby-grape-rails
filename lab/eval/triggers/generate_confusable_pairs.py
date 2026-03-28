#!/usr/bin/env python3
"""Write deterministic confusable-skill pairs from trigger overlap analysis."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from lab.eval.trigger_scorer import build_confusable_pairs, load_all_descriptions


OUTPUT = Path(__file__).resolve().parent / "_confusable_pairs.json"


def main() -> None:
    pairs = build_confusable_pairs(load_all_descriptions(), limit=15)
    payload = {"pairs": pairs, "count": len(pairs)}
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(str(OUTPUT))


if __name__ == "__main__":
    main()
