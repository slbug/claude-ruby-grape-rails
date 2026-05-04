"""Deterministic checks for research/review output artifacts."""


import re
import sys
from pathlib import Path

import yaml

from .frontmatter import extract_frontmatter_block


STATUS_RE = re.compile(r"^\d+\.\s+\[(VERIFIED|UNSUPPORTED|CONFLICT|WEAK)\]", re.MULTILINE)
LOCAL_EVIDENCE_RE = re.compile(
    r"^\s*-\s*Evidence:\s+((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+(?:\.(?:rb|ru|rake|erb|haml|slim|yml|yaml|json|md|txt|sql|js|ts|tsx|jsx|py|sh))?:\d+)$",
    re.MULTILINE,
)
EXTERNAL_EVIDENCE_RE = re.compile(r"^\s*-\s*Evidence:\s+<?https?://[^ >]+>?\s+\[T[1-5]\]$", re.MULTILINE)
PLACEHOLDER_EXTERNAL_RE = re.compile(
    r"https?://(?:example\.com\b|[^ >]+/(?:discussions|issues)/0+\b)",
    re.IGNORECASE,
)


def _normalize_newlines(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def _section(content: str, heading: str) -> str:
    content = _normalize_newlines(content)
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)")
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def has_h1(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    in_fence = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        return (
            (True, "Top-level heading present")
            if stripped.startswith("# ")
            else (False, "Missing top-level heading")
        )
    return False, "Missing top-level heading"


def has_research_metadata(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^(Last Updated|Date):\s+\d{4}-\d{2}-\d{2}$", content)
    return bool(match), "Date metadata present" if match else "Missing Date: or Last Updated: metadata"


def has_sources_section(content: str) -> tuple[bool, str]:
    body = _section(content, "Sources")
    return bool(body), "Sources section present" if body else "Missing ## Sources section"


def has_tiered_sources(content: str, minimum: int = 2) -> tuple[bool, str]:
    body = _section(content, "Sources")
    if not body:
        return False, "Missing ## Sources section"
    count = len(re.findall(r"\[T[1-5]\]", body))
    return count >= minimum, f"{count} tiered source marker(s) in Sources"


def has_inline_tier_markers(content: str, minimum: int = 2) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    sources_heading_match = re.search(r"(?m)^##\s+Sources\s*$", content)
    body_without_sources = content[: sources_heading_match.start()] if sources_heading_match else content
    count = len(re.findall(r"\[T[1-5]\]", body_without_sources))
    return count >= minimum, f"{count} inline tier marker(s) before Sources"


def has_research_decision_section(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(
        r"(?m)^## (Recommendation|Summary|Executive Summary|Takeaways|Quick Facts|Risks|Migration path)$",
        content,
    )
    return bool(match), "Decision-oriented section present" if match else "Missing summary/recommendation section"


def has_non_placeholder_sources(content: str) -> tuple[bool, str]:
    body = _section(content, "Sources")
    urls = re.findall(r"https?://[^ >]+", body)
    placeholders = [url for url in urls if PLACEHOLDER_EXTERNAL_RE.search(url)]
    return (
        (True, "No placeholder-like source URLs found")
        if not placeholders
        else (False, f"Placeholder-like source URLs found: {placeholders[:2]}")
    )


def has_review_title(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^# Review: .+", content)
    return bool(match), "Review title present" if match else "Missing # Review: heading"


def has_review_verdict(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    presence = re.search(r"(?m)^\*\*Verdict\*\*:\s+.+$", content)
    if not presence:
        return False, "Missing **Verdict** line"
    # Verdict text must come VERBATIM from canonical 4-set. Longest-first
    # alternation prevents `PASS` matching the prefix of `PASS WITH WARNINGS`.
    canonical = re.search(
        r"(?m)^\*\*Verdict\*\*:\s+(PASS WITH WARNINGS|REQUIRES CHANGES|BLOCKED|PASS)\s*$",
        content,
    )
    if not canonical:
        emitted = presence.group(0).split(":", 1)[1].strip()
        return False, (
            f"Verdict {emitted!r} not in canonical 4-set "
            "{PASS, PASS WITH WARNINGS, REQUIRES CHANGES, BLOCKED}"
        )
    return True, f"Verdict present: {canonical.group(1)}"


def has_review_summary_table(content: str) -> tuple[bool, str]:
    body = _section(content, "Summary")
    match = re.search(r"\|\s*Severity\s*\|\s*Count\s*\|", body)
    return bool(match), "Severity summary table present" if match else "Missing severity summary table"


def _table_data_rows(body: str) -> list[list[str]]:
    """Return every data row of the first markdown table found in body.

    Skips header + separator. Each row returned as a list of trimmed cells.
    No cell-count filtering — callers validate width per their contract,
    so malformed rows surface instead of being silently dropped.
    """
    lines = body.splitlines()
    sep_idx = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if "|" in s and re.match(r"^\|?\s*:?-{3,}", s):
            sep_idx = i
            break
    if sep_idx is None:
        return []
    rows: list[list[str]] = []
    for ln in lines[sep_idx + 1 :]:
        s = ln.strip()
        if not s.startswith("|"):
            break
        cells = [c.strip() for c in s.strip("|").split("|")]
        rows.append(cells)
    return rows


_RECOVERY_STATES = frozenset(
    {"artifact", "stub-replaced", "recovered-from-return", "stub-no-output"}
)
_CANONICAL_VERDICTS = frozenset(
    {"PASS", "PASS WITH WARNINGS", "REQUIRES CHANGES", "BLOCKED"}
)
_COVERAGE_FINDINGS_RE = re.compile(
    r"^\d+\s+BLOCKER\s*/\s*\d+\s+WARNING\s*/\s*\d+\s+SUGGESTION$"
)
_REVIEWERS_HEADER_RE = re.compile(r"(?m)^\*\*Reviewers\*\*:\s*(.+?)\s*$")


def has_review_reviewer_coverage(content: str) -> tuple[bool, str]:
    body = _section(content, "Reviewer Coverage")
    if not body:
        return False, "Missing ## Reviewer Coverage section"
    # Contract: `| <slug> | <recovery-state> | <findings-counts> |`
    # where recovery-state ∈ _RECOVERY_STATES and findings-counts matches
    # `{n} BLOCKER / {n} WARNING / {n} SUGGESTION`.
    rows = _table_data_rows(body)
    if not rows:
        return False, "Reviewer Coverage table empty"
    bad: list[str] = []
    for idx, row in enumerate(rows, start=1):
        if len(row) != 3:
            bad.append(f"row {idx}: {len(row)} cell(s); contract requires exactly 3 (slug | recovery state | findings counts)")
            continue
        slug, recovery, findings = row[0], row[1], row[2]
        if not slug:
            bad.append(f"row {idx}: missing reviewer slug")
            continue
        if recovery not in _RECOVERY_STATES:
            bad.append(f"{slug}: invalid recovery state {recovery!r}")
            continue
        if not _COVERAGE_FINDINGS_RE.match(findings):
            bad.append(f"{slug}: findings cell {findings!r} not in `{{n}} BLOCKER / {{n}} WARNING / {{n}} SUGGESTION` form")
    if bad:
        return False, "Reviewer Coverage row(s) violate contract: " + "; ".join(bad)
    return True, f"Reviewer Coverage section with {len(rows)} reviewer row(s)"


def has_review_reviewer_verdicts(content: str) -> tuple[bool, str]:
    body = _section(content, "Reviewer Verdicts")
    if not body:
        return False, "Missing ## Reviewer Verdicts section"
    # Contract: `| <slug> | <raw verdict> | <canonical> |`
    # where canonical ∈ _CANONICAL_VERDICTS.
    rows = _table_data_rows(body)
    if not rows:
        return False, "Reviewer Verdicts table empty"
    bad: list[str] = []
    for idx, row in enumerate(rows, start=1):
        if len(row) != 3:
            bad.append(f"row {idx}: {len(row)} cell(s); contract requires exactly 3 (slug | raw verdict | canonical)")
            continue
        slug, raw, canonical = row[0], row[1], row[2]
        if not slug:
            bad.append(f"row {idx}: missing reviewer slug")
            continue
        if not raw:
            bad.append(f"{slug}: raw verdict cell empty (playbook requires preserving the agent's verbatim verdict text)")
            continue
        if canonical not in _CANONICAL_VERDICTS:
            bad.append(f"{slug}: canonical verdict {canonical!r} not in 4-set {{PASS, PASS WITH WARNINGS, REQUIRES CHANGES, BLOCKED}}")
    if bad:
        return False, "Reviewer Verdicts row(s) violate contract: " + "; ".join(bad)
    return True, f"Reviewer Verdicts section with {len(rows)} verdict row(s)"


def has_review_reviewer_completeness(content: str) -> tuple[bool, str]:
    """Reconcile `**Reviewers**:` header list against Coverage + Verdicts row slugs.

    Header order + count must match Coverage rows exactly, and Verdicts
    rows exactly. Duplicate reviewer rows (e.g. two `ruby-reviewer` rows)
    fail — playbook requires exactly one Coverage/Verdicts row per
    spawned reviewer.
    """
    from collections import Counter

    content_norm = _normalize_newlines(content)
    header_match = _REVIEWERS_HEADER_RE.search(content_norm)
    if not header_match:
        return False, "Missing `**Reviewers**:` header line"
    header_slugs = [
        slug
        for slug in (s.strip() for s in header_match.group(1).split(","))
        if slug
    ]
    if not header_slugs:
        return False, "`**Reviewers**:` header has no slugs"
    header_counts = Counter(header_slugs)
    header_dups = sorted(slug for slug, n in header_counts.items() if n > 1)
    if header_dups:
        return False, f"`**Reviewers**:` header lists duplicate slug(s): {header_dups}"

    coverage_body = _section(content, "Reviewer Coverage")
    verdicts_body = _section(content, "Reviewer Verdicts")
    if not coverage_body:
        return False, "Missing ## Reviewer Coverage section (cannot reconcile reviewer set)"
    if not verdicts_body:
        return False, "Missing ## Reviewer Verdicts section (cannot reconcile reviewer set)"

    coverage_slugs = [row[0] for row in _table_data_rows(coverage_body) if row and row[0]]
    verdicts_slugs = [row[0] for row in _table_data_rows(verdicts_body) if row and row[0]]

    problems: list[str] = []

    def _diff(label: str, rows: list[str]) -> None:
        row_counts = Counter(rows)
        dups = sorted(slug for slug, n in row_counts.items() if n > 1)
        if dups:
            problems.append(f"{label} table has duplicate reviewer row(s): {dups}")
        missing = sorted(set(header_slugs) - set(rows))
        if missing:
            problems.append(f"{label} table missing reviewers: {missing}")
        extra = sorted(set(rows) - set(header_slugs))
        if extra:
            problems.append(f"{label} table has unexpected reviewers: {extra}")
        if not dups and not missing and not extra and rows != header_slugs:
            # Set membership matches but order/count differs — synthesis
            # reordered reviewers between header and table. Reject so the
            # consolidated artifact stays deterministic.
            problems.append(
                f"{label} table reviewer order {rows} does not match "
                f"`**Reviewers**:` header order {header_slugs}"
            )

    _diff("Coverage", coverage_slugs)
    _diff("Verdicts", verdicts_slugs)

    if problems:
        return False, "; ".join(problems)
    return True, f"`**Reviewers**:` header reconciled with {len(header_slugs)} Coverage + Verdicts row(s)"


def has_review_file_refs(content: str, minimum: int = 1) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    matches = re.findall(r"(?m)^\*\*File\*\*:\s+`?.+:\d+`?$", content)
    return len(matches) >= minimum, f"{len(matches)} finding file ref(s) present"


def has_review_mandatory_table(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(
        r"(?m)^\|\s*#\s*\|\s*Finding\s*\|\s*Severity\s*\|\s*Reviewer\s*\|\s*File\s*\|\s*New\?\s*\|$",
        content,
    )
    return bool(match), "Mandatory finding table present" if match else "Missing mandatory finding table"


def review_has_no_task_lists(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^\s*-\s+\[[ xX]\]\s+", content)
    return not bool(match), "No task lists present" if not match else "Review should not contain task lists"


def review_has_no_followup_sections(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^## (Next Steps|Action Items|Follow-up|Follow Up|Fix Plan)\s*$", content)
    return (
        (True, "No follow-up planning section present")
        if not match
        else (False, "Review should not contain follow-up planning sections")
    )


def has_provenance_header(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^# Provenance: .+", content)
    return bool(match), "Provenance heading present" if match else "Missing # Provenance: heading"


def has_provenance_artifact_pointer(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^\*\*Artifact\*\*:\s+.+$", content)
    return bool(match), "Artifact pointer present" if match else "Missing **Artifact** pointer"


def has_provenance_summary_counts(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    patterns = (
        r"(?m)^\*\*Verified\*\*:\s+\d+$",
        r"(?m)^\*\*Unsupported\*\*:\s+\d+$",
        r"(?m)^\*\*Conflicts\*\*:\s+\d+$",
        r"(?m)^\*\*Weakly sourced\*\*:\s+\d+$",
    )
    missing = [pattern for pattern in patterns if not re.search(pattern, content)]
    return not missing, "Summary count lines present" if not missing else "Missing one or more summary count lines"


def has_provenance_tier_summary(content: str) -> tuple[bool, str]:
    content = _normalize_newlines(content)
    match = re.search(r"(?m)^\*\*Source Tiers\*\*:\s+T1:\d+\s+T2:\d+\s+T3:\d+$", content)
    return bool(match), "Source tier summary present" if match else "Missing **Source Tiers** summary"


def has_provenance_claim_log(content: str) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    return bool(body), "Claim Log section present" if body else "Missing ## Claim Log section"


def has_provenance_claim_entries(content: str, minimum: int = 1) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    count = len(STATUS_RE.findall(body))
    return count >= minimum, f"{count} claim log entry(ies) present"


def has_provenance_required_fixes(content: str) -> tuple[bool, str]:
    body = _section(content, "Required Fixes")
    return bool(body), "Required Fixes section present" if body else "Missing ## Required Fixes section"


def has_provenance_external_evidence(content: str) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    count = len(EXTERNAL_EVIDENCE_RE.findall(body))
    return count >= 1, f"{count} external evidence line(s) present"


def provenance_external_evidence_is_non_placeholder(content: str) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    urls = re.findall(r"https?://[^ >]+", body)
    placeholders = [url for url in urls if PLACEHOLDER_EXTERNAL_RE.search(url)]
    return (
        (True, "No placeholder-like provenance URLs found")
        if not placeholders
        else (False, f"Placeholder-like provenance URLs found: {placeholders[:2]}")
    )


def has_provenance_local_evidence(content: str) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    count = len(LOCAL_EVIDENCE_RE.findall(body))
    return count >= 1, f"{count} local-evidence line(s) present"


def compute_trust_state(sidecar: Path) -> str:
    """Return one of {clean, weak, conflicted, missing}.

    Canonical YAML-frontmatter schema:

        ---
        claims:
          - id: c1
        sources:
          - kind: primary
            supports: [c1]
        conflicts: []
        ---

    Anything not matching this shape (no frontmatter, malformed YAML,
    unparsable, missing claims/sources lists) returns `missing` — callers
    treat that as "needs migration". YAML parse errors are surfaced via
    `yaml.YAMLError` to stderr (with line/column from the parser) so
    contributors can locate the malformed line, but the function still
    returns `missing` so the eval gate keeps a deterministic outcome.
    """
    if not sidecar.exists():
        return "missing"
    text = sidecar.read_text(encoding="utf-8", errors="replace")
    block = extract_frontmatter_block(text)
    if block is None:
        return "missing"
    try:
        meta = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = ""
        if mark is not None:
            # Frontmatter starts on line 2 of the file (after the opening
            # `---`). Adjust the parser's 0-based line number so the
            # diagnostic points at the real line in `sidecar`.
            location = f" at {sidecar}:{mark.line + 2}:{mark.column + 1}"
        sys.stderr.write(
            f"compute_trust_state: malformed YAML{location}: "
            f"{exc.__class__.__name__}\n"
        )
        return "missing"
    if not isinstance(meta, dict):
        return "missing"
    # Strict shape validation. All three top-level keys are required; any
    # off-spec frontmatter (missing key, wrong type, claim missing string
    # `id`, supports not a list of strings, kind absent or unknown) maps
    # to `missing` so malformed schemas surface as broken instead of being
    # graded `clean`, `weak`, or `conflicted`.
    if "claims" not in meta or "sources" not in meta or "conflicts" not in meta:
        return "missing"
    claims = meta.get("claims")
    sources = meta.get("sources")
    conflicts = meta.get("conflicts")

    if not isinstance(claims, list) or not claims:
        return "missing"
    if not isinstance(sources, list) or not sources:
        return "missing"
    if not all(isinstance(c, dict) and isinstance(c.get("id"), str) for c in claims):
        return "missing"
    if not all(isinstance(s, dict) for s in sources):
        return "missing"
    if not isinstance(conflicts, list):
        return "missing"
    allowed_kinds = {"primary", "secondary", "tool-output"}
    for s in sources:
        kind = s.get("kind")
        if kind not in allowed_kinds:
            return "missing"
        if "supports" not in s:
            return "missing"
        supports = s.get("supports")
        if not isinstance(supports, list) or not supports:
            return "missing"
        if not all(isinstance(cid, str) for cid in supports):
            return "missing"

    if conflicts:
        return "conflicted"

    support_counts: dict[str, int] = {c["id"]: 0 for c in claims}
    for s in sources:
        # Dedupe within a single source so `supports: [c1, c1]` does not
        # inflate the count toward the "≥2 independent sources" rule.
        for cid in set(s.get("supports") or []):
            if cid in support_counts:
                support_counts[cid] += 1
    all_tool_only = all(s.get("kind") == "tool-output" for s in sources)
    if all_tool_only or any(count < 2 for count in support_counts.values()):
        return "weak"
    return "clean"
