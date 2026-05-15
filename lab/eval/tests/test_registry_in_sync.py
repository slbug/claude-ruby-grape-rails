"""Unit test: skill-registry.yml in sync with generated routing artifacts.

Runs `scripts/generate-skill-routing.sh --check`. The script exits 0 when
every BEGIN-GENERATED marker block in every target file matches the content
the registry would emit. Non-zero exit (with drift report on stderr) fails
the test.
"""

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


class RegistryInSyncTests(unittest.TestCase):
    def test_registry_matches_generated_artifacts(self) -> None:
        result = subprocess.run(
            ["bash", "scripts/generate-skill-routing.sh", "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            "Registry out of sync with generated routing artifacts.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
