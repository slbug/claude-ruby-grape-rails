#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# Run markdown linting on staged .md files
mapfile -d '' -t STAGED_MD_FILES < <(git diff --cached --name-only -z --diff-filter=ACM -- '*.md')

if [[ ${#STAGED_MD_FILES[@]} -gt 0 ]]; then
  echo "Linting staged Markdown files..."

  if command -v npx >/dev/null 2>&1; then
    if ! printf '%s\0' "${STAGED_MD_FILES[@]}" | xargs -0 npx markdownlint --ignore node_modules --ignore docs --ignore reports; then
      echo ""
      echo "Markdown lint errors found. Fix them or run:"
      echo "  npm run lint:fix"
      echo ""
      exit 1
    fi
  else
    echo "Warning: npx not found, skipping markdown lint"
  fi
fi

# Validate JSON files
mapfile -d '' -t STAGED_JSON_FILES < <(git diff --cached --name-only -z --diff-filter=ACM -- '*.json')

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
