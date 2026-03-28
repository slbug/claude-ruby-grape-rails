from __future__ import annotations

import unittest

from lab.eval import agent_matchers
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

    def test_parse_frontmatter_inline_comma_lists(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit, NotebookEdit
skills: testing, review
---
"""
        data = matchers.parse_frontmatter(content)
        self.assertEqual(data["tools"], ["Read", "Grep", "Glob", "Bash"])
        self.assertEqual(data["disallowedTools"], ["Write", "Edit", "NotebookEdit"])
        self.assertEqual(data["skills"], ["testing", "review"])

    def test_parse_frontmatter_empty_list_like_keys_return_lists(self) -> None:
        content = """---
name: sample-agent
tools:
disallowedTools:
skills:
---
"""
        data = matchers.parse_frontmatter(content)
        self.assertEqual(data["tools"], [])
        self.assertEqual(data["disallowedTools"], [])
        self.assertEqual(data["skills"], [])

    def test_has_iron_laws(self) -> None:
        passed, _ = matchers.has_iron_laws(SAMPLE, min_count=1)
        self.assertTrue(passed)

    def test_description_structure(self) -> None:
        passed, _ = matchers.description_structure(SAMPLE)
        self.assertTrue(passed)

    def test_no_dangerous_patterns_catches_rm_rf_root(self) -> None:
        passed, evidence = matchers.no_dangerous_patterns("rm -rf /")
        self.assertFalse(passed)
        self.assertIn("rm", evidence)

    def test_read_only_tools_coherent_requires_write_blocks_for_read_only_agents(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools:
  - Read
  - Grep
disallowedTools:
  - Write
  - Edit
  - NotebookEdit
---
"""
        passed, _ = agent_matchers.read_only_tools_coherent(content)
        self.assertTrue(passed)

    def test_read_only_tools_coherent_fails_when_read_only_agent_lacks_disallowed_write_tools(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools:
  - Read
  - Grep
---
"""
        passed, evidence = agent_matchers.read_only_tools_coherent(content)
        self.assertFalse(passed)
        self.assertIn("Read tool present", evidence)

    def test_read_only_tools_coherent_supports_inline_comma_lists(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit, NotebookEdit
---
"""
        passed, _ = agent_matchers.read_only_tools_coherent(content)
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main()
