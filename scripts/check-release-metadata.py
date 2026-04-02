#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
PACKAGE_JSON = ROOT / "package.json"
MARKETPLACE_JSON = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_JSON = ROOT / "plugins" / "ruby-grape-rails" / ".claude-plugin" / "plugin.json"


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    errors: list[str] = []

    package = load_json(PACKAGE_JSON)
    marketplace = load_json(MARKETPLACE_JSON)
    plugin = load_json(PLUGIN_JSON)
    changelog_text = CHANGELOG.read_text(encoding="utf-8")

    current_version = package.get("version")
    if not isinstance(current_version, str) or not current_version:
        errors.append("package.json is missing a string version.")
        current_version = ""

    marketplace_version = marketplace.get("metadata", {}).get("version")
    plugin_version = plugin.get("version")
    marketplace_ref = marketplace.get("plugins", [{}])[0].get("source", {}).get("ref")

    if marketplace_version != current_version:
        errors.append(
            f".claude-plugin/marketplace.json metadata.version={marketplace_version!r} does not match package.json version={current_version!r}."
        )
    if plugin_version != current_version:
        errors.append(
            f"plugins/ruby-grape-rails/.claude-plugin/plugin.json version={plugin_version!r} does not match package.json version={current_version!r}."
        )
    expected_ref = f"v{current_version}" if current_version else None
    if expected_ref and marketplace_ref != expected_ref:
        errors.append(
            f".claude-plugin/marketplace.json source.ref={marketplace_ref!r} does not match expected {expected_ref!r}."
        )

    headings = re.findall(r"^## \[([^\]]+)\]", changelog_text, flags=re.MULTILINE)
    link_defs = {
        match.group(1): match.group(2)
        for match in re.finditer(r"^\[([^\]]+)\]:\s+(\S+)", changelog_text, flags=re.MULTILINE)
    }

    missing_links = [heading for heading in headings if heading not in link_defs]
    if missing_links:
        errors.append(
            "CHANGELOG.md is missing footer links for headings: " + ", ".join(missing_links)
        )

    duplicate_headings = sorted({heading for heading in headings if headings.count(heading) > 1})
    if duplicate_headings:
        errors.append(
            "CHANGELOG.md has duplicate version headings: " + ", ".join(duplicate_headings)
        )

    if current_version and current_version not in headings:
        errors.append(f"CHANGELOG.md is missing a heading for the current version [{current_version}].")

    unreleased_url = link_defs.get("Unreleased")
    expected_unreleased = (
        f"https://github.com/slbug/claude-ruby-grape-rails/compare/v{current_version}...HEAD"
        if current_version
        else None
    )
    if expected_unreleased and unreleased_url != expected_unreleased:
        errors.append(
            f"CHANGELOG.md [Unreleased] link={unreleased_url!r} does not match expected {expected_unreleased!r}."
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Release metadata and changelog links are aligned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
