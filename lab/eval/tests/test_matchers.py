from __future__ import annotations

import unittest

from lab.eval import matchers


SAMPLE = """---
name: rb:sample
description: Use for Ruby verification and review workflows with Rails context.
tools:
  - Read
---
# Sample

## Iron Laws

1. Never skip tests.

## Workflow

- Read `references/example.md`
- Run `bundle exec rubocop`
"""


class MatcherTests(unittest.TestCase):
    def test_parse_frontmatter_scalars_and_lists(self) -> None:
        data = matchers.parse_frontmatter(SAMPLE)
        self.assertEqual(data["name"], "rb:sample")
        self.assertEqual(data["tools"], ["Read"])

    def test_has_iron_laws(self) -> None:
        passed, _ = matchers.has_iron_laws(SAMPLE, min_count=1)
        self.assertTrue(passed)

    def test_description_structure(self) -> None:
        passed, _ = matchers.description_structure(SAMPLE)
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main()
