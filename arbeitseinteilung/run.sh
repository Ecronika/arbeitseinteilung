#!/usr/bin/env bash
echo "Starting Arbeitseinteilung..."

if [ "${GUNICORN_WORKERS:-1}" -gt 1 ]; then
    echo "FEHLER: Mehr als 1 Worker ist wegen In-Memory WebSocket-Locks nicht unterstützt." >&2
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "WARNUNG: SECRET_KEY wurde beim Start automatisch generiert. Sessions gehen beim Neustart verloren."
fi

# Gunicorn mit eventlet Worker starten, genau wie im originalen Dockerfile
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8090 "app:create_app()"
