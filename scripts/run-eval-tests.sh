#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [[ -L "$SCRIPT_SOURCE" ]]; do
  SOURCE_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd -P)"
  LINK_TARGET="$(readlink "$SCRIPT_SOURCE")"
  if [[ "$LINK_TARGET" == /* ]]; then
    SCRIPT_SOURCE="$LINK_TARGET"
  else
    SCRIPT_SOURCE="${SOURCE_DIR}/${LINK_TARGET}"
  fi
done
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd -P)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
cd "$PROJECT_ROOT" || exit 1

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "ERROR: lab/eval tests require python3 3.10+." >&2
  echo "Current python3: $(python3 --version 2>/dev/null || echo unavailable)" >&2
  exit 1
fi

exec python3 -m unittest discover -s lab/eval/tests -p 'test_*.py' -t . -v
