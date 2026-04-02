#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter
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


def extract_github_repo_slug(repo_field: object) -> str | None:
    repo_url = ""
    if isinstance(repo_field, str):
        repo_url = repo_field.strip()
    elif isinstance(repo_field, dict):
        repo_url = str(repo_field.get("url", "")).strip()
    else:
        return None

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo_url):
        return repo_url

    normalized = re.sub(r"^git\+", "", repo_url)

    for pattern in (
        r"^https?://github\.com/(?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?/?$",
        r"^(?:ssh://)?git@github\.com[:/](?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?/?$",
    ):
        match = re.match(pattern, normalized)
        if match:
            return match.group("slug")

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

    try:
        changelog_text = CHANGELOG.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: {CHANGELOG} not found", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR: could not read {CHANGELOG}: {e}", file=sys.stderr)
        return 1

    # Type-safe access after validation
    package_dict: dict = package  # type: ignore[assignment]
    marketplace_dict: dict = marketplace  # type: ignore[assignment]
    plugin_dict: dict = plugin  # type: ignore[assignment]

    current_version = package_dict.get("version")
    if not isinstance(current_version, str) or not current_version:
        errors.append("package.json is missing a string version.")
        current_version = ""

    # Validate metadata is a dict before accessing version
    metadata = marketplace_dict.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("marketplace.json metadata must be a JSON object")
        marketplace_version = None
    else:
        marketplace_version = metadata.get("version")
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

    # Validate source is a dict before extracting ref
    if ruby_plugin:
        source = ruby_plugin.get("source")
        if source is None:
            marketplace_ref = None
        elif isinstance(source, dict):
            marketplace_ref = source.get("ref")
        else:
            errors.append("marketplace.json plugin source must be a JSON object")
            marketplace_ref = None
    else:
        marketplace_ref = None

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

    heading_counts = Counter(headings)
    duplicate_headings = sorted(
        heading for heading, count in heading_counts.items() if count > 1
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

    repo_field = package_dict.get("repository", "")
    repo_slug = extract_github_repo_slug(repo_field)
    if repo_slug:
        expected_unreleased = (
            f"https://github.com/{repo_slug}/compare/v{current_version}...HEAD"
            if current_version
            else None
        )
    else:
        errors.append(
            f"Cannot extract repository slug from package.json repository field: {repo_field!r}"
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
