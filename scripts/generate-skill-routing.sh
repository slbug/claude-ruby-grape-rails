#!/usr/bin/env bash
# Generate routing-table + advertisement footers + tutorial-content inventory from
# plugins/ruby-grape-rails/references/skill-registry.yml.
#
# Usage:
#   scripts/generate-skill-routing.sh          # write generated blocks into target files
#   scripts/generate-skill-routing.sh --check  # exit 1 if any block diverges from registry

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUBY_SCRIPT="${SCRIPT_DIR}/generate-skill-routing.rb"
REGISTRY="${REPO_ROOT}/plugins/ruby-grape-rails/references/skill-registry.yml"

if [[ ! -f "$REGISTRY" ]]; then
  echo "generate-skill-routing: registry not found at $REGISTRY" >&2
  exit 1
fi

if [[ ! -f "$RUBY_SCRIPT" || -L "$RUBY_SCRIPT" || ! -r "$RUBY_SCRIPT" ]]; then
  echo "generate-skill-routing: Ruby script missing or unusable at $RUBY_SCRIPT" >&2
  exit 1
fi

exec ruby "$RUBY_SCRIPT" "$@"
