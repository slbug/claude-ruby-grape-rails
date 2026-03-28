#!/usr/bin/env python3
"""Generate a deterministic hard trigger corpus from existing trigger files."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from lab.eval.trigger_scorer import PROMPT_BUCKETS, build_confusable_pairs, load_all_descriptions, load_trigger_file


TRIGGERS_DIR = Path(__file__).resolve().parent
OUTPUT = TRIGGERS_DIR / "_hard_corpus.json"


def _extract_prompt(item):
    if isinstance(item, str):
        return {"prompt": item}
    return dict(item)


def main() -> None:
    descriptions = load_all_descriptions()
    confusable = build_confusable_pairs(descriptions, limit=15)
    corpus = []

    for skill in sorted(descriptions):
        data = load_trigger_file(skill)
        if not data:
            continue
        for bucket in PROMPT_BUCKETS:
            for item in data.get(bucket, []):
                prompt = _extract_prompt(item)
                prompt["skill"] = skill
                prompt["bucket"] = bucket
                prompt["difficulty"] = "hard" if bucket.startswith("hard_") else "standard"
                corpus.append(prompt)

    payload = {
        "count": len(corpus),
        "confusable_pairs": confusable,
        "prompts": corpus,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(str(OUTPUT))


if __name__ == "__main__":
    main()
