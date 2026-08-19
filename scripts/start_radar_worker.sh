#!/bin/sh
set -eu

export RADAR_WORKER_ID="${RADAR_WORKER_ID:-railway-${RAILWAY_REPLICA_ID:-worker}}"

echo "Starting DENTAI Patient Radar worker: ${RADAR_WORKER_ID}"
exec python -m app.radar.worker
