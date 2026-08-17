#!/bin/sh
set -eu

if [ "${WHATSAPP_EMBEDDED_SERVICE:-true}" = "true" ]; then
  export WHATSAPP_SERVICE_PORT="${WHATSAPP_SERVICE_PORT:-3001}"
  export WHATSAPP_SESSION_DIR="${WHATSAPP_SESSION_DIR:-/app/data/whatsapp_sessions}"
  if [ -z "${WHATSAPP_SERVICE_URL:-}" ] || [ "${WHATSAPP_SERVICE_URL}" = "http://whatsapp-service:3001" ]; then
    export WHATSAPP_SERVICE_URL="http://127.0.0.1:${WHATSAPP_SERVICE_PORT}"
  fi
  mkdir -p "$WHATSAPP_SESSION_DIR"
  echo "Starting embedded WhatsApp service on 127.0.0.1:${WHATSAPP_SERVICE_PORT}"
  (
    cd /app/whatsapp_service
    node src/index.js
  ) &
else
  echo "Embedded WhatsApp service disabled; using WHATSAPP_SERVICE_URL=${WHATSAPP_SERVICE_URL:-unset}"
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}"
