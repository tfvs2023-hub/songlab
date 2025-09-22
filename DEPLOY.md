Simple deploy instructions (non-developer)

Run these on the server inside the repository folder (example path: `~/songlab_advanced_full`):

1) Pull latest and restart helper

```bash
cd ~/songlab_advanced_full
./scripts/deploy_backend.sh
```

2) Check health and logs

```bash
curl http://127.0.0.1:8002/api/health
tail -n 120 uvicorn_debug.log
```

Notes:
- If a systemd service named `songlab-backend` exists, the helper will restart it via `sudo systemctl restart songlab-backend`.
- If no systemd unit exists, the helper will attempt to start `uvicorn main_v2:app` using `.venv_debug/bin/python`.
- If you don't have a venv at `.venv_debug`, create one or install dependencies as described in `setup_instructions.md`.

If anything fails, copy the command output and paste it back here and I'll debug it for you.
