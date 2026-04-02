#!/usr/bin/env bash
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RUBY_PLUGIN_DETECT_RUNTIME_QUIET=1
exec "${SCRIPT_DIR}/detect-runtime.sh"
