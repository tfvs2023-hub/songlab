Staging deployment

Overview
- Push to the `staging` branch to trigger the GitHub Actions workflow `frontend-staging-deploy.yml`.
- The workflow uploads a tarball and copies it to the staging server; the server extracts into `/home/tfvs2023/app/staging`.

Required GitHub Secrets (repo settings -> Secrets):
- STAGING_HOST: staging server host or IP
- STAGING_USER: SSH user
- STAGING_SSH_KEY: private SSH key for the user (no passphrase) - used by Actions

Server-side steps (once):
- Create directories:
  sudo mkdir -p /home/tfvs2023/app/staging /home/tfvs2023/app/dist
  sudo chown -R www-data:www-data /home/tfvs2023/app
- Create an nginx server block for staging using `deploy/nginx_staging.conf` and enable it.
- On the server, copy `scripts/promote_staging_to_prod.sh` and make it executable: `sudo chmod +x promote_staging_to_prod.sh`.

Promotion
- After validating on staging, run on server:
  sudo ./promote_staging_to_prod.sh
  # this moves staging -> production and reloads nginx

Notes
- The staging nginx config contains `charset utf-8;` to ensure the Content-Type header includes charset.
- The promotion script does an atomic directory move and a backup of the previous production.
