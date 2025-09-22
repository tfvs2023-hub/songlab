#!/usr/bin/env bash
set -euo pipefail

# Manual deploy helper for server (run on the server or via SSH)
# Usage: sudo bash manual_deploy.sh
# This script assumes the uploaded tarball is at /home/tfvs2023/app/frontend_temp.tar.gz

TAR=/home/tfvs2023/app/frontend_temp.tar.gz
TARGET=/home/tfvs2023/app/dist
TMP=/home/tfvs2023/app/dist_new
BACKUP_DIR=/home/tfvs2023/app/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="$BACKUP_DIR/dist_backup_$TIMESTAMP"

echo "Manual deploy starting: $(date)"
if [ ! -f "$TAR" ]; then
  echo "ERROR: tarball not found at $TAR"
  ls -la /home/tfvs2023/app || true
  exit 1
fi

sudo mkdir -p "$TMP"
sudo rm -rf "$TMP"/* || true

echo "Extracting $TAR to $TMP"
sudo tar -xzf "$TAR" -C "$TMP"

# Basic validation
if [ ! -f "$TMP/index.html" ]; then
  echo "ERROR: index.html missing in extracted content"
  sudo ls -la "$TMP" || true
  exit 1
fi
if [ ! -f "$TMP/style.css" ]; then
  echo "ERROR: style.css missing in extracted content"
  sudo ls -la "$TMP" || true
  exit 1
fi

# Backup existing dist
sudo mkdir -p "$BACKUP_DIR"
if [ -d "$TARGET" ]; then
  echo "Backing up current $TARGET to $BACKUP"
  sudo mv "$TARGET" "$BACKUP"
fi

# Swap
echo "Swapping $TMP -> $TARGET"
sudo mv "$TMP" "$TARGET"

# (Optional) Adjust ownership if needed. Uncomment and set DEPLOY_USER if required.
# DEPLOY_USER=ubuntu
# sudo chown -R "$DEPLOY_USER": "$TARGET"

# Reload nginx
echo "Reloading nginx"
sudo systemctl reload nginx || true

echo "Manual deploy finished. Backup (if any) is at: $BACKUP"
exit 0
