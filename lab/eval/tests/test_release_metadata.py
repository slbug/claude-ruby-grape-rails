from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "scripts" / "check-release-metadata.py"
SPEC = importlib.util.spec_from_file_location("check_release_metadata", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseMetadataTests(unittest.TestCase):
    def test_extract_github_repo_slug_accepts_https(self) -> None:
        self.assertEqual(
            MODULE.extract_github_repo_slug("https://github.com/slbug/claude-ruby-grape-rails.git"),
            "slbug/claude-ruby-grape-rails",
        )

    def test_extract_github_repo_slug_accepts_git_plus_https(self) -> None:
        self.assertEqual(
            MODULE.extract_github_repo_slug({"type": "git", "url": "git+https://github.com/slbug/claude-ruby-grape-rails.git"}),
            "slbug/claude-ruby-grape-rails",
        )

    def test_extract_github_repo_slug_accepts_ssh(self) -> None:
        self.assertEqual(
            MODULE.extract_github_repo_slug({"type": "git", "url": "git@github.com:slbug/claude-ruby-grape-rails.git"}),
            "slbug/claude-ruby-grape-rails",
        )

    def test_expected_marketplace_plugin_name_defaults_to_plugin_name(self) -> None:
        self.assertEqual(
            MODULE.expected_marketplace_plugin_name({"name": "forked-plugin"}),
            "forked-plugin",
        )

    def test_expected_marketplace_plugin_name_accepts_env_override(self) -> None:
        previous = os.environ.get("RUBY_PLUGIN_EXPECTED_MARKETPLACE_NAME")
        os.environ["RUBY_PLUGIN_EXPECTED_MARKETPLACE_NAME"] = "renamed-plugin"
        try:
            self.assertEqual(
                MODULE.expected_marketplace_plugin_name({"name": "forked-plugin"}),
                "renamed-plugin",
            )
        finally:
            if previous is None:
                os.environ.pop("RUBY_PLUGIN_EXPECTED_MARKETPLACE_NAME", None)
            else:
                os.environ["RUBY_PLUGIN_EXPECTED_MARKETPLACE_NAME"] = previous

    def test_expected_marketplace_plugin_name_rejects_non_string_plugin_name(self) -> None:
        self.assertIsNone(MODULE.expected_marketplace_plugin_name({"name": None}))
        self.assertIsNone(MODULE.expected_marketplace_plugin_name({"name": 123}))
        self.assertIsNone(MODULE.expected_marketplace_plugin_name({"name": []}))


if __name__ == "__main__":
    unittest.main()
