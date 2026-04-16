"""Tests for Ollama URL helpers in behavioral_scorer."""

from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
