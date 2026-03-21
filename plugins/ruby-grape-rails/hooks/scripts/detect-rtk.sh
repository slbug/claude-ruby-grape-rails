#!/bin/bash
# Detect if RTK is installed and available
# RTK is a CLI proxy that reduces LLM token consumption by 60-90%
# https://github.com/rtk-ai/rtk
#
# NOTE: This script is currently informational only. It detects RTK
# availability but no downstream hooks currently consume RTK_AVAILABLE
# or RTK_PATH. Future integration could use this for automatic token
# optimization suggestions.

set -e

RTK_PATH=""

# Check for rtk in common locations
if command -v rtk &> /dev/null; then
  RTK_PATH=$(command -v rtk)
elif [ -f "$HOME/.local/bin/rtk" ]; then
  RTK_PATH="$HOME/.local/bin/rtk"
elif [ -f "/usr/local/bin/rtk" ]; then
  RTK_PATH="/usr/local/bin/rtk"
elif [ -f "/opt/homebrew/bin/rtk" ]; then
  RTK_PATH="/opt/homebrew/bin/rtk"
fi

if [ -n "$RTK_PATH" ]; then
  RTK_VERSION=$($RTK_PATH --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
  echo "✓ RTK detected at: $RTK_PATH (v$RTK_VERSION)"
  echo "RTK_AVAILABLE=true"
  echo "RTK_PATH=$RTK_PATH"
  
  # Show token savings if available
  if $RTK_PATH gain --help &> /dev/null; then
    echo "RTK_GAIN_AVAILABLE=true"
  fi
  
  exit 0
else
  echo "○ RTK not detected (install: https://github.com/rtk-ai/rtk)"
  echo "RTK_AVAILABLE=false"
  exit 0
fi
