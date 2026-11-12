#!/usr/bin/env bash
# Khởi tạo metadata Superset (idempotent) rồi chạy web server.
set -e

superset db upgrade
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USER:-admin}" \
  --firstname Admin --lastname Olist \
  --email admin@example.com \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true
superset init

exec /usr/bin/run-server.sh
