"""Tests for apfel URL/port helpers in behavioral_scorer."""

from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from lab.eval.behavioral_scorer import (
    _derive_health_url,
    _get_apfel_port,
    _is_loopback_base_url,
    _normalize_apfel_base_url,
)


class TestDeriveHealthUrl(unittest.TestCase):
    """_derive_health_url strips the /v1 path and appends /health."""

    def test_openai_style_v1(self) -> None:
        self.assertEqual(
            _derive_health_url("http://127.0.0.1:11434/v1"),
            "http://127.0.0.1:11434/health",
        )

    def test_trailing_slash_after_v1(self) -> None:
        self.assertEqual(
            _derive_health_url("http://127.0.0.1:11434/v1/"),
            "http://127.0.0.1:11434/health",
        )

    def test_multiple_trailing_slashes(self) -> None:
        self.assertEqual(
            _derive_health_url("http://127.0.0.1:11434/v1//"),
            "http://127.0.0.1:11434/health",
        )

    def test_bare_host(self) -> None:
        self.assertEqual(
            _derive_health_url("http://127.0.0.1:11434"),
            "http://127.0.0.1:11434/health",
        )

    def test_root_slash(self) -> None:
        self.assertEqual(
            _derive_health_url("http://127.0.0.1:11434/"),
            "http://127.0.0.1:11434/health",
        )

    def test_https_preserved(self) -> None:
        self.assertEqual(
            _derive_health_url("https://apfel.example.com:9443/v1"),
            "https://apfel.example.com:9443/health",
        )

    def test_custom_path_prefix(self) -> None:
        """Non-/v1 prefix is preserved (user's custom mount point)."""
        self.assertEqual(
            _derive_health_url("https://proxy.example.com/apfel/v1"),
            "https://proxy.example.com/apfel/health",
        )


class TestIsLoopbackBaseUrl(unittest.TestCase):
    """_is_loopback_base_url flags local hosts only."""

    def test_ipv4_loopback(self) -> None:
        self.assertTrue(_is_loopback_base_url("http://127.0.0.1:11434/v1"))

    def test_ipv6_loopback(self) -> None:
        self.assertTrue(_is_loopback_base_url("http://[::1]:11434/v1"))

    def test_localhost_name(self) -> None:
        self.assertTrue(_is_loopback_base_url("http://localhost:11434/v1"))

    def test_public_host(self) -> None:
        self.assertFalse(_is_loopback_base_url("https://apfel.example.com:9443/v1"))

    def test_private_network(self) -> None:
        """Private-range IP is not loopback — user expects remote semantics."""
        self.assertFalse(_is_loopback_base_url("http://192.168.1.5:8080/v1"))

    def test_all_interfaces_is_not_loopback(self) -> None:
        """0.0.0.0 binds all interfaces but is not the loopback address for probes."""
        self.assertFalse(_is_loopback_base_url("http://0.0.0.0:11434/v1"))


class TestNormalizeApfelBaseUrl(unittest.TestCase):
    """_normalize_apfel_base_url prepends http:// when scheme missing, errors on garbage."""

    def test_passthrough_http(self) -> None:
        self.assertEqual(
            _normalize_apfel_base_url("http://127.0.0.1:11434/v1"),
            "http://127.0.0.1:11434/v1",
        )

    def test_passthrough_https(self) -> None:
        self.assertEqual(
            _normalize_apfel_base_url("https://apfel.example.com/v1"),
            "https://apfel.example.com/v1",
        )

    def test_schemeless_ipv4(self) -> None:
        self.assertEqual(
            _normalize_apfel_base_url("127.0.0.1:11434/v1"),
            "http://127.0.0.1:11434/v1",
        )

    def test_schemeless_localhost(self) -> None:
        """Without normalization, urlsplit treats 'localhost' as scheme — bug fix case."""
        self.assertEqual(
            _normalize_apfel_base_url("localhost:11434/v1"),
            "http://localhost:11434/v1",
        )

    def test_schemeless_bare_host(self) -> None:
        self.assertEqual(
            _normalize_apfel_base_url("127.0.0.1:11434"),
            "http://127.0.0.1:11434",
        )

    def test_empty_rejected(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            _normalize_apfel_base_url("")
        self.assertIn("Invalid APFEL_BASE_URL", str(ctx.exception))


class TestGetApfelPort(unittest.TestCase):
    """_get_apfel_port parses env var, falls back on garbage."""

    def test_unset_returns_default(self) -> None:
        import os
        env_copy = dict(os.environ)
        env_copy.pop("APFEL_PORT", None)
        with patch.dict("os.environ", env_copy, clear=True):
            self.assertEqual(_get_apfel_port(), 11434)

    def test_valid_int(self) -> None:
        with patch.dict("os.environ", {"APFEL_PORT": "9999"}, clear=False):
            self.assertEqual(_get_apfel_port(), 9999)

    def test_invalid_falls_back_with_warning(self) -> None:
        from lab.eval.behavioral_scorer import log as behavioral_log

        with patch.dict("os.environ", {"APFEL_PORT": "not-a-port"}, clear=False):
            with self.assertLogs(behavioral_log, level=logging.WARNING) as captured:
                port = _get_apfel_port()
            self.assertEqual(port, 11434)
            self.assertTrue(any("APFEL_PORT" in r.getMessage() for r in captured.records))


if __name__ == "__main__":
    unittest.main()
