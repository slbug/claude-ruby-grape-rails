"""Deterministic checks for research/review output artifacts."""


import re
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
    match = re.search(r"(?m)^\*\*Verdict\*\*:\s+.+$", content)
    return bool(match), "Verdict present" if match else "Missing **Verdict** line"


def has_review_summary_table(content: str) -> tuple[bool, str]:
    body = _section(content, "Summary")
    match = re.search(r"\|\s*Severity\s*\|\s*Count\s*\|", body)
    return bool(match), "Severity summary table present" if match else "Missing severity summary table"


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
    treat that as "needs migration".
    """
    if not sidecar.exists():
        return "missing"
    text = sidecar.read_text(encoding="utf-8", errors="replace")
    block = extract_frontmatter_block(text)
    if block is None:
        return "missing"
    try:
        meta = yaml.safe_load(block)
    except yaml.YAMLError:
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
