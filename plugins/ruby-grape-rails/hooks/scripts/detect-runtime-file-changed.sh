#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.
#
# Registered in hooks.json under FileChanged, CwdChanged, and DirectoryAdded.
# Reads no hook payload, so it is event-shape agnostic: every registration
# triggers the same quiet re-detection of the Ruby runtime snapshot.
# DirectoryAdded fires after /add-dir (or the SDK register_repo_root control
# request) registers an additional working directory, which CwdChanged does
# not cover because the session cwd is unchanged.


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/detect-runtime-async.sh"
