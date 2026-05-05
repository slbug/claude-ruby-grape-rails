"""Drift gates for shipped templates / canonical examples.

Validators in `output_checks.py` cover consolidated review artifacts.
Templates the plugin ships as canonical examples (e.g.
`triage-plan-template.md`) load directly into agent context, so a
drifted example can teach incorrect bucket / phase mapping even when
all artifact-scoring fixtures pass. These tests pin the contracts the
templates MUST embody.
"""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TRIAGE_PLAN_TEMPLATE = (
    REPO_ROOT
    / "plugins/ruby-grape-rails/skills/triage/references/triage-plan-template.md"
)

_IRON_LAW_RE = re.compile(r"Iron Law\s+\d+", re.IGNORECASE)
_PHASE_HEADING_RE = re.compile(r"^##+\s+(Phase\s+\d+|Deferred Findings|Pre-existing Issues)", re.IGNORECASE)
_TASK_LINE_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+\[P\d+-T\d+\]")


def _walk_phase_sections(text: str):
    """Yield (heading, lines) per top-level `## Phase N` / Deferred / Pre-existing section.

    Walks the rendered template body inside the outer 4-backtick fence
    used by `triage-plan-template.md`. Each tuple holds the heading
    text and the body lines until the next matching heading.
    """
    current_heading: str | None = None
    current_body: list[str] = []
    for line in text.splitlines():
        m = _PHASE_HEADING_RE.match(line)
        if m:
            if current_heading is not None:
                yield current_heading, current_body
            current_heading = line.strip("# ").strip()
            current_body = []
            continue
        if line.startswith("## ") and current_heading is not None:
            yield current_heading, current_body
            current_heading = None
            current_body = []
            continue
        if current_heading is not None:
            current_body.append(line)
    if current_heading is not None:
        yield current_heading, current_body


class TriagePlanTemplateDriftTests(unittest.TestCase):
    def test_iron_law_refs_only_in_blockers_phase(self) -> None:
        """`Iron Law N` MUST NOT appear in non-BLOCKER task lines.

        Per `triage-patterns.md` § "Always Fix": ALL Iron Law
        violations are non-negotiable BLOCKERs. A canonical task
        example referencing `Iron Law N` under `## Phase 2: Warnings`
        / `## Deferred Findings` would teach the agent to defer or
        downgrade an Iron Law violation. The `## Pre-existing Issues
        (informational)` section is exempt — pre-existing findings
        legitimately retain their Iron Law label while being routed
        out of any Phase.
        """
        text = TRIAGE_PLAN_TEMPLATE.read_text(encoding="utf-8")
        bad: list[str] = []
        for heading, body in _walk_phase_sections(text):
            heading_l = heading.lower()
            if heading_l.startswith("phase 1") or "pre-existing" in heading_l:
                continue
            for line in body:
                if not _TASK_LINE_RE.match(line):
                    continue
                if _IRON_LAW_RE.search(line):
                    bad.append(f"{heading!r} contains Iron Law task: {line.strip()!r}")
        self.assertFalse(
            bad,
            "Iron Law violations are BLOCKER per triage-patterns; canonical "
            "examples MUST NOT place them in non-BLOCKER phases. "
            "Drifted lines: " + "; ".join(bad),
        )

    def test_phase_2_uses_canonical_warning_pseudo_bucket(self) -> None:
        """`## Phase 2: Warnings (selected)` heading MUST stay canonical.

        Drift guard: a rename to `## Phase 2: Recommendations` or
        similar would split the bucket vocabulary across the template
        and the review-playbook contract.
        """
        text = TRIAGE_PLAN_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("## Phase 2: Warnings (selected)", text)


if __name__ == "__main__":
    unittest.main()
