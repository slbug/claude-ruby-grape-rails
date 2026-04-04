#!/usr/bin/env bash
# Fetch Claude Code releases from GitHub API and extract new versions.
# Policy: informational — exits non-zero on missing deps, network/API/parse failures.
#
# Usage:
#   ./scripts/fetch-cc-changelog.sh           # New versions since last check
#   ./scripts/fetch-cc-changelog.sh --all     # Re-fetch all versions
#   ./scripts/fetch-cc-changelog.sh --set=X   # Reset last checked to version X
#
# Output:
#   STATUS: UP_TO_DATE   (no new versions)
#   STATUS: NEW_VERSIONS (followed by release entries)

set -o nounset
set -o pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
case "$SCRIPT_PATH" in
  */*) SCRIPT_BASE_DIR="${SCRIPT_PATH%/*}" ;;
  *) SCRIPT_BASE_DIR="." ;;
esac
SCRIPT_DIR="$(cd "${SCRIPT_BASE_DIR}" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

STATE_DIR="${REPO_ROOT}/.claude/cc-changelog"
STATE_FILE="${STATE_DIR}/last-checked-version.txt"
RELEASES_URL="https://api.github.com/repos/anthropics/claude-code/releases"
CURL_TIMEOUT=15
# GitHub returns at most 100 per page; CC has ~75 releases as of 2026-04.
# If this exceeds 100, add Link-header pagination.
PER_PAGE=100
FETCH_ALL=false

for arg in "$@"; do
  case "$arg" in
    --all) FETCH_ALL=true ;;
    --set=*)
      version="${arg#--set=}"
      mkdir -p "${STATE_DIR}"
      printf '%s\n' "$version" >"${STATE_FILE}"
      echo "STATE: reset last checked version to ${version}" >&2
      exit 0
      ;;
    *)
      echo "Usage: $0 [--all|--set=VERSION]" >&2
      exit 1
      ;;
  esac
done

# Check dependencies
for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}" >&2
    exit 1
  fi
done

# Read last checked version
last_checked=""
if [[ -f "$STATE_FILE" ]] && [[ "$FETCH_ALL" == "false" ]]; then
  last_checked="$(head -1 "$STATE_FILE" | tr -d '[:space:]')"
fi

# Fetch releases (single page, newest first; PER_PAGE=100 covers current release count)
tmp_file="$(mktemp "${TMPDIR:-/tmp}/cc-releases.XXXXXX")" || {
  echo "ERROR: could not create temporary file" >&2
  exit 1
}
trap 'rm -f -- "${tmp_file:?}"' EXIT

http_code="$(curl -s -w '%{http_code}' \
  --connect-timeout "$CURL_TIMEOUT" \
  --max-time 30 \
  -H "Accept: application/vnd.github+json" \
  "${RELEASES_URL}?per_page=${PER_PAGE}" \
  -o "$tmp_file" 2>/dev/null)" || {
  echo "ERROR: failed to fetch releases from GitHub API" >&2
  exit 1
}

if [[ "$http_code" != "200" ]]; then
  echo "ERROR: GitHub API returned HTTP ${http_code}" >&2
  if [[ "$http_code" == "403" ]]; then
    echo "HINT: likely rate-limited. Wait or use a GITHUB_TOKEN." >&2
  fi
  exit 1
fi

# Extract and filter releases using jq
release_count="$(jq 'length' "$tmp_file" 2>/dev/null)" || {
  echo "ERROR: failed to parse GitHub API response" >&2
  exit 1
}

if [[ "$release_count" -eq 0 ]]; then
  echo "STATUS: UP_TO_DATE"
  echo "No releases found." >&2
  exit 0
fi

# Build filtered output via jq
filtered_file="$(mktemp "${TMPDIR:-/tmp}/cc-filtered.XXXXXX")" || {
  echo "ERROR: could not create temporary file" >&2
  exit 1
}
trap 'rm -f -- "${tmp_file:?}" "${filtered_file:?}"' EXIT

if [[ -n "$last_checked" ]] && [[ "$FETCH_ALL" == "false" ]]; then
  # Filter to versions newer than last_checked using jq + sort -V
  jq -r '.[].tag_name' "$tmp_file" | sed 's/^v//' | while IFS= read -r ver; do
    # Include only versions strictly newer than last_checked
    if [[ "$ver" != "$last_checked" ]]; then
      older="$(printf '%s\n%s' "$ver" "$last_checked" | sort -V | head -1)"
      if [[ "$older" == "$last_checked" ]]; then
        echo "$ver"
      fi
    fi
  done >"$filtered_file"
else
  jq -r '.[].tag_name' "$tmp_file" | sed 's/^v//' >"$filtered_file"
fi

new_count="$(wc -l <"$filtered_file" | tr -d ' ')"

if [[ "$new_count" -eq 0 ]]; then
  echo "STATUS: UP_TO_DATE"
  exit 0
fi

# Output new versions
latest="$(head -1 "$filtered_file")"
echo "STATUS: NEW_VERSIONS"
echo "LATEST: ${latest}"
if [[ -n "$last_checked" ]]; then
  echo "PREVIOUS: ${last_checked}"
fi
echo "---"

while IFS= read -r ver; do
  # Extract release body for this version
  body="$(jq -r --arg tag "v${ver}" '.[] | select(.tag_name == $tag) | .body // "(no release notes)"' "$tmp_file")"
  date="$(jq -r --arg tag "v${ver}" '.[] | select(.tag_name == $tag) | .published_at // "unknown"' "$tmp_file")"

  printf '## %s (%s)\n' "$ver" "$date"
  printf '\n'
  printf '%s\n' "$body"
  printf '\n'
  printf '%s\n' "---"
done <"$filtered_file"
