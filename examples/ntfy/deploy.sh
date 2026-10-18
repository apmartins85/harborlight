#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
helm repo add helmforge https://repo.helmforge.dev --force-update
helm repo update helmforge
helm upgrade --install ntfy helmforge/ntfy --version 1.6.2 \
  --namespace notifications --create-namespace \
  -f examples/ntfy/values.yaml --wait --timeout 180s
helm upgrade --install demo ./charts/harborlight \
  --namespace harborlight --create-namespace \
  --reset-values --wait --timeout 120s
