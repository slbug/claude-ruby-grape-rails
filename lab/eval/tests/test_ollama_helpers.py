"""Tests for Ollama URL helpers in behavioral_scorer."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from lab.eval import behavioral_scorer as bs
from lab.eval.behavioral_scorer import (
    _derive_ollama_api_url,
    _normalize_ollama_base_url,
)


class TestNormalizeOllamaBaseUrl(unittest.TestCase):
    """Ollama OpenAI base URL normalization."""

    def test_root_path_adds_v1(self) -> None:
        self.assertEqual(
            _normalize_ollama_base_url("http://127.0.0.1:11434"),
            "http://127.0.0.1:11434/v1",
        )

    def test_bare_host_adds_scheme_and_v1(self) -> None:
        self.assertEqual(
            _normalize_ollama_base_url("127.0.0.1:11434"),
            "http://127.0.0.1:11434/v1",
        )

    def test_explicit_v1_preserved(self) -> None:
        self.assertEqual(
            _normalize_ollama_base_url("http://localhost:11434/v1"),
            "http://localhost:11434/v1",
        )

    def test_prefixed_v1_preserved(self) -> None:
        self.assertEqual(
            _normalize_ollama_base_url("https://proxy.example.com/ollama/v1"),
            "https://proxy.example.com/ollama/v1",
        )


class TestDeriveOllamaApiUrl(unittest.TestCase):
    """Native Ollama API URL derivation from OpenAI-compatible base URLs."""

    def test_root_v1_stripped(self) -> None:
        self.assertEqual(
            _derive_ollama_api_url("http://127.0.0.1:11434/v1", "/api/version"),
            "http://127.0.0.1:11434/api/version",
        )

    def test_prefixed_v1_stripped(self) -> None:
        self.assertEqual(
            _derive_ollama_api_url(
                "https://proxy.example.com/ollama/v1",
                "/api/tags",
            ),
            "https://proxy.example.com/ollama/api/tags",
        )


class TestEnsureOllamaServer(unittest.TestCase):
    """Ollama local auto-spawn validation."""

    def setUp(self) -> None:
        bs._ollama_base_url_cache = None
        bs._ollama_server_proc = None
        bs._ollama_stderr_path = None

    def tearDown(self) -> None:
        bs._ollama_base_url_cache = None
        bs._ollama_server_proc = None
        bs._ollama_stderr_path = None

    def test_https_loopback_rejected_before_spawn(self) -> None:
        with patch.dict(
            "os.environ",
            {"RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL": "https://127.0.0.1:11434/v1"},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "requires an http URL"):
                bs._ensure_ollama_server()


if __name__ == "__main__":
    unittest.main()
