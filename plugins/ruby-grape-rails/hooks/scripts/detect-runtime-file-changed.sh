#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.
#
# Registered in hooks.json under FileChanged, CwdChanged, and DirectoryAdded.
# Every registration triggers the same quiet re-detection of the Ruby runtime
# snapshot.
#
# Payload contract: this wrapper reads nothing itself, but the exec chain
# (detect-runtime-async.sh -> detect-runtime.sh) calls read_hook_input and
# passes the payload to resolve_workspace_root, which reads the base field
# .cwd only. No event-specific field is read, so the chain does not depend on
# any single event's schema. Workspace-root resolution falls back to
# CLAUDE_PROJECT_DIR and then $PWD, so a missing, empty, or unparseable
# payload still resolves; failures warn and exit 0.
#
# DirectoryAdded fires after /add-dir (or the SDK register_repo_root control
# request) registers an additional working directory, which CwdChanged does
# not cover because the session cwd is unchanged.


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/detect-runtime-async.sh"
