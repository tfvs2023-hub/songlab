#!/usr/bin/env bash
# Populate /home/tfvs2023/app/dist/static from existing dist files.
# Intended to be run on the server (or adapted paths locally).

set -euo pipefail

DIST_DIR="/home/tfvs2023/app/dist"
STATIC_DIR="$DIST_DIR/static"

if [ ! -d "$DIST_DIR" ]; then
  echo "Dist directory not found at $DIST_DIR" >&2
  exit 1
fi

echo "Creating $STATIC_DIR if missing"
sudo mkdir -p "$STATIC_DIR"

echo "Copying common static files to $STATIC_DIR"
sudo cp -a "$DIST_DIR"/script.js "$STATIC_DIR/" 2>/dev/null || true
sudo cp -a "$DIST_DIR"/style.css "$STATIC_DIR/" 2>/dev/null || true
sudo chown -R tfvs2023:tfvs2023 "$STATIC_DIR"

echo "Reload nginx"
sudo systemctl reload nginx || true

echo "Done."
