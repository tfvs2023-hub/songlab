Frontend deploy notes

1) Purpose
- The repo contains an automated GitHub Actions workflow `.github/workflows/frontend-deploy.yml` that packages `frontend_temp/` into a tarball, uploads it to the server, extracts it into a temporary directory, validates required files (`index.html`, `style.css`), swaps into place atomically, and reloads nginx.

2) Nginx example
- See `frontend_nginx_example.conf` for a recommended server block. To apply on the server:

  sudo cp frontend_nginx_example.conf /etc/nginx/sites-available/songlab.conf
  sudo ln -s /etc/nginx/sites-available/songlab.conf /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx

3) Migration note
- The workflow includes a normalization step that rewrites absolute `http(s)://www.songlab.kr:8001/static/...` and `http(s)://www.songlab.kr:8001/...` references in HTML files to root-relative paths before creating the tarball. This avoids deploying HTML that points to a separate host/port for static assets.

4) Rollback and cleanup
- If post-deploy verification fails (style.css doesn't return 200), the workflow will automatically roll back to the previous `dist_old` directory. Old backups older than 14 days are removed automatically.

5) If you want different behavior
- You can remove the normalization step if your frontend build reliably uses correct paths. Alternatively, adjust the nginx `location /static/` alias to preserve legacy URLs.
