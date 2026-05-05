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
TRIAGE_SKILL = REPO_ROOT / "plugins/ruby-grape-rails/skills/triage/SKILL.md"

_IRON_LAW_RE = re.compile(r"Iron Law\s+\d+", re.IGNORECASE)
_PHASE_HEADING_RE = re.compile(r"^##+\s+(Phase\s+\d+|Deferred Findings|Pre-existing Issues)", re.IGNORECASE)
_TASK_LINE_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+\[P\d+-T\d+\]")
_TASK_ANNOTATION_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+\[P\d+-T\d+\]\[([^\]]+)\]")
# Canonical Set A from `plan/references/planning-workflow.md` § "Plan Generation".
# `/rb:work` parser routes on this enum; off-list labels are descriptive narrative
# (e.g. `[ruby]`, `[ar]`, `[grape]`) and break the work workflow.
_CANONICAL_PLAN_ANNOTATIONS = frozenset(
    {"direct", "active record", "hotwire", "sidekiq", "concurrency", "security", "test"}
)


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

    def test_task_annotations_use_canonical_set_a(self) -> None:
        """Every `- [ ] [Pn-Tm][annotation] ...` task line MUST use a Set A annotation.

        Set A per `plan/references/planning-workflow.md` § "Plan
        Generation": `direct`, `active record`, `hotwire`, `sidekiq`,
        `concurrency`, `security`, `test`. Off-list labels (`ruby`,
        `testing`, `grape`, `ar`, `sequel`, `perf`) are descriptive
        narrative or subagent type names, not plan-task annotations,
        and break `/rb:work` parsing.
        """
        text = TRIAGE_PLAN_TEMPLATE.read_text(encoding="utf-8")
        bad: list[str] = []
        for line in text.splitlines():
            m = _TASK_ANNOTATION_RE.match(line)
            if not m:
                continue
            annotation = m.group(1)
            if annotation not in _CANONICAL_PLAN_ANNOTATIONS:
                bad.append(f"non-Set-A annotation [{annotation}] in: {line.strip()!r}")
        self.assertFalse(
            bad,
            "Plan-task annotations MUST be from canonical Set A; off-list labels "
            "break `/rb:work`. Drifted lines: " + "; ".join(bad),
        )


_FOR_PLAN_HEADING_RE = re.compile(r"^##\s+Output Format\s*$")
_FENCE_OPEN_RE = re.compile(r"^(`{3,}|~{3,})")
_BARE_TASK_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+(?!\[P\d+-T\d+\]\[)")


class TriageSkillEmbeddedExampleDriftTests(unittest.TestCase):
    """Drift gates for canonical examples embedded INSIDE `triage/SKILL.md`.

    `triage-plan-template.md` already has its own gates; this class
    covers the SKILL body's `### For Plan` example block + the
    Smart Grouping pseudocode, both of which load directly into agent
    context and can teach drifted contracts even when the template
    file is correct.
    """

    def test_for_plan_example_uses_canonical_task_format(self) -> None:
        """`- [ ] ...` lines under `### For Plan` MUST use `[Pn-Tm][annotation]`.

        Bare checkboxes in the example would teach `/rb:triage` to
        emit plan files unparseable by `/rb:work`. Pin the canonical
        task shape inside the SKILL body's worked example.
        """
        text = TRIAGE_SKILL.read_text(encoding="utf-8")
        in_section = False
        in_fence = False
        bad: list[str] = []
        for line in text.splitlines():
            if not in_section:
                if _FOR_PLAN_HEADING_RE.match(line):
                    in_section = True
                continue
            # Stop at the next `### `/`## ` heading outside fenced blocks.
            if not in_fence and (line.startswith("### ") or line.startswith("## ")):
                break
            if _FENCE_OPEN_RE.match(line.lstrip()):
                in_fence = not in_fence
                continue
            if not in_fence:
                continue
            if _BARE_TASK_RE.match(line) and not line.lstrip().startswith("- [ ] [P"):
                bad.append(line.strip())
        self.assertFalse(
            bad,
            "`### For Plan` example task lines MUST use `[Pn-Tm][annotation]` "
            "format. Drifted lines: " + "; ".join(bad),
        )

    def test_skill_pseudocode_no_rule_id_grouping(self) -> None:
        """Step 3 contract: review artifacts have no stable `rule_id`.

        Embedded pseudocode (Smart Grouping etc.) MUST NOT key
        groupings on `rule_id` — that would teach the synthesizer to
        invent IDs the artifact does not provide. The Step 3 prose
        legitimately mentions `rule_id` to prohibit it; this gate
        targets the symbol-access pattern (`f[:rule_id]`,
        `finding[:rule_id]`, `:rule_id` in `group_by`) inside
        executable-looking pseudocode, not bare prose mentions.
        """
        text = TRIAGE_SKILL.read_text(encoding="utf-8")
        bad_patterns = [r"\[\s*:rule_id\s*\]", r"group_by[^\n]*rule_id", r"f\.rule_id\b"]
        bad: list[str] = []
        for pat in bad_patterns:
            for m in re.finditer(pat, text):
                bad.append(f"{pat!r} matched: {m.group(0)!r}")
        self.assertFalse(
            bad,
            "Pseudocode in triage SKILL.md MUST NOT key groupings on rule_id "
            "(no stable id in review artifacts). Drifted patterns: " + "; ".join(bad),
        )

    def test_skill_no_pseudocode_implementation_blocks(self) -> None:
        """SKILL bodies are agent instructions, not implementation pseudocode.

        Triage routing happens via agent reasoning over the review
        artifact. Embedded ` ```ruby ` / ` ```yaml ` blocks describing
        in-process algorithms or fabricated schemas (e.g.,
        `compound_analysis`) teach the wrong execution model.
        Allowed fenced blocks: shell command examples (` ```text `,
        ` ``` ` plain) under Integration / Edge Cases / Commands.
        """
        text = TRIAGE_SKILL.read_text(encoding="utf-8")
        # Forbid `def `, `findings.group_by`, fabricated YAML schemas.
        forbidden = [
            (r"^\s*def\s+\w+\(", "Ruby `def` method block"),
            (r"compound_analysis\b", "fabricated `compound_analysis` schema"),
            (r"potential_root_cause\s*:", "fabricated `potential_root_cause` schema"),
        ]
        bad: list[str] = []
        for pat, label in forbidden:
            if re.search(pat, text, re.MULTILINE):
                bad.append(label)
        self.assertFalse(
            bad,
            "SKILL.md is agent instructions, not pseudocode. Found: " + "; ".join(bad),
        )


if __name__ == "__main__":
    unittest.main()
