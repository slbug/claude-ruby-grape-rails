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
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} contains invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def validate_json_root(data: object, name: str) -> str | None:
    """Validate that loaded JSON is a dict. Returns error message or None."""
    if not isinstance(data, dict):
        return f"{name} root must be a JSON object, got {type(data).__name__}"
    return None


def main() -> int:
    errors: list[str] = []

    package = load_json(PACKAGE_JSON)
    marketplace = load_json(MARKETPLACE_JSON)
    plugin = load_json(PLUGIN_JSON)

    # Validate JSON roots are dicts
    for data, name in [
        (package, "package.json"),
        (marketplace, "marketplace.json"),
        (plugin, "plugin.json"),
    ]:
        err = validate_json_root(data, name)
        if err:
            errors.append(err)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    changelog_text = CHANGELOG.read_text(encoding="utf-8")

    # Type-safe access after validation
    package_dict: dict = package  # type: ignore[assignment]
    marketplace_dict: dict = marketplace  # type: ignore[assignment]
    plugin_dict: dict = plugin  # type: ignore[assignment]

    current_version = package_dict.get("version")
    if not isinstance(current_version, str) or not current_version:
        errors.append("package.json is missing a string version.")
        current_version = ""

    marketplace_version = marketplace_dict.get("metadata", {}).get("version")
    plugin_version = plugin_dict.get("version")

    # Select plugin by name instead of assuming index 0
    plugins = marketplace_dict.get("plugins", [])
    if not isinstance(plugins, list):
        errors.append("marketplace.json plugins must be a list")
        ruby_plugin = None
    else:
        ruby_plugin = next(
            (
                p
                for p in plugins
                if isinstance(p, dict) and p.get("name") == "ruby-grape-rails"
            ),
            None,
        )
        if ruby_plugin is None:
            errors.append("ruby-grape-rails plugin not found in marketplace.json")

    marketplace_ref = ruby_plugin.get("source", {}).get("ref") if ruby_plugin else None

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
        for match in re.finditer(
            r"^\[([^\]]+)\]:\s+(\S+)", changelog_text, flags=re.MULTILINE
        )
    }

    missing_links = [heading for heading in headings if heading not in link_defs]
    if missing_links:
        errors.append(
            "CHANGELOG.md is missing footer links for headings: "
            + ", ".join(missing_links)
        )

    duplicate_headings = sorted(
        {heading for heading in headings if headings.count(heading) > 1}
    )
    if duplicate_headings:
        errors.append(
            "CHANGELOG.md has duplicate version headings: "
            + ", ".join(duplicate_headings)
        )

    if current_version and current_version not in headings:
        errors.append(
            f"CHANGELOG.md is missing a heading for the current version [{current_version}]."
        )

    unreleased_url = link_defs.get("Unreleased")

    # Derive repo slug from package.json repository URL
    # Handle both dict form {"type": "git", "url": "..."} and string form "owner/repo"
    repo_field = package_dict.get("repository", "")
    if isinstance(repo_field, str):
        # String form: "owner/repo" or "https://github.com/owner/repo"
        if repo_field.startswith("https://github.com/"):
            repo_url = repo_field
        elif "/" in repo_field and " " not in repo_field:
            # Assume "owner/repo" format
            repo_url = f"https://github.com/{repo_field}.git"
        else:
            repo_url = ""
    elif isinstance(repo_field, dict):
        repo_url = repo_field.get("url", "")
    else:
        repo_url = ""

    repo_match = re.match(r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?$", repo_url)
    if repo_match:
        repo_slug = repo_match.group(1)
        expected_unreleased = (
            f"https://github.com/{repo_slug}/compare/v{current_version}...HEAD"
            if current_version
            else None
        )
    else:
        errors.append(
            f"Cannot extract repository slug from package.json repository.url: {repo_url!r}"
        )
        expected_unreleased = None
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
