"""Deterministic checks for research/review output artifacts."""

from __future__ import annotations

import re


STATUS_RE = re.compile(r"^\d+\.\s+\[(VERIFIED|UNSUPPORTED|CONFLICT|WEAK|OPINION|REMOVED)\]", re.MULTILINE)
LOCAL_EVIDENCE_RE = re.compile(
    r"^\s*-\s*Evidence:\s+((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:rb|ru|rake|erb|haml|slim|yml|yaml|json|md|txt|sql|js|ts|tsx|jsx|py|sh):\d+)$",
    re.MULTILINE,
)
EXTERNAL_EVIDENCE_RE = re.compile(r"^\s*-\s*Evidence:\s+<?https?://[^ >]+>?\s+\[T[1-5]\]$", re.MULTILINE)


def _section(content: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^## {re.escape(heading)}\n(.*?)(?=^## |\Z)")
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def has_h1(content: str) -> tuple[bool, str]:
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
    body_without_sources = content.split("\n## Sources", 1)[0]
    count = len(re.findall(r"\[T[1-5]\]", body_without_sources))
    return count >= minimum, f"{count} inline tier marker(s) before Sources"


def has_research_decision_section(content: str) -> tuple[bool, str]:
    match = re.search(
        r"(?m)^## (Recommendation|Summary|Takeaways|Quick Facts|Risks|Migration path)$",
        content,
    )
    return bool(match), "Decision-oriented section present" if match else "Missing summary/recommendation section"


def has_review_title(content: str) -> tuple[bool, str]:
    match = re.search(r"(?m)^# Review: .+", content)
    return bool(match), "Review title present" if match else "Missing # Review: heading"


def has_review_verdict(content: str) -> tuple[bool, str]:
    match = re.search(r"(?m)^\*\*Verdict\*\*:\s+.+$", content)
    return bool(match), "Verdict present" if match else "Missing **Verdict** line"


def has_review_summary_table(content: str) -> tuple[bool, str]:
    body = _section(content, "Summary")
    match = re.search(r"\|\s*Severity\s*\|\s*Count\s*\|", body)
    return bool(match), "Severity summary table present" if match else "Missing severity summary table"


def has_review_file_refs(content: str, minimum: int = 1) -> tuple[bool, str]:
    matches = re.findall(r"(?m)^\*\*File\*\*:\s+`?.+:\d+`?$", content)
    return len(matches) >= minimum, f"{len(matches)} finding file ref(s) present"


def has_review_mandatory_table(content: str) -> tuple[bool, str]:
    match = re.search(
        r"(?m)^\|\s*#\s*\|\s*Finding\s*\|\s*Severity\s*\|\s*Reviewer\s*\|\s*File\s*\|\s*New\?\s*\|$",
        content,
    )
    return bool(match), "Mandatory finding table present" if match else "Missing mandatory finding table"


def review_has_no_task_lists(content: str) -> tuple[bool, str]:
    match = re.search(r"(?m)^\s*-\s+\[[ xX]\]\s+", content)
    return not bool(match), "No task lists present" if not match else "Review should not contain task lists"


def has_provenance_header(content: str) -> tuple[bool, str]:
    match = re.search(r"(?m)^# Provenance: .+", content)
    return bool(match), "Provenance heading present" if match else "Missing # Provenance: heading"


def has_provenance_artifact_pointer(content: str) -> tuple[bool, str]:
    match = re.search(r"(?m)^\*\*Artifact\*\*:\s+.+$", content)
    return bool(match), "Artifact pointer present" if match else "Missing **Artifact** pointer"


def has_provenance_summary_counts(content: str) -> tuple[bool, str]:
    patterns = (
        r"(?m)^\*\*Verified\*\*:\s+\d+$",
        r"(?m)^\*\*Unsupported\*\*:\s+\d+$",
        r"(?m)^\*\*Conflicts\*\*:\s+\d+$",
        r"(?m)^\*\*Weakly sourced\*\*:\s+\d+$",
    )
    missing = [pattern for pattern in patterns if not re.search(pattern, content)]
    return not missing, "Summary count lines present" if not missing else "Missing one or more summary count lines"


def has_provenance_tier_summary(content: str) -> tuple[bool, str]:
    match = re.search(r"(?m)^\*\*Source Tiers\*\*:\s+T1:\d+\s+T2:\d+\s+T3:\d+$", content)
    return bool(match), "Source tier summary present" if match else "Missing **Source Tiers** summary"


def has_provenance_claim_log(content: str) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    return bool(body), "Claim Log section present" if body else "Missing ## Claim Log section"


def has_provenance_claim_entries(content: str, minimum: int = 2) -> tuple[bool, str]:
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


def has_provenance_local_evidence(content: str) -> tuple[bool, str]:
    body = _section(content, "Claim Log")
    count = len(LOCAL_EVIDENCE_RE.findall(body))
    return count >= 1, f"{count} local-evidence line(s) present"
