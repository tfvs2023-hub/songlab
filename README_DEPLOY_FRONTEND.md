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

If you see 404s or HTML being returned for requests to `/static/*`, you have two simple options:

- Fix the HTML: update `<script>`/`<link>` tags in your HTML to use root-relative paths (for example replace `/static/script.js` with `/script.js`). This is the fastest fix if your deployed files are at the repository root.
- Serve /static: create a `/home/tfvs2023/app/dist/static/` folder on the server and copy static assets there, or use the provided `frontend_nginx_example.conf` which maps `/static/` to that folder so legacy references keep working.

Utilities
- `scripts/normalize_frontend_static_paths.sh`: run locally before packaging to rewrite `/static/` references to `/` inside `frontend_temp`.
- `scripts/populate_dist_static.sh`: run on the server to create `/home/tfvs2023/app/dist/static/` and copy `script.js`/`style.css` there for compatibility.

4) Rollback and cleanup
- If post-deploy verification fails (style.css doesn't return 200), the workflow will automatically roll back to the previous `dist_old` directory. Old backups older than 14 days are removed automatically.

5) If you want different behavior
- You can remove the normalization step if your frontend build reliably uses correct paths. Alternatively, adjust the nginx `location /static/` alias to preserve legacy URLs.
