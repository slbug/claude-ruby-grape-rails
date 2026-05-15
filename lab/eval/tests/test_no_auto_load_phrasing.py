"""Unit test: README, tutorial-content, and CLAUDE.md contain no stale
"auto-loads based on file context" promise.

`paths:` frontmatter on plugin SKILL.md is empirically non-functional
at plugin scope. Any doc text that promises automatic file-context-driven
skill loading is wrong and must be removed.
"""

import re
import unittest

from lab.eval.matchers import PLUGIN_ROOT, PROJECT_ROOT


def _scan_targets() -> list:
    targets = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CLAUDE.md",
    ]
    targets += sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
    targets += sorted((PLUGIN_ROOT / "skills").glob("*/references/*.md"))
    return targets


SCAN_FILES = _scan_targets()

# Stale phrasings that claim plugin SKILL.md `paths:` triggers auto-load.
# The plugin-scope `paths:` mechanism is empirically non-functional —
# any doc text that promises automatic file-context-driven skill loading
# is wrong. Patterns scoped narrowly to avoid false positives on the
# functional `.claude/rules/*.md` `paths:` mechanism (which IS noted as
# distinct in surviving prose).
STALE_PATTERNS = [
    re.compile(
        r"auto-loads? (?:the right )?(?:domain knowledge )?based on (?:what )?files? you'?re editing",
        re.IGNORECASE,
    ),
    re.compile(r"auto-load.{0,40}file context", re.IGNORECASE),
    re.compile(r"\bauto-loaded references\b", re.IGNORECASE),
    re.compile(r"^\s*\|.*\|\s*Plugin loads\b", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"\bauto-loaded for files? under\b",
        re.IGNORECASE,
    ),
]


class NoAutoLoadPhrasingTests(unittest.TestCase):
    def test_no_stale_auto_load_phrasing(self) -> None:
        violations: list[str] = []
        for path in SCAN_FILES:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for pat in STALE_PATTERNS:
                for m in pat.finditer(text):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}: {m.group(0)!r}")
        self.assertEqual(
            violations,
            [],
            "Stale 'auto-load' phrasing remains:\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
