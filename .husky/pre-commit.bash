#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# Run markdown linting on staged .md files
STAGED_MD_FILES=()
while IFS= read -r -d '' file; do
  STAGED_MD_FILES+=("$file")
done < <(git diff --cached --name-only -z --diff-filter=ACM -- '*.md')

if [[ ${#STAGED_MD_FILES[@]} -gt 0 ]]; then
  echo "Linting staged Markdown files..."

  if command -v npx >/dev/null 2>&1; then
    if ! printf '%s\0' "${STAGED_MD_FILES[@]}" | xargs -0 npx markdownlint --; then
      echo ""
      echo "Markdown lint errors found. Fix them or run:"
      echo "  npm run lint:fix"
      echo ""
      exit 1
    fi
  else
    echo "ERROR: npx not found, cannot lint staged Markdown files." >&2
    echo "Install Node.js dependencies with 'npm ci' before committing Markdown changes." >&2
    exit 1
  fi
fi

# Validate JSON files
STAGED_JSON_FILES=()
while IFS= read -r -d '' file; do
  STAGED_JSON_FILES+=("$file")
done < <(git diff --cached --name-only -z --diff-filter=ACM -- '*.json')

if [[ ${#STAGED_JSON_FILES[@]} -gt 0 ]]; then
  echo "Validating staged JSON files..."

  for file in "${STAGED_JSON_FILES[@]}"; do
    if [[ -f "$file" ]]; then
      if ! python3 -m json.tool "$file" > /dev/null 2>&1; then
        echo "Invalid JSON: $file"
        exit 1
      fi
    fi
  done
fi

echo "Pre-commit checks passed!"
