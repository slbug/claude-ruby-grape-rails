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

    def test_get_sections_ignores_nested_headings_in_parent_sections(self) -> None:
        content = """---
name: rb:sample
description: Sample skill
---
# Sample

## Workflow
Top-level workflow guidance.

### Details
Nested detail that should stay inside Workflow.

## Notes
Additional notes.
"""
        sections = matchers.get_sections(content)
        self.assertEqual(set(sections), {"Workflow", "Notes"})
        self.assertIn("Nested detail", sections["Workflow"])

    def test_description_structure(self) -> None:
        passed, _ = matchers.description_structure(SAMPLE)
        self.assertTrue(passed)

    def test_description_structure_returns_failure_specific_evidence(self) -> None:
        content = """---
name: rb:sample
description: Ruby workflow helper for local changes.
---
"""
        passed, evidence = matchers.description_structure(content)
        self.assertFalse(passed)
        self.assertIn("missing explicit use/intent framing", evidence)

    def test_valid_skill_refs_accepts_frontmatter_command_aliases(self) -> None:
        content = "Use /rb:runtime and /rb:trace when runtime debugging needs live inspection."
        passed, evidence = matchers.valid_skill_refs(content)
        self.assertTrue(passed)
        self.assertEqual(evidence, "all skill refs valid")

    def test_workflow_step_coverage_accepts_compact_heading_and_list_structure(self) -> None:
        content = """---
name: rb:quick
description: Use for Ruby quick fixes and review follow-up.
---
# Quick Path

Use when the change is small and low risk.

1. inspect the existing code path first
2. implement directly
3. verify with the narrowest correct command set
"""
        passed, evidence = matchers.workflow_step_coverage(content, min_sections=3)
        self.assertTrue(passed)
        self.assertIn("structure units", evidence)

    def test_no_duplication_ignores_repeated_fenced_command_examples(self) -> None:
        content = """---
name: rb:sample
description: Use for Ruby verification and review workflows with Rails context.
---
# Sample

```bash
/rb:runtime logs error
```

```bash
/rb:runtime logs error
```
"""
        passed, evidence = matchers.no_duplication(content)
        self.assertTrue(passed)
        self.assertEqual(evidence, "no repeated long lines")

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

    def test_read_only_tools_coherent_treats_edit_tool_as_write_capable(self) -> None:
        content = """---
name: sample-agent
description: Make direct code edits when needed.
tools: Read, Edit, Grep, Glob
---
"""
        passed, evidence = agent_matchers.read_only_tools_coherent(content)
        self.assertTrue(passed)
        self.assertIn("write access", evidence)

    def test_permission_mode_valid_accepts_absent_field_for_shipped_agents(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools: Read, Grep, Glob, Bash
---
"""
        passed, evidence = agent_matchers.permission_mode_valid(content)
        self.assertTrue(passed)
        self.assertIn("acceptable", evidence)

    def test_omit_claudemd_coherent_requires_read_only_agents_to_opt_out_of_claude_md(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit, NotebookEdit
---
"""
        passed, evidence = agent_matchers.omit_claudemd_coherent(content)
        self.assertFalse(passed)
        self.assertIn("missing omitClaudeMd", evidence)

    def test_omit_claudemd_coherent_accepts_true_for_read_only_agents(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code carefully with read-only restrictions.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit, NotebookEdit
omitClaudeMd: true
---
"""
        passed, evidence = agent_matchers.omit_claudemd_coherent(content)
        self.assertTrue(passed)
        self.assertIn("omits CLAUDE.md", evidence)

    def test_omit_claudemd_coherent_rejects_true_for_write_capable_agents(self) -> None:
        content = """---
name: sample-agent
description: Coordinate the workflow and write output files.
tools: Read, Write, Grep, Glob
omitClaudeMd: true
---
"""
        passed, evidence = agent_matchers.omit_claudemd_coherent(content)
        self.assertFalse(passed)
        self.assertIn("should not set omitClaudeMd", evidence)

    def test_omit_claudemd_coherent_rejects_true_for_edit_capable_agents(self) -> None:
        content = """---
name: sample-agent
description: Make direct code edits when needed.
tools: Read, Edit, Grep, Glob
omitClaudeMd: true
---
"""
        passed, evidence = agent_matchers.omit_claudemd_coherent(content)
        self.assertFalse(passed)
        self.assertIn("should not set omitClaudeMd", evidence)


    # --- denylist-only agent matcher tests (v1.8.1) ---

    def test_tools_present_accepts_denylist_only_agent(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code.
disallowedTools: Edit, NotebookEdit
---
"""
        passed, evidence = agent_matchers.tools_present(content)
        self.assertTrue(passed)
        self.assertIn("denylist-only", evidence)

    def test_tools_present_fails_when_no_tools_and_no_disallowed(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code.
---
"""
        passed, _ = agent_matchers.tools_present(content)
        self.assertFalse(passed)

    def test_read_only_coherent_accepts_denylist_with_edit_blocked(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code.
disallowedTools: Edit, NotebookEdit
---
"""
        passed, evidence = agent_matchers.read_only_tools_coherent(content)
        self.assertTrue(passed)
        self.assertIn("Edit/NotebookEdit", evidence)

    def test_read_only_coherent_fails_denylist_without_edit_blocked(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code.
disallowedTools: Bash
---
"""
        passed, evidence = agent_matchers.read_only_tools_coherent(content)
        self.assertFalse(passed)
        self.assertIn("must disallow", evidence)

    def test_omit_claudemd_accepts_denylist_only_with_omit(self) -> None:
        content = """---
name: sample-agent
description: Review Ruby code.
disallowedTools: Edit, NotebookEdit
omitClaudeMd: true
---
"""
        passed, evidence = agent_matchers.omit_claudemd_coherent(content)
        self.assertTrue(passed)
        self.assertIn("specialist", evidence)

    def test_omit_claudemd_accepts_denylist_only_without_omit(self) -> None:
        content = """---
name: sample-agent
description: Orchestrate review workflow.
disallowedTools: Edit, NotebookEdit
---
"""
        passed, evidence = agent_matchers.omit_claudemd_coherent(content)
        self.assertTrue(passed)
        self.assertIn("acceptable", evidence)

    # --- no_bash_blocks regression tests (v1.8.0) ---

    def test_no_bash_blocks_passes_clean_skill(self) -> None:
        content = """---
name: rb:sample
description: Use for Ruby verification and review workflows.
---
# Sample

Run `bundle exec rspec` to verify.

- Check: `bundle exec standardrb`
- Auto-fix: `bundle exec standardrb --fix`
"""
        passed, evidence = matchers.no_bash_blocks(content)
        self.assertTrue(passed)
        self.assertEqual(evidence, "no bash blocks")

    def test_no_bash_blocks_detects_bash_block(self) -> None:
        content = """---
name: rb:sample
description: Use for Ruby verification.
---
# Sample

```bash
bundle exec rspec
```
"""
        passed, evidence = matchers.no_bash_blocks(content)
        self.assertFalse(passed)
        self.assertIn("line(s):", evidence)

    def test_no_bash_blocks_ignores_plain_fenced_blocks(self) -> None:
        content = """---
name: rb:sample
description: Use for Ruby verification.
---
# Sample

```
bundle exec rspec
```

```ruby
User.find(1)
```
"""
        passed, evidence = matchers.no_bash_blocks(content)
        self.assertTrue(passed)

    def test_no_bash_blocks_counts_multiple(self) -> None:
        content = """---
name: rb:sample
description: Use for Ruby verification.
---
# Sample

```bash
bundle exec rspec
```

Some text.

```bash
bundle exec rubocop
```
"""
        passed, evidence = matchers.no_bash_blocks(content)
        self.assertFalse(passed)
        self.assertIn("2 ```bash block(s)", evidence)
        self.assertIn("line(s):", evidence)


if __name__ == "__main__":
    unittest.main()
