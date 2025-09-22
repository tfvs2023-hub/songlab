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

# If USE_OVERRIDES is not set or set to 1/true, copy files from /app/overrides
# into /app so edited files in a mounted volume take precedence at runtime.
USE_OVERRIDES=${USE_OVERRIDES:-1}
if [ "$USE_OVERRIDES" = "1" ] || [ "$USE_OVERRIDES" = "true" ] || [ "$USE_OVERRIDES" = "True" ]; then
  if [ -d "/app/overrides" ]; then
    echo "Applying runtime overrides from /app/overrides -> /app (overwriting)"
    # Use a portable copy: preserve structure and overwrite files. -a preserves
    # permissions/timestamps where supported. The trailing slash handles copying
    # contents of overrides into /app.
    cp -a /app/overrides/. /app/ 2>/dev/null || {
      # Fallback to a safe recursive copy if -a isn't supported in this shell
      find /app/overrides -type d -exec mkdir -p "/app/{}" \; 2>/dev/null || true
      find /app/overrides -type f -exec sh -c 'for f; do dst="/app/${f#/app/overrides/}"; mkdir -p "$(dirname "$dst")"; cp -f "$f" "$dst"; echo "Overriding: ${dst#/app/}"; done' sh {} +
    }
  else
    echo "/app/overrides not present; skipping overrides"
  fi
else
  echo "USE_OVERRIDES=$USE_OVERRIDES -> skipping runtime overrides"
fi

# Start uvicorn with the provided port, run in foreground
# Use --proxy-headers so X-Forwarded-For/Proto from Cloud Run are honored
# Set log level to info for clearer startup logs
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --log-level info
