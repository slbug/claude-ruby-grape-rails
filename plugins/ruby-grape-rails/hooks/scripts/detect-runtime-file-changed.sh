#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/detect-runtime-async.sh"
