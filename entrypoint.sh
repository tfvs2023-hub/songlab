#!/bin/sh
# entrypoint.sh - validate PORT and start uvicorn

echo "Starting container. ENV vars:"
env | sort

# Default PORT fallback
PORT=${PORT:-8080}

# Validate PORT is integer
if ! echo "$PORT" | grep -Eq '^[0-9]+$'; then
  echo "Error: PORT value '$PORT' is not a valid integer." >&2
  exit 2
fi

echo "Using PORT=$PORT"

# Start uvicorn with the provided port, run in foreground
# Use --proxy-headers so X-Forwarded-For/Proto from Cloud Run are honored
# Set log level to info for clearer startup logs
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --log-level info
