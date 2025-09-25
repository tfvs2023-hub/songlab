#!/bin/sh
# Restart uvicorn from the app directory so Python can import main_v2
pkill -f "uvicorn main_v2:app" || true
sleep 1
cd /home/tfvs2023/app || exit 1
nohup /usr/bin/python3 -m uvicorn main_v2:app --host 127.0.0.1 --port 8002 --log-level info > /home/tfvs2023/app/uvicorn.log 2>&1 &
echo restarted
