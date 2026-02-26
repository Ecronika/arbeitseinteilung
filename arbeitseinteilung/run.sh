#!/usr/bin/env bash
echo "Starting Arbeitseinteilung..."

# Gunicorn mit eventlet Worker starten, genau wie im originalen Dockerfile
exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8090 "app:create_app()"
