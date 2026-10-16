#!/bin/sh
# Apply database migrations, then start the API.
# The database may still be starting (compose / Kubernetes), so retry for a while.
set -e

MAX_ATTEMPTS="${MIGRATION_MAX_ATTEMPTS:-30}"
attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "Migrations failed after $attempt attempts, giving up." >&2
    exit 1
  fi
  echo "Database not ready (attempt $attempt/$MAX_ATTEMPTS), retrying in 2s..." >&2
  attempt=$((attempt + 1))
  sleep 2
done

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  --no-server-header
