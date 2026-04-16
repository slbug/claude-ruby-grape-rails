"""Tests for the shared results_dir helper module."""

from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from lab.eval import results_dir as rd


class TestResolveProvider(unittest.TestCase):
    """resolve_provider() validates against the allowlist and honors env var."""

    def setUp(self) -> None:
        # Each test starts with a clean warning cache so one-time warnings fire.
        rd._warned_invalid_env.clear()

    def test_explicit_supported(self) -> None:
        self.assertEqual(rd.resolve_provider("ollama"), "ollama")
        self.assertEqual(rd.resolve_provider("apfel"), "apfel")
        self.assertEqual(rd.resolve_provider("haiku"), "haiku")

    def test_explicit_invalid_returns_default(self) -> None:
        # Programmatic caller bad-input: fall through to default, no warning.
        self.assertEqual(rd.resolve_provider("bogus"), rd.DEFAULT_PROVIDER)

    def test_none_reads_env(self) -> None:
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: "haiku"}, clear=False):
            self.assertEqual(rd.resolve_provider(None), "haiku")

    def test_none_unset_env_falls_back_to_default(self) -> None:
        import os
        env_copy = dict(os.environ)
        env_copy.pop(rd.PROVIDER_ENV_VAR, None)
        with patch.dict("os.environ", env_copy, clear=True):
            self.assertEqual(rd.resolve_provider(None), rd.DEFAULT_PROVIDER)

    def test_invalid_env_warns_once(self) -> None:
        """Typo in env var emits a warning once per unique bad value."""
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: "haik"}, clear=False):
            with self.assertLogs(rd._log, level=logging.WARNING) as captured:
                rd.resolve_provider(None)
                rd.resolve_provider(None)  # second call — should NOT warn again
            # Only one warning emitted for the repeated bad value.
            self.assertEqual(len(captured.records), 1)
            self.assertIn("haik", captured.records[0].getMessage())

    def test_invalid_env_warns_per_distinct_value(self) -> None:
        """Different bad values each warn once."""
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: "haik"}, clear=False):
            with self.assertLogs(rd._log, level=logging.WARNING) as captured:
                rd.resolve_provider(None)
            self.assertEqual(len(captured.records), 1)
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: "apfl"}, clear=False):
            with self.assertLogs(rd._log, level=logging.WARNING) as captured:
                rd.resolve_provider(None)
            self.assertEqual(len(captured.records), 1)

    def test_empty_env_does_not_warn(self) -> None:
        """Empty-string env var falls back silently (not a user typo)."""
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: ""}, clear=False):
            # Use self.assertNoLogs via assertLogs + catch if supported; else
            # check the warned cache stays empty.
            rd.resolve_provider(None)
            self.assertEqual(rd._warned_invalid_env, set())

    def test_path_traversal_rejected(self) -> None:
        """Attempts to escape RESULTS_BASE via env var resolve to default."""
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: "../etc"}, clear=False):
            self.assertEqual(rd.resolve_provider(None), rd.DEFAULT_PROVIDER)


class TestResultsDir(unittest.TestCase):
    """results_dir() composes the provider-scoped Path."""

    def test_explicit_provider(self) -> None:
        with patch.dict("os.environ", {rd.OLLAMA_MODEL_ENV_VAR: ""}, clear=False):
            self.assertEqual(rd.results_dir("ollama"), rd.RESULTS_BASE / "gemma4")
            self.assertEqual(rd.results_dir("apfel"), rd.RESULTS_BASE / "apfel")
            self.assertEqual(rd.results_dir("haiku"), rd.RESULTS_BASE / "haiku")

    def test_invalid_provider_uses_default(self) -> None:
        with patch.dict("os.environ", {rd.OLLAMA_MODEL_ENV_VAR: ""}, clear=False):
            self.assertEqual(rd.results_dir("bogus"), rd.RESULTS_BASE / "gemma4")

    def test_none_uses_env(self) -> None:
        with patch.dict("os.environ", {rd.PROVIDER_ENV_VAR: "haiku"}, clear=False):
            self.assertEqual(rd.results_dir(None), rd.RESULTS_BASE / "haiku")

    def test_explicit_ollama_model(self) -> None:
        self.assertEqual(
            rd.results_dir("ollama", model="qwen3:8b"),
            rd.RESULTS_BASE / "qwen3-8b",
        )


class TestOllamaNamespace(unittest.TestCase):
    """Ollama cache namespace is derived from the active model tag."""

    def test_default_model(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(rd.resolve_ollama_model(), "gemma4:latest")
            self.assertEqual(rd.model_cache_namespace(), "gemma4")

    def test_non_latest_tags_are_preserved(self) -> None:
        self.assertEqual(rd.model_cache_namespace("qwen3:8b"), "qwen3-8b")
        self.assertEqual(rd.model_cache_namespace("qwen3:14b"), "qwen3-14b")

    def test_latest_tag_and_library_prefix_removed(self) -> None:
        self.assertEqual(rd.model_cache_namespace("library/gemma4:latest"), "gemma4")

    def test_env_model_controls_ollama_result_dir(self) -> None:
        env = {
            rd.PROVIDER_ENV_VAR: "ollama",
            rd.OLLAMA_MODEL_ENV_VAR: "qwen3:8b",
        }
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(rd.results_dir(None), rd.RESULTS_BASE / "qwen3-8b")


if __name__ == "__main__":
    unittest.main()
