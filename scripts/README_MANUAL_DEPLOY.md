Manual deploy and Actions-log paste template

What this provides
- A safe, minimal manual deploy script: `scripts/manual_deploy.sh` intended to run on the server.
- A small README explaining how to use it and how to paste GitHub Actions logs into the issue or chat for debugging.

When to use
- If the automated GitHub Actions deploy fails and you trust the tarball already uploaded to `/home/tfvs2023/app/frontend_temp.tar.gz` on the server.
- If you prefer to deploy manually instead of debugging CI immediately.

Quick steps (server)
1. SSH to the server as a user that can sudo.
2. Move the uploaded tarball into place (if it isn't already):
   sudo mv /tmp/frontend_temp.tar.gz /home/tfvs2023/app/frontend_temp.tar.gz
3. Run the script:
   sudo bash /home/tfvs2023/app/scripts/manual_deploy.sh

What it does
- Extracts the tarball to `/home/tfvs2023/app/dist_new`
- Verifies `index.html` and `style.css` exist
- Moves existing `/home/tfvs2023/app/dist` to a timestamped backup under `/home/tfvs2023/app/backups`
- Moves the new content into `/home/tfvs2023/app/dist`
- Reloads nginx

Actions log paste template
- If the GitHub Actions run failed, please paste (only) the failing step name and the last ~200 lines of its log here.
  Example template to copy/paste:

  --- BEGIN ACTIONS LOG ---
  Workflow: frontend-deploy.yml
  Run id: <paste-run-id>
  Failed step: <step name>
  Last lines of logs:
  <paste lines>
  --- END ACTIONS LOG ---

Security notes
- The script assumes the tarball is present at `/home/tfvs2023/app/frontend_temp.tar.gz` and that `sudo` can move and reload services.
- If you require a different deploy user, edit `DEPLOY_USER` in the script and verify ownership with `chown`.

If you want, I can also:
- Create a one-shot SSH command for you to run locally that uploads the tarball and runs the script (requires your consent to generate the command only; no credentials are used here).
- Parse the Actions logs you paste and propose concrete fixes to the workflow or server steps.
