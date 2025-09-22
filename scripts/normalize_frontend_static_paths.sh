#!/usr/bin/env bash
# Normalize legacy "/static/" references to root-relative paths in frontend_temp
# Usage: ./scripts/normalize_frontend_static_paths.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend_temp"

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "frontend_temp not found at $FRONTEND_DIR" >&2
  exit 1
fi

echo "Normalizing /static/ references in HTML/JS/CSS under $FRONTEND_DIR"
find "$FRONTEND_DIR" -type f \( -name "*.html" -o -name "*.js" -o -name "*.css" \) -print0 \
  | xargs -0 -n1 sed -i "s|/static/|/|g"

echo "Done. Please repackage frontend_temp for deploy."
