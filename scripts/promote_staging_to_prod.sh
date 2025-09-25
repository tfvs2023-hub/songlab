#!/bin/bash
# Usage: sudo ./promote_staging_to_prod.sh
set -e
STAGING_DIR=/home/tfvs2023/app/staging
PROD_DIR=/home/tfvs2023/app/dist
BACKUP_DIR=/home/tfvs2023/app/backup_$(date +%s)

echo "Backing up current production to $BACKUP_DIR"
sudo mv "$PROD_DIR" "$BACKUP_DIR"

echo "Promoting staging to production"
sudo mv "$STAGING_DIR" "$PROD_DIR"

# Ensure permissions
sudo chown -R www-data:www-data "$PROD_DIR" || true

# Reload nginx
sudo systemctl reload nginx

echo "Promotion complete"
