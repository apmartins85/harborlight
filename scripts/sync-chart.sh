#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
cp app.py index.html charts/harborlight/files/
cp microservices/task-api/app.py charts/harborlight/files/task-api.py
