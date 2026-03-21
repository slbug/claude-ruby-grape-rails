#!/bin/bash
# Detect if betterleaks is installed and available
# Sets environment variable for other hooks to use
#
# NOTE: This script is currently informational only. It detects betterleaks
# availability but no downstream hooks currently consume BETTERLEAKS_AVAILABLE
# or BETTERLEAKS_PATH. Future integration could use this for automatic
# memory leak detection during test runs.

set -e

BETTERLEAKS_PATH=""

# Check for betterleaks in common locations
if command -v betterleaks &> /dev/null; then
  BETTERLEAKS_PATH=$(command -v betterleaks)
elif [ -f "$HOME/.local/bin/betterleaks" ]; then
  BETTERLEAKS_PATH="$HOME/.local/bin/betterleaks"
elif [ -f "/usr/local/bin/betterleaks" ]; then
  BETTERLEAKS_PATH="/usr/local/bin/betterleaks"
elif [ -f "/opt/homebrew/bin/betterleaks" ]; then
  BETTERLEAKS_PATH="/opt/homebrew/bin/betterleaks"
fi

if [ -n "$BETTERLEAKS_PATH" ]; then
  echo "✓ Betterleaks detected at: $BETTERLEAKS_PATH"
  # Output for hook system to capture
  echo "BETTERLEAKS_AVAILABLE=true"
  echo "BETTERLEAKS_PATH=$BETTERLEAKS_PATH"
  exit 0
else
  echo "○ Betterleaks not detected (install: https://github.com/betterleaks/betterleaks)"
  echo "BETTERLEAKS_AVAILABLE=false"
  exit 0
fi
