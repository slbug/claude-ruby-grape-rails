#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

if python3 -m pytest --version >/dev/null 2>&1; then
  exec python3 -m pytest lab/eval/tests -v
fi

exec python3 -m unittest discover -s lab/eval/tests -p 'test_*.py' -v
